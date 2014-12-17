# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009-2010  Nick Hall
# Copyright (C) 2011       Tim G L Lyons
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""
Citation Tree View (or Source tree view).
A view showing all the Sources with child Citations
"""
#-------------------------------------------------------------------------
#
# python modules
#
#-------------------------------------------------------------------------
import logging
LOG = logging.getLogger(".citation")
_LOG = logging.getLogger('.gui.citationtreeview')

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gui.views.listview import TEXT, MARKUP, ICON
from gramps.gui.views.treemodels.citationtreemodel import CitationTreeModel
from gramps.gen.plug import CATEGORY_QR_SOURCE_OR_CITATION
from gramps.gen.lib import Citation, Source
from gramps.gui.views.listview import ListView
from gramps.gen.utils.db import (get_source_and_citation_referents, 
                                get_citation_referents)
from gramps.gui.views.bookmarks import CitationBookmarks
from gramps.gen.errors import WindowActiveError
from gramps.gui.ddtargets import DdTargets
from gramps.gui.dialog import ErrorDialog
from gramps.gui.editors import EditCitation, DeleteCitationQuery, EditSource, \
    DeleteSrcQuery
from gramps.gui.filters.sidebar import SourceSidebarFilter
from gramps.gui.merge import MergeCitation, MergeSource

#-------------------------------------------------------------------------
#
# Internationalization
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# PlaceTreeView
#
#-------------------------------------------------------------------------
class CitationTreeView(ListView):
    """
    A hierarchical view of sources with citations below them.
    """
    # The data items here have to correspond, in order, to the items in
    # src/giu/views/treemodels/citationtreemodel.py
    COL_TITLE_PAGE     =  0
    COL_ID             =  1
    COL_DATE           =  2
    COL_CONFIDENCE     =  3
    COL_PRIV           =  4    
    COL_TAGS           =  5    
    COL_CHAN           =  6    
    COL_SRC_AUTH       =  7
    COL_SRC_ABBR       =  8
    COL_SRC_PINFO      =  9
    # column definitions
    COLUMNS = [
        (_('Source: Title or Citation: Volume/Page'), TEXT, None),
        (_('ID'), TEXT, None),
        (_('Date'), MARKUP, None),
        (_('Confidence'), TEXT, None),
        (_('Private'), ICON, 'gramps-lock'),
        (_('Tags'), TEXT, None),
        (_('Last Changed'), TEXT, None),
        (_('Source: Author'), TEXT, None),
        (_('Source: Abbreviation'), TEXT, None),
        (_('Source: Publication Information'), TEXT, None),
        ]
    COLUMN_FILTERABLE = [
        COL_TITLE_PAGE, 
        COL_ID,
        COL_CHAN,
        COL_SRC_AUTH,
        COL_SRC_ABBR,
        COL_SRC_PINFO
        ]
    # default setting with visible columns, order of the col, and their size
    CONFIGSETTINGS = (
        ('columns.visible', [COL_TITLE_PAGE, COL_ID, COL_SRC_AUTH,
                             COL_SRC_PINFO]),
        ('columns.rank', [COL_TITLE_PAGE, COL_ID, COL_DATE, COL_CONFIDENCE,
                          COL_PRIV, COL_TAGS, COL_CHAN, COL_SRC_AUTH,
                          COL_SRC_ABBR, COL_SRC_PINFO]),
        ('columns.size', [200, 75, 100, 75, 40, 100, 100, 150, 100, 150])
        )    
    ADD_MSG = _("Add a new citation and a new source")
    ADD_SOURCE_MSG = _("Add a new source")
    ADD_CITATION_MSG = _("Add a new citation to an existing source")
    EDIT_MSG = _("Edit the selected citation or source")
    DEL_MSG = _("Delete the selected citation or source")
    MERGE_MSG = _("Merge the selected citations or selected sources")
    FILTER_TYPE = "Citation"
    QR_CATEGORY = CATEGORY_QR_SOURCE_OR_CITATION
    
    def __init__(self, pdata, dbstate, uistate, nav_group=0):
        
        signal_map = {
            'citation-add'     : self._citation_row_add,
            'citation-update'  : self._citation_row_update,
            'citation-delete'  : self._citation_row_delete,
            'citation-rebuild' : self._citation_object_build,
            'source-add'       : self._source_row_add,
            'source-update'    : self._source_row_update,
            'source-delete'    : self._source_row_delete,
            'source-rebuild'   : self._source_object_build,
            }

        ListView.__init__(
            self, _('Citation Tree View'), pdata, dbstate, uistate, 
            CitationTreeModel, signal_map,
            CitationBookmarks, nav_group,
            multiple=True,
            filter_class=SourceSidebarFilter)

        self.func_list.update({
            '<PRIMARY>J' : self.jump,
            '<PRIMARY>BackSpace' : self.key_delete,
            })

        self.additional_uis.append(self.additional_ui())

    # Override change_active from NavigationView, so that only Citations can be
    # put in the history list for the CitationTreeView
    def change_active(self, handle):
        if self.dbstate.db.get_citation_from_handle(handle):
            super(CitationTreeView, self).change_active(handle)
        else:
            # FIXME: See http://www.gramps-project.org/bugs/view.php?id=6352 a
            # more comprehensive solution is needed in the long term. See also
            # add in Bookmarks.CitationBookmarks
            pass
    
    def setup_filter(self):
        """
        Override the setup of the default Search Bar in listview, so that only
        the searchable source fields are shown.
        """
             
        self.search_bar.setup_filter(
            [(self.COLUMNS[pair[1]][0], pair[1], pair[1] in self.exact_search())
                for pair in self.column_order() if pair[0] and 
                                pair[1] in self.COLUMN_FILTERABLE])

    def _print_handles(self, text, handle_list):
        for handle in handle_list:
            source = self.dbstate.db.get_source_from_handle(handle)
            citation = self.dbstate.db.get_citation_from_handle(handle)
            _LOG.debug("\n\n\n")
            if source:
                _LOG.debug("---- %s -- source %s" % 
                           (text, source.get_title()))
            elif citation:
                _LOG.debug("---- %s -- citation %s" % 
                           (text, citation.get_page()))
            else:
                _LOG.debug("---- %s -- handle %s" % (text, handle))
   
    def _citation_row_add(self, handle_list):            
        self._print_handles("citation row add", handle_list)
        self.row_add(handle_list)
    
    def _citation_row_update(self, handle_list):            
        self._print_handles("citation row update", handle_list)
        self.row_update(handle_list)
    
    def _citation_row_delete(self, handle_list):            
        self._print_handles("citation row delete", handle_list)
        self.row_delete(handle_list)
    
    def _citation_object_build(self, *args):            
        _LOG.debug("citation object build")
        self.object_build(*args)
    
    def _source_row_add(self, handle_list):            
        self._print_handles("source row add", handle_list)
        self.row_add(handle_list)
    
    def _source_row_update(self, handle_list):            
        self._print_handles("source row update", handle_list)
        self.row_update(handle_list)
    
    def _source_row_delete(self, handle_list):            
        self._print_handles("source row delete", handle_list)
        self.row_delete(handle_list)
    
    def _source_object_build(self, *args):            
        _LOG.debug("source object build")
        self.object_build(*args)
    
    def navigation_type(self):
        return 'Citation'

    def drag_info(self):
        # Since drag only needs to work when just one row is selected, ideally,
        # this should just return SOURCE_LINK if one source is selected and
        # CITATION_LINK if one citation is selected, and probably None
        # otherwise. However, this doesn't work. Drag and drop failed to work at
        # all for citationtree view, and I think this was because None is
        # returned during initialisation. There is also a problem where it seems
        # at some point during a citation merge, neither a Source nor a Citation
        # is selected. Hence the simplistic solution implemented below, where
        # CITATION_LINK is always returned except when it is obviously correct
        # to return SOURCE_LINK.
        
        selection = self.selected_handles()
        if len(selection) == 1 and \
            self.dbstate.db.get_source_from_handle(selection[0]):
                return DdTargets.SOURCE_LINK
        else:
            return DdTargets.CITATION_LINK
    
    def get_stock(self):
        return 'gramps-citation'

    def get_viewtype_stock(self):
        """
        Override the default icon.  Set for hierarchical view.
        """
        return 'gramps-tree-group'
        
    def define_actions(self):
        """
        This defines the possible actions for the citation views.
        Possible actions are:
        add_source: Add a new source (this is also available from the
                      source view)
        add:        Add a new citation and a new source (this can also be done 
                      by source view add a source, then citation view add a new 
                      citation to an existing source)
        share:      Add a new citation to an existing source (when a source is
                      selected)
        edit:       Edit a source or a citation.
        merge:      Merge the selected sources or citations.
        remove:     Delete the selected sources or citations.
        
        
        """
        ListView.define_actions(self)

        self._add_action('Add source', 'gramps-source', _("Add source..."), 
                         accel=None, 
                         tip=self.ADD_SOURCE_MSG, 
                         callback=self.add_source)
        self._add_action('Add citation', 'gramps-citation', 
                         _("Add citation..."), 
                         accel=None, 
                         tip=self.ADD_CITATION_MSG, 
                         callback=self.share)
        
        self.all_action = Gtk.ActionGroup(name=self.title + "/CitationAll")
        self.edit_action = Gtk.ActionGroup(name=self.title + "/CitationEdit")

        self._add_action('FilterEdit', None, _('Citation Filter Editor'),
                         callback=self.filter_editor,)
        self._add_action('QuickReport', None, _("Quick View"), None, None, None)

        self._add_action_group(self.edit_action)
        self._add_action_group(self.all_action)

        self.all_action.add_actions([
                ('OpenAllNodes', None, _("Expand all Nodes"), None, None, 
                 self.open_all_nodes),  
                ('CloseAllNodes', None, _("Collapse all Nodes"), None, None, 
                 self.close_all_nodes), 
                ])

    def additional_ui(self):
        """
        Defines the UI string for UIManager
        """
        return '''<ui>
          <menubar name="MenuBar">
            <menu action="FileMenu">
              <placeholder name="LocalExport">
                <menuitem action="ExportTab"/>
              </placeholder>
            </menu>
            <menu action="BookMenu">
              <placeholder name="AddEditBook">
                <menuitem action="AddBook"/>
                <menuitem action="EditBook"/>
              </placeholder>
            </menu>
            <menu action="GoMenu">
              <placeholder name="CommonGo">
                <menuitem action="Back"/>
                <menuitem action="Forward"/>
              </placeholder>
            </menu>
            <menu action="EditMenu">
              <placeholder name="CommonEdit">
                <menuitem action="Add"/>
                <menuitem action="Add source"/>
                <menuitem action="Add citation"/>
                <menuitem action="Edit"/>
                <menuitem action="Remove"/>
                <menuitem action="Merge"/>
             </placeholder>
              <menuitem action="FilterEdit"/>
            </menu>
          </menubar>
          <toolbar name="ToolBar">
            <placeholder name="CommonNavigation">
              <toolitem action="Back"/>  
              <toolitem action="Forward"/>  
            </placeholder>
            <placeholder name="CommonEdit">
              <toolitem action="Add"/>
              <toolitem action="Add source"/>
              <toolitem action="Add citation"/>
              <toolitem action="Edit"/>
              <toolitem action="Remove"/>
              <toolitem action="Merge"/>
            </placeholder>
          </toolbar>
          <popup name="Popup">
            <menuitem action="Back"/>
            <menuitem action="Forward"/>
            <separator/>
            <menuitem action="OpenAllNodes"/>
            <menuitem action="CloseAllNodes"/>
            <separator/>
            <menuitem action="Add"/>
            <menuitem action="Add citation"/>
            <menuitem action="Edit"/>
            <menuitem action="Remove"/>
            <menuitem action="Merge"/>
            <separator/>
            <menu name="QuickReport" action="QuickReport"/>
          </popup>
        </ui>'''

    def add_source(self, obj):
        """
        add_source: Add a new source (this is also available from the
                      source view)
        
        Create a new Source instance and call the EditSource editor with the
        new source. 
        
        Called when the Add_source button is clicked. 
        If the window already exists (WindowActiveError), we ignore it. 
        This prevents the dialog from coming up twice on the same object.
        
        However, since the window is identified by the Source object, and
        we have just created a new one, it seems to be impossible for the 
        window to already exist, so this is just an extra safety measure.
        """
        try:
            EditSource(self.dbstate, self.uistate, [], Source())
        except WindowActiveError:
            pass

    def add(self, obj):
        """
        add:        Add a new citation and a new source (this can also be done 
                      by source view add a source, then citation view add a new 
                      citation to an existing source)
        
        Create a new Source instance and Citation instance and call the 
        EditSource editor with the new source. 
        
        Called when the Add button is clicked. 
        If the window already exists (WindowActiveError), we ignore it. 
        This prevents the dialog from coming up twice on the same object.
        
        However, since the window is identified by the Source object, and
        we have just created a new one, it seems to be impossible for the 
        window to already exist, so this is just an extra safety measure.
        """
        try:
            EditCitation(self.dbstate, self.uistate, [], Citation(),
                         Source())
        except WindowActiveError:
            pass

    def share(self, obj):
        """
        share:      Add a new citation to an existing source (when a source is
                      selected)
        """
        for handle in self.selected_handles():
            # The handle will either be a Source handle or a Citation handle
            source = self.dbstate.db.get_source_from_handle(handle)
            citation = self.dbstate.db.get_citation_from_handle(handle)
            if (not source and not citation) or (source and citation):
                raise ValueError("selection must be either source or citation")
            if source:
                try:
                    EditCitation(self.dbstate, self.uistate, [], 
                                 Citation(), source)
                except WindowActiveError:
                    from gramps.gui.dialog import WarningDialog
                    WarningDialog(_("Cannot share this reference"),
                                  self.__blocked_text())
            else:
                msg = _("Cannot add citation.")
                msg2 = _("In order to add a citation to an existing source, "
                         " you must select a source.")
                ErrorDialog(msg, msg2)
#    
    def remove(self, obj):
        self.remove_selected_objects()

    def remove_object_from_handle(self, handle):
        # The handle will either be a Source handle or a Citation handle
        source = self.dbstate.db.get_source_from_handle(handle)
        citation = self.dbstate.db.get_citation_from_handle(handle)
        if (not source and not citation) or (source and citation):
            raise ValueError("selection must be either source or citation")
        if citation:
            the_lists = get_citation_referents(handle, self.dbstate.db)
            object = self.dbstate.db.get_citation_from_handle(handle)
            query = DeleteCitationQuery(self.dbstate, self.uistate, object, 
                                        the_lists)
            is_used = any(the_lists)
            return (query, is_used, object)
        else:
            the_lists = get_source_and_citation_referents(handle, 
                                                                self.dbstate.db)
            LOG.debug('the_lists %s' % [the_lists])    
    
            object = self.dbstate.db.get_source_from_handle(handle)
            query = DeleteSrcQuery(self.dbstate, self.uistate, object, 
                                   the_lists)
            is_used = any(the_lists)
            return (query, is_used, object)

    def edit(self, obj):
        """
        Edit either a Source or a Citation, depending on user selection
        """
        for handle in self.selected_handles():
            # The handle will either be a Source handle or a Citation handle
            source = self.dbstate.db.get_source_from_handle(handle)
            citation = self.dbstate.db.get_citation_from_handle(handle)
            if (not source and not citation) or (source and citation):
                raise ValueError("selection must be either source or citation")
            if citation:
                try:
                    EditCitation(self.dbstate, self.uistate, [], citation)
                except WindowActiveError:
                    pass
            else: # FIXME need try block here
                try:
                    EditSource(self.dbstate, self.uistate, [], source)
                except WindowActiveError:
                    from gramps.gui.dialog import WarningDialog
                    WarningDialog(_("Cannot share this reference"),
                                  self.__blocked_text2())

    def __blocked_text(self):
        """
        Return the common text used when citation cannot be edited
        """
        return _("This citation cannot be created at this time. "
                    "Either the associated Source object is already being "
                    "edited, or another citation associated with the same "
                    "source is being edited.\n\nTo edit this "
                    "citation, you need to close the object.")

    def __blocked_text2(self):
        """
        Return the common text used when citation cannot be edited
        """
        return _("This source cannot be edited at this time. "
                    "Either the associated Source object is already being "
                    "edited, or another citation associated with the same "
                    "source is being edited.\n\nTo edit this "
                    "source, you need to close the object.")

    def merge(self, obj):
        """
        Merge the selected citations.
        """
        mlist = self.selected_handles()
        
        if len(mlist) != 2:
            msg = _("Cannot merge citations.")
            msg2 = _("Exactly two citations must be selected to perform a "
                     "merge. A second citation can be selected by holding "
                     "down the control key while clicking on the desired "
                     "citation.")
            ErrorDialog(msg, msg2)
        else:
            source1 = self.dbstate.db.get_source_from_handle(mlist[0])
            citation1 = self.dbstate.db.get_citation_from_handle(mlist[0])
            if (not source1 and not citation1) or (source1 and citation1):
                raise ValueError("selection must be either source or citation")
            
            source2 = self.dbstate.db.get_source_from_handle(mlist[1])
            citation2 = self.dbstate.db.get_citation_from_handle(mlist[1])
            if (not source2 and not citation2) or (source2 and citation2):
                raise ValueError("selection must be either source or citation")
            
            if citation1 and citation2:
                if not citation1.get_reference_handle()  == \
                                citation2.get_reference_handle():         
                    msg = _("Cannot merge citations.")
                    msg2 = _("The two selected citations must have the same "
                             "source to perform a merge. If you want to merge "
                             "these two citations, then you must merge the "
                             "sources first.")
                    ErrorDialog(msg, msg2)
                else:
                    MergeCitation(self.dbstate, self.uistate,  mlist[0], 
                                  mlist[1])
            elif source1 and source2:
                MergeSource(self.dbstate, self.uistate, mlist[0], mlist[1])
            else:
                msg = _("Cannot perform merge.")
                msg2 = _("Both objects must be of the same type, either "
                         "both must be sources, or both must be "
                         "citations.")
                ErrorDialog(msg, msg2)

    def get_handle_from_gramps_id(self, gid):
        obj = self.dbstate.db.get_citation_from_gramps_id(gid)
        if obj:
            return obj.get_handle()
        else:
            return None

    def tag_updated(self, handle_list):
        """
        Update tagged rows when a tag color changes.
        """
        all_links = set([])
        for tag_handle in handle_list:
            links = set([link[1] for link in
                         self.dbstate.db.find_backlink_handles(tag_handle,
                                                include_classes='Citation')])
            all_links = all_links.union(links)
        self.row_update(list(all_links))

    def add_tag(self, transaction, handle, tag_handle):
        """
        Add the given tag to the given source or citation.
        """
        citation = self.dbstate.db.get_citation_from_handle(handle)
        if citation:
            citation.add_tag(tag_handle)
            self.dbstate.db.commit_citation(citation, transaction)
        else:
            source = self.dbstate.db.get_source_from_handle(handle)
            source.add_tag(tag_handle)
            self.dbstate.db.commit_source(source, transaction)

    def get_default_gramplets(self):
        """
        Define the default gramplets for the sidebar and bottombar.
        """
        return (("Citation Filter",),
                ("Citation Gallery",
                 "Citation Notes",
                 "Citation Backlinks"))

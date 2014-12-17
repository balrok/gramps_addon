#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
# Copyright (C) 2009       Gary Burton
# Copyright (C) 2011       Tim G L Lyons
# Copyright (C) 2011,2014  Nick Hall
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
EditCitation class for Gramps.
"""

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
import logging
LOG = logging.getLogger(".citation")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import Citation, NoteType, Source
from gramps.gen.db import DbTxn
from .editprimary import EditPrimary
from .objectentries import SourceEntry
from .displaytabs import (NoteTab, GalleryTab, SrcAttrEmbedList,
                          CitationBackRefList)
from ..widgets import (MonitoredEntry, PrivacyButton, MonitoredMenu,
                       MonitoredDate, MonitoredTagList)
from ..dialog import ErrorDialog
from ..glade import Glade

#-------------------------------------------------------------------------
#
# EditCitationclass
#
#-------------------------------------------------------------------------

class EditCitation(EditPrimary):
    """
    Create an EditCitation window. Associate a citation with the window.
    
    This class is called both to edit the Citation Primary object
    and to edit references from other objects to citations.
    It is called from ..editors.__init__ for editing the primary object
    and is called from CitationEmbedList for editing references
    
    @param callertitle: Text passed by calling object to add to title 
    @type callertitle: str
    """

    def __init__(self, dbstate, uistate, track, obj, source=None, callback=None,
                 callertitle = None):
        """
        The obj parameter is mandatory. If the source parameter is not 
        provided, it will be deduced from the obj Citation object.
        """
        if source:
            obj.set_reference_handle(source.get_handle())
        self.callertitle = callertitle
        EditPrimary.__init__(self, dbstate, uistate, track, obj, 
                             dbstate.db.get_citation_from_handle, 
                             dbstate.db.get_citation_from_gramps_id, callback)

    def empty_object(self):
        """
        Return an empty Citation object for comparison for changes.
        
        It is used by the base class L{EditPrimary}.
        """
        return Citation()

    def get_menu_title(self):
        """
        Construct the menu title, which may include the name of the object that
        contains a reference to this citation.
        """
        title = self.obj.get_page()
        if title:
            if self.callertitle:
                title = _('Citation') + \
                        (': %(id)s - %(context)s' % {
                         'id'      : title,
                         'context' : self.callertitle
                         })
            else:
                title = _('Citation') + ": " + title
        else:
            if self.callertitle:
                title = _('New Citation') + \
                        (': %(id)s - %(context)s' % {
                         'id'      : title,
                         'context' : self.callertitle
                         })
            else:     
                title = _('New Citation')
        return title

    def _local_init(self):
        """
        Local initialization function.
        
        Perform basic initialization, including setting up widgets
        and the glade interface. It is called by the base class L{EditPrimary},
        and overridden here.
        """
        self.width_key = 'interface.citation-width'
        self.height_key = 'interface.citation-height'
        
        self.glade = Glade()
        self.set_window(self.glade.toplevel, None, 
                        self.get_menu_title())
        
        self.share_btn = self.glade.get_object('select_source')
        self.add_del_btn = self.glade.get_object('add_del_source')

    def _connect_signals(self):
        """
        Connects any signals that need to be connected.
        
        Called by the init routine of the base class L{EditPrimary}.
        """
        self.define_ok_button(self.glade.get_object('ok'), self.save)
        self.define_cancel_button(self.glade.get_object('cancel'))
        self.define_help_button(self.glade.get_object('help'))

    def _connect_db_signals(self):
        """
        Connect any signals that need to be connected. 
        Called by the init routine of the base class (_EditPrimary).
                
        What this code does is to check that the object edited is not deleted
        whilst editing it.  If the object is deleted we need to close the editor
        windows and clean up.  If the database emits a rebuild signal for the
        database object type we also abort the edit.
        """
        
        self._add_db_signal('citation-rebuild', self._do_close)
        self._add_db_signal('citation-delete', self.check_for_close)

    def _setup_fields(self):
        """
        Get control widgets and attach them to Citation's attributes.
        """
        self.source_field = SourceEntry(self.dbstate, self.uistate, self.track,
                                      self.glade.get_object("source"),
                                      self.obj.set_reference_handle,
                                      self.obj.get_reference_handle,
                                      self.add_del_btn, self.share_btn,
                                      callback=self.source_changed)
        
        self.date = MonitoredDate(
            self.glade.get_object("date_entry"),
            self.glade.get_object("date_stat"), 
            self.obj.get_date_object(),
            self.uistate,
            self.track,
            self.db.readonly)

        self.gid = MonitoredEntry(
            self.glade.get_object('gid'), self.obj.set_gramps_id,
            self.obj.get_gramps_id,self.db.readonly)

        self.volume = MonitoredEntry(
            self.glade.get_object("volume"), self.obj.set_page,
            self.obj.get_page, self.db.readonly)
        
        self.type_mon = MonitoredMenu(
            self.glade.get_object('confidence'),
            self.obj.set_confidence_level,
            self.obj.get_confidence_level, [
            (_('Very Low'), Citation.CONF_VERY_LOW),
            (_('Low'), Citation.CONF_LOW),
            (_('Normal'), Citation.CONF_NORMAL),
            (_('High'), Citation.CONF_HIGH),
            (_('Very High'), Citation.CONF_VERY_HIGH)],
            self.db.readonly)

        self.tags2 = MonitoredTagList(
            self.glade.get_object("tag_label"), 
            self.glade.get_object("tag_button"), 
            self.obj.set_tag_list, 
            self.obj.get_tag_list,
            self.db,
            self.uistate, self.track,
            self.db.readonly)

        self.ref_privacy = PrivacyButton(
            self.glade.get_object('privacy'), self.obj, self.db.readonly)

    def _create_tabbed_pages(self):
        """
        Create the notebook tabs and inserts them into the main
        window.
        """
        notebook = Gtk.Notebook()

        self.note_tab = NoteTab(self.dbstate, self.uistate, self.track,
                    self.obj.get_note_list(), self.get_menu_title(),
                    notetype=NoteType.CITATION)
        self._add_tab(notebook, self.note_tab)
        self.track_ref_for_deletion("note_tab")

        self.gallery_tab = GalleryTab(self.dbstate, self.uistate, self.track,
                       self.obj.get_media_list())
        self._add_tab(notebook, self.gallery_tab)
        self.track_ref_for_deletion("gallery_tab")
            
        self.attr_tab = SrcAttrEmbedList(self.dbstate, self.uistate, self.track,
                          self.obj.get_attribute_list())
        self._add_tab(notebook, self.attr_tab)
        self.track_ref_for_deletion("attr_tab")
            
        self.citationref_list = CitationBackRefList(self.dbstate, self.uistate, 
                              self.track,
                              self.db.find_backlink_handles(self.obj.handle))
        self._add_tab(notebook, self.citationref_list)
        self.track_ref_for_deletion("citationref_list")

        self._setup_notebook_tabs(notebook)

        notebook.show_all()
        self.glade.get_object('vbox').pack_start(notebook, True, True, 0)

    def source_changed(self):
        handle = self.obj.get_reference_handle()
        if handle:
            source = self.db.get_source_from_handle(handle)
            author = source.get_author()
        else:
            author = ''
        self.glade.get_object("author").set_text(author)

    def build_menu_names(self, source):
        """
        Provide the information needed by the base class to define the
        window management menu entries.
        """
        return (_('Edit Citation'), self.get_menu_title())        

    def save(self, *obj):
        """
        Save the data.
        """
        self.ok_button.set_sensitive(False)
        if not self.obj.get_reference_handle():
            ErrorDialog(_("No source selected"),
                        _("A source is anything (personal testimony, "
                          "video recording, photograph, newspaper column, "
                          "gravestone...) from which information can be "
                          "derived. To create a citation, first select the "
                          "required source, and then record the location of "
                          "the information referenced within the source in the "
                          "'Volume/Page' field."))
            self.ok_button.set_sensitive(True)
            return
        
        (uses_dupe_id, gramps_id) = self._uses_duplicate_id()
        if uses_dupe_id:
            prim_object = self.get_from_gramps_id(gramps_id)
            name = prim_object.get_page()
            msg1 = _("Cannot save citation. ID already exists.")
            msg2 = _("You have attempted to use the existing Gramps ID with "
                     "value %(id)s. This value is already used by '" 
                     "%(prim_object)s'. Please enter a different ID or leave "
                     "blank to get the next available ID value.") % {
                         'id' : gramps_id, 'prim_object' : name }
            ErrorDialog(msg1, msg2)
            self.ok_button.set_sensitive(True)
            return

        with DbTxn('', self.db) as trans:
            if not self.obj.get_handle():
                self.db.add_citation(self.obj, trans)
                msg = _("Add Citation (%s)") % self.obj.get_page()
            else:
                if not self.obj.get_gramps_id():
                    self.obj.set_gramps_id(
                                    self.db.find_next_citation_gramps_id())
                self.db.commit_citation(self.obj, trans)
                msg = _("Edit Citation (%s)") % self.obj.get_page()
            trans.set_description(msg)
                        
        if self.callback:
            self.callback(self.obj.get_handle())
        self.close()

    def data_has_changed(self):
        """
        A date comparison can fail incorrectly because we have made the
        decision to store entered text in the date. However, there is no
        entered date when importing from a XML file, so we can get an
        incorrect fail.
        """
        if self.db.readonly:
            return False
        elif self.obj.handle:
            orig = self.get_from_handle(self.obj.handle)
            if orig:
                cmp_obj = orig
            else:
                cmp_obj = self.empty_object()
            return cmp_obj.serialize(True)[1:] != self.obj.serialize(True)[1:]
        else:
            cmp_obj = self.empty_object()
            return cmp_obj.serialize(True)[1:] != self.obj.serialize()[1:]

class DeleteCitationQuery(object):
    def __init__(self, dbstate, uistate, citation, the_lists):
        self.citation = citation
        self.db = dbstate.db
        self.uistate = uistate
        self.the_lists = the_lists

    def query_response(self):
        with DbTxn(_("Delete Citation (%s)") % self.citation.get_page(),
                   self.db) as trans:
            self.db.disable_signals()
        
            (person_list, family_list, event_list, place_list, source_list, 
             media_list, repo_list) = self.the_lists

            ctn_handle_list = [self.citation.get_handle()]

            for handle in person_list:
                person = self.db.get_person_from_handle(handle)
                person.remove_citation_references(ctn_handle_list)
                self.db.commit_person(person, trans)

            for handle in family_list:
                family = self.db.get_family_from_handle(handle)
                family.remove_citation_references(ctn_handle_list)
                self.db.commit_family(family, trans)

            for handle in event_list:
                event = self.db.get_event_from_handle(handle)
                event.remove_citation_references(ctn_handle_list)
                self.db.commit_event(event, trans)

            for handle in place_list:
                place = self.db.get_place_from_handle(handle)
                place.remove_citation_references(ctn_handle_list)
                self.db.commit_place(place, trans)

            for handle in source_list:
                source = self.db.get_source_from_handle(handle)
                source.remove_citation_references(ctn_handle_list)
                self.db.commit_source(source, trans)

            for handle in media_list:
                media = self.db.get_object_from_handle(handle)
                media.remove_citation_references(ctn_handle_list)
                self.db.commit_media_object(media, trans)

            for handle in repo_list:
                repo = self.db.get_repository_from_handle(handle)
                repo.remove_citation_references(ctn_handle_list)
                self.db.commit_repository(repo, trans)

            self.db.enable_signals()
            self.db.remove_citation(self.citation.get_handle(), trans)

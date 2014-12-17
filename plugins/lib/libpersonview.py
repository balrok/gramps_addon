# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Gary Burton
# Copyright (C) 2009-2010  Nick Hall
# Copyright (C) 2010       Benny Malengier
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
Provide the base for a list person view.
"""

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger(".gui.personview")

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import Person, Surname
from gramps.gen.db import DbTxn
from gramps.gui.views.listview import ListView, TEXT, MARKUP, ICON
from gramps.gen.utils.string import data_recover_msg
from gramps.gen.display.name import displayer as name_displayer
from gramps.gui.dialog import ErrorDialog, QuestionDialog
from gramps.gen.errors import WindowActiveError
from gramps.gui.views.bookmarks import PersonBookmarks
from gramps.gen.config import config
from gramps.gui.ddtargets import DdTargets
from gramps.gui.editors import EditPerson
from gramps.gui.filters.sidebar import PersonSidebarFilter
from gramps.gui.merge import MergePerson
from gramps.gen.plug import CATEGORY_QR_PERSON

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext

#-------------------------------------------------------------------------
#
# PersonView
#
#-------------------------------------------------------------------------
class BasePersonView(ListView):
    """
    Base view for PersonView listviews ListView, a treeview
    """
    COL_NAME = 0
    COL_ID = 1
    COL_GEN = 2
    COL_BDAT = 3
    COL_BPLAC = 4
    COL_DDAT = 5
    COL_DPLAC = 6
    COL_SPOUSE = 7
    COL_PARENTS = 8
    COL_MARRIAGES = 9
    COL_CHILDREN = 10
    COL_TODO = 11
    COL_PRIV = 12
    COL_TAGS = 13
    COL_CHAN = 14
    # column definitions
    COLUMNS = [
        (_('Name'), TEXT, None),
        (_('ID'), TEXT, None),
        (_('Gender'), TEXT, None),
        (_('Birth Date'), MARKUP, None),
        (_('Birth Place'), MARKUP, None),
        (_('Death Date'), MARKUP, None),
        (_('Death Place'), MARKUP, None),
        (_('Spouse'), TEXT, None),
        (_('Number of Parents'), TEXT, 'gramps-parents'),
        (_('Number of Marriages'), TEXT, 'gramps-family'),
        (_('Number of Children'), TEXT, 'gramps-relation'),
        (_('Number of To Do Notes'), TEXT, 'gramps-notes'),
        (_('Private'), ICON, 'gramps-lock'),
        (_('Tags'), TEXT, None),
        (_('Last Changed'), TEXT, None),
        ]
    # default setting with visible columns, order of the col, and their size
    CONFIGSETTINGS = (
        ('columns.visible', [COL_NAME, COL_ID, COL_GEN, COL_BDAT, COL_DDAT]),
        ('columns.rank', [COL_NAME, COL_ID, COL_GEN, COL_BDAT, COL_BPLAC,
                           COL_DDAT, COL_DPLAC, COL_SPOUSE, COL_PARENTS,
                           COL_MARRIAGES, COL_CHILDREN, COL_TODO, COL_PRIV,
                           COL_TAGS, COL_CHAN]),
        ('columns.size', [250, 75, 75, 100, 175, 100, 175, 100, 30, 30, 30, 30,
                          30, 100, 100])
        )  
    ADD_MSG     = _("Add a new person")
    EDIT_MSG    = _("Edit the selected person")
    DEL_MSG     = _("Remove the selected person")
    MERGE_MSG   = _("Merge the selected persons")
    FILTER_TYPE = "Person"
    QR_CATEGORY = CATEGORY_QR_PERSON

    def __init__(self, pdata, dbstate, uistate, title, model, nav_group=0):
        """
        Create the Person View
        """
        signal_map = {
            'person-add'     : self.row_add,
            'person-update'  : self.row_update,
            'person-delete'  : self.row_delete,
            'person-rebuild' : self.object_build,
            'person-groupname-rebuild' : self.object_build,
            'no-database': self.no_database,
            }
 
        ListView.__init__(
            self, title, pdata, dbstate, uistate,
            model, signal_map,
            PersonBookmarks, nav_group,
            multiple=True,
            filter_class=PersonSidebarFilter)
            
        self.func_list.update({
            '<PRIMARY>J' : self.jump,
            '<PRIMARY>BackSpace' : self.key_delete,
            })

        uistate.connect('nameformat-changed', self.build_tree)

        self.additional_uis.append(self.additional_ui())

    def navigation_type(self):
        """
        Return the navigation type of the view.
        """
        return 'Person'

    def drag_info(self):
        """
        Specify the drag type for a single selection
        """
        return DdTargets.PERSON_LINK
        
    def exact_search(self):
        """
        Returns a tuple indicating columns requiring an exact search
        'female' contains the string 'male' so we need an exact search
        """
        return (BasePersonView.COL_GEN,)

    def get_stock(self):
        """
        Use the grampsperson stock icon
        """
        return 'gramps-person'

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
                <separator/>
                <menuitem action="HomePerson"/>
                <separator/>
              </placeholder>
            </menu>
            <menu action="EditMenu">
              <placeholder name="CommonEdit">
                <menuitem action="Add"/>
                <menuitem action="Edit"/>
                <menuitem action="Remove"/>
                <menuitem action="Merge"/>
              </placeholder>
              <menuitem action="SetActive"/>
              <menuitem action="FilterEdit"/>
            </menu>
          </menubar>
          <toolbar name="ToolBar">
            <placeholder name="CommonNavigation">
              <toolitem action="Back"/>
              <toolitem action="Forward"/>  
              <toolitem action="HomePerson"/>
            </placeholder>
            <placeholder name="CommonEdit">
              <toolitem action="Add"/>
              <toolitem action="Edit"/>
              <toolitem action="Remove"/>
              <toolitem action="Merge"/>
            </placeholder>
          </toolbar>
          <popup name="Popup">
            <menuitem action="Back"/>
            <menuitem action="Forward"/>
            <menuitem action="HomePerson"/>
            <separator/>
            <menuitem action="Add"/>
            <menuitem action="Edit"/>
            <menuitem action="Remove"/>
            <menuitem action="Merge"/>
            <separator/>
            <menu name="QuickReport" action="QuickReport"/>
            <menu name="WebConnect" action="WebConnect"/>
          </popup>
        </ui>'''

    def get_handle_from_gramps_id(self, gid):
        """
        Return the handle of the person having the given Gramps ID. 
        """
        obj = self.dbstate.db.get_person_from_gramps_id(gid)
        if obj:
            return obj.get_handle()
        else:
            return None

    def add(self, obj):
        """
        Add a new person to the database.
        """
        person = Person()
        #the editor requires a surname
        person.primary_name.add_surname(Surname())
        person.primary_name.set_primary_surname(0)
        
        try:
            EditPerson(self.dbstate, self.uistate, [], person)
        except WindowActiveError:
            pass
 
    def edit(self, obj):
        """
        Edit an existing person in the database.
        """
        for handle in self.selected_handles():
            person = self.dbstate.db.get_person_from_handle(handle)
            try:
                EditPerson(self.dbstate, self.uistate, [], person)
            except WindowActiveError:
                pass

    def remove(self, obj):
        """
        Remove a person from the database.
        """
        for sel in self.selected_handles():
            person = self.dbstate.db.get_person_from_handle(sel)
            self.active_person = person
            name = name_displayer.display(person) 

            msg = _('Deleting the person will remove the person '
                             'from the database.')
            msg = "%s %s" % (msg, data_recover_msg)
            QuestionDialog(_('Delete %s?') % name, 
                                          msg, 
                                          _('_Delete Person'), 
                                          self.delete_person_response)

    def delete_person_response(self):
        """
        Deletes the person from the database.
        """
        # set the busy cursor, so the user knows that we are working
        self.uistate.set_busy_cursor(True)

        # create the transaction
        with DbTxn('', self.dbstate.db) as trans:
        
            # create name to save
            person = self.active_person
            active_name = _("Delete Person (%s)") % name_displayer.display(person)

            # delete the person from the database
            # Above will emit person-delete, which removes the person via 
            # callback to the model, so row delete is signaled
            self.dbstate.db.delete_person_from_database(person, trans)
            trans.set_description(active_name)

        self.uistate.set_busy_cursor(False)

    def define_actions(self):
        """
        Required define_actions function for PageView. Builds the action
        group information required. We extend beyond the normal here, 
        since we want to have more than one action group for the PersonView.
        Most PageViews really won't care about this.

        Special action groups for Forward and Back are created to allow the
        handling of navigation buttons. Forward and Back allow the user to
        advance or retreat throughout the history, and we want to have these
        be able to toggle these when you are at the end of the history or
        at the beginning of the history.
        """

        ListView.define_actions(self)

        self.all_action = Gtk.ActionGroup(name=self.title + "/PersonAll")
        self.edit_action = Gtk.ActionGroup(name=self.title + "/PersonEdit")

        self.all_action.add_actions([
                ('FilterEdit', None, _('Person Filter Editor'), None, None,
                self.filter_editor),
                ('Edit', Gtk.STOCK_EDIT, _("action|_Edit..."),
                "<PRIMARY>Return", self.EDIT_MSG, self.edit), 
                ('QuickReport', None, _("Quick View"), None, None, None), 
                ('WebConnect', None, _("Web Connection"), None, None, None), 
                ])


        self.edit_action.add_actions(
            [
                ('Add', Gtk.STOCK_ADD, _("_Add..."), "<PRIMARY>Insert", 
                 self.ADD_MSG, self.add), 
                ('Remove', Gtk.STOCK_REMOVE, _("_Remove"), "<PRIMARY>Delete", 
                 self.DEL_MSG, self.remove),
                ('Merge', 'gramps-merge', _('_Merge...'), None,
                 self.MERGE_MSG, self.merge),
                ('ExportTab', None, _('Export View...'), None, None,
                 self.export), 
                ])

        self._add_action_group(self.edit_action)
        self._add_action_group(self.all_action)

    def enable_action_group(self, obj):
        """
        Turns on the visibility of the View's action group.
        """
        ListView.enable_action_group(self, obj)
        self.all_action.set_visible(True)
        self.edit_action.set_visible(True)
        self.edit_action.set_sensitive(not self.dbstate.db.readonly)
        
    def disable_action_group(self):
        """
        Turns off the visibility of the View's action group.
        """
        ListView.disable_action_group(self)

        self.all_action.set_visible(False)
        self.edit_action.set_visible(False)

    def merge(self, obj):
        """
        Merge the selected people.
        """
        mlist = self.selected_handles()

        if len(mlist) != 2:
            ErrorDialog(
        _("Cannot merge people"), 
        _("Exactly two people must be selected to perform a merge. "
          "A second person can be selected by holding down the "
          "control key while clicking on the desired person."))
        else:
            MergePerson(self.dbstate, self.uistate, mlist[0], mlist[1])

    def tag_updated(self, handle_list):
        """
        Update tagged rows when a tag color changes.
        """
        all_links = set([])
        for tag_handle in handle_list:
            links = set([link[1] for link in
                         self.dbstate.db.find_backlink_handles(tag_handle,
                                                    include_classes='Person')])
            all_links = all_links.union(links)
        self.row_update(list(all_links))

    def add_tag(self, transaction, person_handle, tag_handle):
        """
        Add the given tag to the given person.
        """
        person = self.dbstate.db.get_person_from_handle(person_handle)
        person.add_tag(tag_handle)
        self.dbstate.db.commit_person(person, transaction)
        
    def get_default_gramplets(self):
        """
        Define the default gramplets for the sidebar and bottombar.
        """
        return (("Person Filter",),
                ("Person Details",
                 "Person Gallery",
                 "Person Events",
                 "Person Children",
                 "Person Citations",
                 "Person Notes",
                 "Person Attributes",
                 "Person Backlinks"))

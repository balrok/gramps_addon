#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
#               2009       Gary Burton
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
The EditPersonRef module provides the EditPersonRef class. This provides a
mechanism for the user to edit address information.
"""

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

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
from gramps.gen.display.name import displayer as name_displayer
from .editsecondary import EditSecondary
from gramps.gen.lib import NoteType
from ..widgets import MonitoredEntry, PrivacyButton
from ..selectors import SelectorFactory
from .displaytabs import CitationEmbedList, NoteTab
from ..glade import Glade

#-------------------------------------------------------------------------
#
# EditPersonRef class
#
#-------------------------------------------------------------------------
class EditPersonRef(EditSecondary):
    """
    Displays a dialog that allows the user to edit a person reference.
    """

    def __init__(self, dbstate, uistate, track, addr, callback):
        """
        Displays the dialog box.

        parent - The class that called the PersonRef editor.
        addr - The address that is to be edited
        """
        EditSecondary.__init__(self, dbstate, uistate, track, addr, callback)

    def _local_init(self):
        self.width_key = 'interface.person-ref-width'
        self.height_key = 'interface.person-ref-height'
        
        self.top = Glade()
                
        self.set_window(self.top.toplevel,
                        self.top.get_object("title"),
                        _('Person Reference Editor'))
        self.person_label = self.top.get_object('person')

    def _setup_fields(self):

        if self.obj.ref:
            p = self.dbstate.db.get_person_from_handle(self.obj.ref)
            self.person_label.set_text(name_displayer.display(p))
        
        self.street = MonitoredEntry(
            self.top.get_object("relationship"),
            self.obj.set_relation,
            self.obj.get_relation,
            self.db.readonly)

        self.priv = PrivacyButton(
            self.top.get_object("private"),
            self.obj,
            self.db.readonly)

    def _connect_signals(self):
        #self.define_help_button(self.top.get_object('help'))
        self.define_cancel_button(self.top.get_object('cancel'))
        self.define_ok_button(self.top.get_object('ok'),self.save)
        self.top.get_object('select').connect('clicked',self._select_person)

    def _connect_db_signals(self):
        """
        Connect any signals that need to be connected. 
        Called by the init routine of the base class (_EditPrimary).
        """
        self._add_db_signal('person-rebuild', self.close)
        self._add_db_signal('person-delete', self.check_for_close)

    def check_for_close(self, handles):
        """
        Callback method for delete signals. 
        If there is a delete signal of the primary object we are editing, the
        editor (and all child windows spawned) should be closed
        """
        if self.obj.ref in handles:
            self.close()

    def _select_person(self, obj):
        SelectPerson = SelectorFactory('Person')

        sel = SelectPerson(self.dbstate, self.uistate, self.track)
        person = sel.run()

        if person:
            self.obj.ref = person.get_handle()
            self.person_label.set_text(name_displayer.display(person))

    def _create_tabbed_pages(self):
        """
        Create the notebook tabs and inserts them into the main
        window.
        """
        
        notebook = Gtk.Notebook()
        
        self.srcref_list = CitationEmbedList(self.dbstate, self.uistate,
                                             self.track, 
                                             self.obj.get_citation_list())
        self._add_tab(notebook, self.srcref_list)
        self.track_ref_for_deletion("srcref_list")

        self.note_tab = NoteTab(self.dbstate, self.uistate, self.track,
                                self.obj.get_note_list(),
                                notetype=NoteType.ASSOCIATION)
        self._add_tab(notebook, self.note_tab)
        self.track_ref_for_deletion("note_tab")

        self._setup_notebook_tabs(notebook)
        notebook.show_all()
        self.top.get_object('vbox').pack_start(notebook, True, True, 0)

    def build_menu_names(self, obj):
        return (_('Person Reference'),_('Person Reference Editor'))

    def save(self,*obj):
        """
        Called when the OK button is pressed. Gets data from the
        form and updates the Address data structure.
        """

        if self.obj.ref:
            if self.callback:
                self.callback(self.obj)
            self.callback = None
            self.close()
        else:
            from ..dialog import ErrorDialog

            ErrorDialog(
                _('No person selected'),
                _('You must either select a person or Cancel '
                  'the edit'))

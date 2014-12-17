#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2009       Gary Burton
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

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext

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
from gramps.gen.const import URL_MANUAL_PAGE
from gramps.gen.lib import Event, NoteType
from gramps.gen.db import DbTxn
from ..display import display_help
from .editprimary import EditPrimary
from .objectentries import PlaceEntry
from ..glade import Glade
from ..dialog import ErrorDialog
from .displaytabs import (CitationEmbedList, NoteTab, GalleryTab, 
                          EventBackRefList, EventAttrEmbedList)
from ..widgets import (MonitoredEntry, PrivacyButton, MonitoredDataType, 
                       MonitoredDate, MonitoredTagList)
from gramps.gen.utils.db import get_participant_from_event

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
WIKI_HELP_PAGE = '%s_-_Entering_and_Editing_Data:_Detailed_-_part_2' % URL_MANUAL_PAGE
WIKI_HELP_SEC = _('manual|Editing_Information_About_Events')

#-------------------------------------------------------------------------
#
# EditEvent class
#
#-------------------------------------------------------------------------
class EditEvent(EditPrimary):

    def __init__(self, dbstate, uistate, track, event, callback=None):

        EditPrimary.__init__(self, dbstate, uistate, track,
                             event, dbstate.db.get_event_from_handle, 
                             dbstate.db.get_event_from_gramps_id)

        self._init_event()

    def _init_event(self):
        if not self.db.readonly:
            self.commit_event = self.db.commit_event

    def empty_object(self):
        return Event()

    def get_menu_title(self):
        handle = self.obj.get_handle()
        if handle:
            who = get_participant_from_event(self.db, handle)
            desc = self.obj.get_description()
            event_name = self.obj.get_type()
            if desc:
                event_name = '%s - %s' % (event_name, desc)
            if who:
                event_name = '%s - %s' % (event_name, who)
            dialog_title = _('Event: %s')  % event_name
        else:
            dialog_title = _('New Event')
        return dialog_title

    def get_custom_events(self):
        return self.dbstate.db.get_event_types()

    def _local_init(self):
        self.width_key = 'interface.event-width'
        self.height_key = 'interface.event-height'

        self.top = Glade()
        self.set_window(self.top.toplevel, None, 
                        self.get_menu_title())

        self.place = self.top.get_object('place')
        self.share_btn = self.top.get_object('select_place')
        self.add_del_btn = self.top.get_object('add_del_place')

    def _connect_signals(self):
        self.top.get_object('button111').connect('clicked', self.close)
        self.top.get_object('button126').connect('clicked', self.help_clicked)

        self.ok_button = self.top.get_object('ok')
        self.ok_button.set_sensitive(not self.db.readonly)
        self.ok_button.connect('clicked', self.save)

    def _connect_db_signals(self):
        """
        Connect any signals that need to be connected. 
        Called by the init routine of the base class (_EditPrimary).
        """
        self._add_db_signal('event-rebuild', self._do_close)
        self._add_db_signal('event-delete', self.check_for_close)

    def _setup_fields(self):

        # place, select_place, add_del_place
        
        self.place_field = PlaceEntry(self.dbstate, self.uistate, self.track,
                                      self.top.get_object("place"),
                                      self.obj.set_place_handle,
                                      self.obj.get_place_handle,
                                      self.add_del_btn, self.share_btn)
        
        self.descr_field = MonitoredEntry(self.top.get_object("event_description"),
                                          self.obj.set_description,
                                          self.obj.get_description, 
                                          self.db.readonly)

        self.gid = MonitoredEntry(self.top.get_object("gid"),
                                  self.obj.set_gramps_id,
                                  self.obj.get_gramps_id, self.db.readonly)

        self.tags = MonitoredTagList(self.top.get_object("tag_label"), 
                                     self.top.get_object("tag_button"), 
                                     self.obj.set_tag_list, 
                                     self.obj.get_tag_list,
                                     self.db,
                                     self.uistate, self.track,
                                     self.db.readonly)

        self.priv = PrivacyButton(self.top.get_object("private"),
                                  self.obj, self.db.readonly)

        self.event_menu = MonitoredDataType(self.top.get_object("personal_events"),
                                            self.obj.set_type,
                                            self.obj.get_type,
                                            custom_values=self.get_custom_events())

        self.date_field = MonitoredDate(self.top.get_object("date_entry"),
                                        self.top.get_object("date_stat"),
                                        self.obj.get_date_object(),
                                        self.uistate, self.track, 
                                        self.db.readonly)

    def _create_tabbed_pages(self):
        """
        Create the notebook tabs and inserts them into the main
        window.
        """
        notebook = Gtk.Notebook()

        self.citation_list = CitationEmbedList(self.dbstate,
                                               self.uistate,
                                               self.track,
                                               self.obj.get_citation_list(), 
                                               self.get_menu_title())
        self._add_tab(notebook, self.citation_list)
        
        self.note_list = NoteTab(self.dbstate,
                                 self.uistate,
                                 self.track,
                                 self.obj.get_note_list(),
                                 notetype=NoteType.EVENT)
        self._add_tab(notebook, self.note_list)
        

        self.gallery_list = GalleryTab(self.dbstate,
                                       self.uistate,
                                       self.track,
                                       self.obj.get_media_list())
        self._add_tab(notebook, self.gallery_list)

        self.attr_list = EventAttrEmbedList(self.dbstate,
                                            self.uistate,
                                            self.track,
                                            self.obj.get_attribute_list())
        self._add_tab(notebook, self.attr_list)

        handle_list = self.dbstate.db.find_backlink_handles(self.obj.handle)
        self.backref_list = EventBackRefList(self.dbstate,
                                             self.uistate,
                                             self.track,
                                             handle_list)
        self._add_tab(notebook, self.backref_list)

        self._setup_notebook_tabs(notebook)
        
        notebook.show_all()
        self.top.get_object('vbox').pack_start(notebook, True, True, 0)

        self.track_ref_for_deletion("citation_list")
        self.track_ref_for_deletion("note_list")
        self.track_ref_for_deletion("gallery_list")
        self.track_ref_for_deletion("attr_list")
        self.track_ref_for_deletion("backref_list")

    def build_menu_names(self, event):
        return (_('Edit Event'), self.get_menu_title())

    def help_clicked(self, obj):
        """Display the relevant portion of GRAMPS manual"""
        display_help(webpage=WIKI_HELP_PAGE, section=WIKI_HELP_SEC)
    def save(self, *obj):
        self.ok_button.set_sensitive(False)
        if self.object_is_empty():
            ErrorDialog(_("Cannot save event"),
                        _("No data exists for this event. Please "
                          "enter data or cancel the edit."))
            self.ok_button.set_sensitive(True)
            return
        
        (uses_dupe_id, id) = self._uses_duplicate_id()
        if uses_dupe_id:
            prim_object = self.get_from_gramps_id(id)
            name = prim_object.get_description()
            msg1 = _("Cannot save event. ID already exists.")
            msg2 = _("You have attempted to use the existing Gramps ID with "
                         "value %(id)s. This value is already used by '" 
                         "%(prim_object)s'. Please enter a different ID or leave "
                         "blank to get the next available ID value.") % {
                         'id' : id, 'prim_object' : name }
            ErrorDialog(msg1, msg2)
            self.ok_button.set_sensitive(True)
            return

        t = self.obj.get_type()
        if t.is_custom() and str(t) == '':
            ErrorDialog(
                _("Cannot save event"),
                _("The event type cannot be empty"))
            self.ok_button.set_sensitive(True)
            return

        if not self.obj.handle:
            with DbTxn(_("Add Event (%s)") % self.obj.get_gramps_id(),
                       self.db) as trans:
                self.db.add_event(self.obj, trans)
        else:
            orig = self.get_from_handle(self.obj.handle)
            if self.obj.serialize() != orig.serialize():
                with DbTxn(_("Edit Event (%s)") % self.obj.get_gramps_id(),
                           self.db) as trans:
                    if not self.obj.get_gramps_id():
                        self.obj.set_gramps_id(self.db.find_next_event_gramps_id())
                    self.commit_event(self.obj, trans)

        if self.callback:
            self.callback(self.obj)
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

#-------------------------------------------------------------------------
#
# Delete Query class
#
#-------------------------------------------------------------------------
class DeleteEventQuery(object):
    def __init__(self, dbstate, uistate, event, person_list, family_list):
        self.event = event
        self.db = dbstate.db
        self.uistate = uistate
        self.person_list = person_list
        self.family_list = family_list

    def query_response(self):
        with DbTxn(_("Delete Event (%s)") % self.event.get_gramps_id(),
                   self.db) as trans:
            self.db.disable_signals()
        
            ev_handle_list = [self.event.get_handle()]

            for handle in self.person_list:
                person = self.db.get_person_from_handle(handle)
                person.remove_handle_references('Event', ev_handle_list)
                self.db.commit_person(person, trans)

            for handle in self.family_list:
                family = self.db.get_family_from_handle(handle)
                family.remove_handle_references('Event', ev_handle_list)
                self.db.commit_family(family, trans)

            self.db.enable_signals()
            self.db.remove_event(self.event.get_handle(), trans)

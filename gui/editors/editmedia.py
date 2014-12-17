#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
# Copyright (C) 2009       Gary Burton
# Copyright (C) 2010       Nick Hall
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
# Standard python modules
#
#-------------------------------------------------------------------------
import os
#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import Gdk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.constfunc import conv_to_unicode
from ..utils import open_file_with_default_application
from gramps.gen.lib import MediaObject, NoteType
from gramps.gen.db import DbTxn
from gramps.gen.mime import get_description, get_type
from ..thumbnails import get_thumbnail_image, find_mime_type_pixbuf
from gramps.gen.utils.file import (media_path_full, find_file, create_checksum)
from .editprimary import EditPrimary
from ..widgets import (MonitoredDate, MonitoredEntry, PrivacyButton,
                         MonitoredTagList)
from .displaytabs import (CitationEmbedList, MediaAttrEmbedList, NoteTab,
                         MediaBackRefList)
from .addmedia import AddMediaObject
from ..dialog import ErrorDialog
from ..glade import Glade

#-------------------------------------------------------------------------
#
# EditMedia
#
#-------------------------------------------------------------------------
class EditMedia(EditPrimary):

    def __init__(self, dbstate, uistate, track, obj, callback=None):

        EditPrimary.__init__(self, dbstate, uistate, track, obj,
                             dbstate.db.get_object_from_handle, 
                             dbstate.db.get_object_from_gramps_id, callback)
        if not self.obj.get_handle():
            #show the addmedia dialog immediately, with track of parent.
            AddMediaObject(dbstate, self.uistate, self.track, self.obj, 
                           self._update_addmedia)

    def empty_object(self):
        return MediaObject()

    def get_menu_title(self):
        if self.obj.get_handle():
            name = self.obj.get_description()
            if not name:
                name = self.obj.get_path()
            if not name:
                name = self.obj.get_mime_type()
            if not name:
                name = _('Note')
            dialog_title = _('Media: %s')  % name
        else:
            dialog_title = _('New Media')
        return dialog_title

    def _local_init(self):
        assert(self.obj)
        self.width_key = 'interface.media-width'
        self.height_key = 'interface.media-height'
        
        self.glade = Glade()
        self.set_window(self.glade.toplevel, 
                        None, self.get_menu_title())

    def _connect_signals(self):
        self.define_cancel_button(self.glade.get_object('button91'))
        self.define_ok_button(self.glade.get_object('ok'), self.save)
        self.define_help_button(self.glade.get_object('button102'))

    def _connect_db_signals(self):
        """
        Connect any signals that need to be connected. 
        Called by the init routine of the base class (_EditPrimary).
        """
        self._add_db_signal('media-rebuild', self._do_close)
        self._add_db_signal('media-delete', self.check_for_close)

    def _setup_fields(self):
        self.date_field = MonitoredDate(self.glade.get_object("date_entry"),
                                        self.glade.get_object("date_edit"),
                                        self.obj.get_date_object(),
                                        self.uistate, self.track,
                                        self.db.readonly)

        self.descr_window = MonitoredEntry(self.glade.get_object("description"),
                                           self.obj.set_description,
                                           self.obj.get_description,
                                           self.db.readonly)
        
        self.gid = MonitoredEntry(self.glade.get_object("gid"),
                                  self.obj.set_gramps_id, 
                                  self.obj.get_gramps_id, self.db.readonly)

        self.tags = MonitoredTagList(
            self.glade.get_object("tag_label"), 
            self.glade.get_object("tag_button"), 
            self.obj.set_tag_list, 
            self.obj.get_tag_list,
            self.db,
            self.uistate, self.track,
            self.db.readonly)

        self.privacy = PrivacyButton(self.glade.get_object("private"),
                                     self.obj, self.db.readonly)

        self.pixmap = self.glade.get_object("pixmap")
        ebox = self.glade.get_object('eventbox')
        ebox.connect('button-press-event', self.button_press_event)
        
        self.mimetext = self.glade.get_object("type")
        self.setup_filepath()
        self.determine_mime()
        self.draw_preview()

    def determine_mime(self):
        descr = get_description(self.obj.get_mime_type())
        if descr:
            self.mimetext.set_text(descr)

        path = self.file_path.get_text()
        path_full = media_path_full(self.db, path)
        if path != self.obj.get_path() and path_full != self.obj.get_path():
            #redetermine mime
            mime = get_type(find_file(path_full))
            self.obj.set_mime_type(mime)
            descr = get_description(mime)
            if descr:
                self.mimetext.set_text(descr)
            else:
                self.mimetext.set_text(_('Unknown'))
        #if mime type not set, is note
        if not self.obj.get_mime_type():
            self.mimetext.set_text(_('Note'))

    def draw_preview(self):
        mtype = self.obj.get_mime_type()
        if mtype:
            pb = get_thumbnail_image(
                        media_path_full(self.db, self.obj.get_path()), 
                        mtype)
            self.pixmap.set_from_pixbuf(pb)
        else:
            pb = find_mime_type_pixbuf('text/plain')
            self.pixmap.set_from_pixbuf(pb)

    def setup_filepath(self):
        self.select = self.glade.get_object('file_select')
        self.file_path = self.glade.get_object("path")

        fname = self.obj.get_path()
        self.file_path.set_text(fname)
        self.select.connect('clicked', self.select_file)

    def _create_tabbed_pages(self):
        notebook = Gtk.Notebook()

        self.citation_tab = CitationEmbedList(self.dbstate,
                                              self.uistate,
                                              self.track,
                                              self.obj.get_citation_list(), 
                                              self.get_menu_title())
        self._add_tab(notebook, self.citation_tab)
        self.track_ref_for_deletion("citation_tab")

        self.attr_tab = MediaAttrEmbedList(self.dbstate,
                                      self.uistate,
                                      self.track,
                                      self.obj.get_attribute_list())
        self._add_tab(notebook, self.attr_tab)
        self.track_ref_for_deletion("attr_tab")
        
        self.note_tab = NoteTab(self.dbstate,
                                self.uistate,
                                self.track,
                                self.obj.get_note_list(), 
                                notetype=NoteType.MEDIA)
        self._add_tab(notebook, self.note_tab)
        self.track_ref_for_deletion("note_tab")

        self.backref_tab = MediaBackRefList(self.dbstate,
                                            self.uistate,
                                            self.track,
                             self.db.find_backlink_handles(self.obj.handle))
        self.backref_list = self._add_tab(notebook, self.backref_tab)
        self.track_ref_for_deletion("backref_tab")
        self.track_ref_for_deletion("backref_list")

        self._setup_notebook_tabs( notebook)
        notebook.show_all()
        self.glade.get_object('vbox').pack_start(notebook, True, True, 0)

    def build_menu_names(self, person):
        return (_('Edit Media Object'), self.get_menu_title())

    def button_press_event(self, obj, event):
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.view_media(obj)

    def view_media(self, obj):
        ref_obj = self.dbstate.db.get_object_from_handle(self.obj.handle)

        if ref_obj:
            media_path = media_path_full(self.dbstate.db,
                                               ref_obj.get_path())
            open_file_with_default_application(media_path)

    def select_file(self, val):
        self.determine_mime()
        path = self.file_path.get_text()
        self.obj.set_path(conv_to_unicode(path))
        AddMediaObject(self.dbstate, self.uistate, self.track, self.obj, 
                       self._update_addmedia)

    def _update_addmedia(self, obj):
        """
        Called when the add media dialog has been called.
        This allows us to update the main form in response to
        any changes: Redraw relevant fields: description, mimetype and path
        """
        for obj in (self.descr_window, ):
            obj.update()
        fname = self.obj.get_path()
        self.file_path.set_text(fname)
        self.determine_mime()
        self.update_checksum()
        self.draw_preview()

    def update_checksum(self):
        self.uistate.set_busy_cursor(True)
        media_path = media_path_full(self.dbstate.db, self.obj.get_path())
        self.obj.set_checksum(create_checksum(os.path.normpath(media_path)))
        self.uistate.set_busy_cursor(False)

    def save(self, *obj):
        self.ok_button.set_sensitive(False)

        if self.object_is_empty():
            ErrorDialog(_("Cannot save media object"),
                        _("No data exists for this media object. Please "
                          "enter data or cancel the edit."))
            self.ok_button.set_sensitive(True)
            return

        (uses_dupe_id, id) = self._uses_duplicate_id()
        if uses_dupe_id:
            prim_object = self.get_from_gramps_id(id)
            name = prim_object.get_description()
            msg1 = _("Cannot save media object. ID already exists.")
            msg2 = _("You have attempted to use the existing Gramps ID with "
                         "value %(id)s. This value is already used by '" 
                         "%(prim_object)s'. Please enter a different ID or leave "
                         "blank to get the next available ID value.") % {
                         'id' : id, 'prim_object' : name }
            ErrorDialog(msg1, msg2)
            self.ok_button.set_sensitive(True)
            return

        path = conv_to_unicode(self.file_path.get_text())
        full_path = media_path_full(self.db, path)
        if os.path.isfile(full_path):
            self.determine_mime()
        else:                                                              
            msg1 = _("There is no media matching the current path value!") 
            msg2 = _("You have attempted to use the path with "            
                            "value '%(path)s'. This path does not exist!"     
                            " Please enter a different path") % {             
                            'path' : path }                                   
            ErrorDialog(msg1, msg2)                                    
            self.ok_button.set_sensitive(True)                             
            return                                                         

        self.obj.set_path(path)

        with DbTxn('', self.db) as trans:
            if not self.obj.get_handle():
                self.db.add_object(self.obj, trans)
                msg = _("Add Media Object (%s)") % self.obj.get_description()
            else:
                if not self.obj.get_gramps_id():
                    self.obj.set_gramps_id(self.db.find_next_object_gramps_id())
                self.db.commit_media_object(self.obj, trans)
                msg = _("Edit Media Object (%s)") % self.obj.get_description()
            trans.set_description(msg)

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

class DeleteMediaQuery(object):

    def __init__(self, dbstate, uistate, media_handle, the_lists):
        self.db = dbstate.db
        self.uistate = uistate
        self.media_handle = media_handle
        self.the_lists = the_lists
        
    def query_response(self):
        with DbTxn(_("Remove Media Object"), self.db) as trans:
            self.db.disable_signals()
        
            (person_list, family_list, event_list,
                    place_list, source_list, citation_list) = self.the_lists

            for handle in person_list:
                person = self.db.get_person_from_handle(handle)
                new_list = [photo for photo in person.get_media_list()
                            if photo.get_reference_handle() != self.media_handle]
                person.set_media_list(new_list)
                self.db.commit_person(person, trans)

            for handle in family_list:
                family = self.db.get_family_from_handle(handle)
                new_list = [photo for photo in family.get_media_list()
                            if photo.get_reference_handle() != self.media_handle]
                family.set_media_list(new_list)
                self.db.commit_family(family, trans)

            for handle in event_list:
                event = self.db.get_event_from_handle(handle)
                new_list = [photo for photo in event.get_media_list()
                            if photo.get_reference_handle() != self.media_handle]
                event.set_media_list(new_list)
                self.db.commit_event(event, trans)

            for handle in place_list:
                place = self.db.get_place_from_handle(handle)
                new_list = [photo for photo in place.get_media_list()
                            if photo.get_reference_handle() != self.media_handle]
                place.set_media_list(new_list)
                self.db.commit_place(place, trans)

            for handle in source_list:
                source = self.db.get_source_from_handle(handle)
                new_list = [photo for photo in source.get_media_list()
                            if photo.get_reference_handle() != self.media_handle]
                source.set_media_list(new_list)
                self.db.commit_source(source, trans)

            for handle in citation_list:
                citation = self.db.get_citation_from_handle(handle)
                new_list = [photo for photo in citation.get_media_list()
                            if photo.get_reference_handle() != self.media_handle]
                citation.set_media_list(new_list)
                self.db.commit_citation(citation, trans)

            self.db.enable_signals()
            self.db.remove_object(self.media_handle, trans)

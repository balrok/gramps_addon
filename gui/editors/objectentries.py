#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
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
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
import sys
if sys.version_info[0] < 3:
    import cPickle as pickle
else:
    import pickle

import logging
_LOG = logging.getLogger(".objectentries")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import (Place, Source, MediaObject, Note)
from .editplace import EditPlace
from .editsource import EditSource
from .editmedia import EditMedia
from .editnote import EditNote
from ..selectors import SelectorFactory
from ..ddtargets import DdTargets
from gramps.gen.errors import WindowActiveError

#-------------------------------------------------------------------------
#
# ObjEntry
#
#-------------------------------------------------------------------------
class ObjEntry(object):
    """
    Handles the selection of a existing or new Object. Supports Drag and Drop
    to select the object.
    This is the base class to create a real entry
    """
    EMPTY_TEXT = ""
    EMPTY_TEXT_RED = ""
    EDIT_STR = ""
    SHARE_STR = ""
    ADD_STR = ""
    DEL_STR = ""

    def __init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share, callback=None):
        """Pass the dbstate and uistate and present track.
            label is a Gtk.Label that shows the persent value
            set_val is function that is called when handle changes, use it
                to update the calling module
            get_val is function that is called to obtain handle from calling
                module
            share is the Gtk.Button to call the object selector or del connect
            add_edt is the Gtk.Button with add or edit value. Pass None if 
                this button should not be present.
        """
        self.label = label
        self.add_edt = add_edt
        self.share = share
        self.dbstate = dbstate
        self.db = dbstate.db
        self.get_val = get_val
        self.set_val = set_val
        self.uistate = uistate
        self.track = track
        self.callback = callback
        
        #connect drag and drop
        self._init_dnd()
        #set the object specific code
        self._init_object()

        #check if valid object:
        handle = self.get_val()
        if handle:
            obj = self.get_from_handle(handle)
            if not obj:
                #invalid val, set it to None
                self.set_val(None)
        if self.get_val():
            self.set_button(True)
            obj = self.get_from_handle(self.get_val())
            name = self.get_label(obj)
        else:
            name = ""
            self.set_button(False)

        if self.db.readonly:
            if self.add_edt is not None:
                self.add_edt.set_sensitive(False)
            self.share.set_sensitive(False)
        else:
            if self.add_edt is not None:
                self.add_edt.set_sensitive(True)
            self.share.set_sensitive(True)

        if self.add_edt is not None:
            self.add_edt.connect('clicked', self.add_edt_clicked)
        self.share.connect('clicked', self.share_clicked)
        
        if not self.db.readonly and not name:
            if self.add_edt is None:
                self.label.set_text(self.EMPTY_TEXT_RED)
            else:
                self.label.set_text(self.EMPTY_TEXT)
            self.label.set_use_markup(True)
        else:
            self.label.set_text(name)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        if self.callback:
            self.callback()

    def _init_dnd(self):
        """inheriting objects must set this
        """
        pass

    def _init_object(self):
        """inheriting objects can use this to set extra variables
        """
        pass

    def get_from_handle(self, handle):
        """ return the object given the hande
            inheriting objects must set this
        """
        pass

    def get_label(self, object):
        """ return the label
            inheriting objects must set this
        """
        pass

    def after_edit(self, obj):
        name = self.get_label(obj)
        self.label.set_text(name)
        if self.callback:
            self.callback()

    def add_edt_clicked(self, obj):
        """ if value, edit, if no value, call editor on new object
        """
        if self.get_val():
            obj = self.get_from_handle(self.get_val())
            self.call_editor(obj)
        else:
            self.call_editor()

    def call_editor(self, obj):
        """inheriting objects must set this
        """
        pass

    def call_selector(self):
        """inheriting objects must set this
        """
        pass

    def drag_data_received(self, widget, context, x, y, selection, info, time):
        (drag_type, idval, obj, val) = pickle.loads(selection.get_data())
        
        data = self.get_from_handle(obj)
        self.obj_added(data)
        
    def obj_added(self, data):
        """ callback from adding an object to the entry"""
        self.set_val(data.handle)
        self.label.set_text(self.get_label(data))
        self.set_button(True)
        if self.callback:
            self.callback()

    def share_clicked(self, obj):
        """ if value, delete connect, in no value, select existing object
        """
        if self.get_val():
            self.set_val(None)
            self.label.set_text(self.EMPTY_TEXT)
            self.label.set_use_markup(True)
            self.set_button(False)
            if self.callback:
                self.callback()
        else:
            select = self.call_selector()
            obj = select.run()
            if obj:
                self.obj_added(obj)

    def set_button(self, use_add):
        """ This sets the correct image to the two buttons.
            If False: select icon and add icon
            If True:  remove icon and edit icon
        """
        if self.add_edt is not None:
            list(map(self.add_edt.remove, self.add_edt.get_children()))
        for i in self.share.get_children():
            self.share.remove(i)

        if use_add:
            image = Gtk.Image()
            image.set_from_stock(Gtk.STOCK_REMOVE, Gtk.IconSize.BUTTON)
            image.show()
            self.share.add(image)
            self.share.set_tooltip_text(self.DEL_STR)
            if self.add_edt is not None:
                image = Gtk.Image()
                image.set_from_stock(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON)
                image.show()
                self.add_edt.add(image)
                self.add_edt.set_tooltip_text(self.EDIT_STR)
        else:
            image = Gtk.Image()
            image.set_from_stock(Gtk.STOCK_INDEX, Gtk.IconSize.BUTTON)
            image.show()
            self.share.add(image)
            self.share.set_tooltip_text(self.SHARE_STR)
            if self.add_edt is not None:
                image = Gtk.Image()
                image.set_from_stock(Gtk.STOCK_ADD, Gtk.IconSize.BUTTON)
                image.show()
                self.add_edt.add(image)
                self.add_edt.set_tooltip_text(self.ADD_STR)

class PlaceEntry(ObjEntry):
    """
    Handles the selection of a existing or new Place. Supports Drag and Drop
    to select a place.
    """
    EMPTY_TEXT = "<i>%s</i>" % _('To select a place, use drag-and-drop '
                                 'or use the buttons')
    EMPTY_TEXT_RED = "<i>%s</i>" % _('No place given, click button to select one')
    EDIT_STR = _('Edit place')
    SHARE_STR = _('Select an existing place')
    ADD_STR = _('Add a new place')
    DEL_STR = _('Remove place')
    
    def __init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share, skip=[]):
        ObjEntry.__init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share)
        self.skip = skip

    def _init_dnd(self):
        """connect drag and drop of places
        """
        self.label.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        tglist = Gtk.TargetList.new([])
        tglist.add(DdTargets.PLACE_LINK.atom_drag_type, DdTargets.PLACE_LINK.target_flags,
                   DdTargets.PLACE_LINK.app_id)
        self.label.drag_dest_set_target_list(tglist)
        self.label.connect('drag_data_received', self.drag_data_received)

    def drag_data_received(self, widget, context, x, y, selection, info, time):
        (drag_type, idval, obj, val) = pickle.loads(selection.get_data())

        if obj not in self.skip:
            data = self.get_from_handle(obj)
            self.obj_added(data)

    def get_from_handle(self, handle):
        """ return the object given the hande
        """
        return self.db.get_place_from_handle(handle)

    def get_label(self, place):
        return "%s [%s]" % (place.get_title(), place.gramps_id)

    def call_editor(self, obj=None):
        if obj is None:
            place = Place()
            func = self.obj_added
        else:
            place = obj
            func = self.after_edit
        try:
            EditPlace(self.dbstate, self.uistate, self.track, 
                      place, func)
        except WindowActiveError:
            pass

    def call_selector(self):
        cls = SelectorFactory('Place')
        return cls(self.dbstate, self.uistate, self.track, skip=self.skip)

class SourceEntry(ObjEntry):
    """
    Handles the selection of a existing or new Source. Supports Drag and Drop
    to select a source.
    """
    EMPTY_TEXT = "<i>%s</i>" % _('First add a source using the buttons')
    EMPTY_TEXT_RED = "<i>%s</i>" % _('First add a source using the button')
    EDIT_STR = _('Edit source')
    SHARE_STR = _('Select an existing source')
    ADD_STR = _('Add a new source')
    DEL_STR = _('Remove source')
    
    def __init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share, callback):
        ObjEntry.__init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share, callback)

    def _init_dnd(self):
        """connect drag and drop of sources
        """
        self.label.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        tglist = Gtk.TargetList.new([])
        tglist.add(DdTargets.SOURCE_LINK.atom_drag_type,
                   DdTargets.SOURCE_LINK.target_flags,
                   DdTargets.SOURCE_LINK.app_id)
        self.label.drag_dest_set_target_list(tglist)
        self.label.connect('drag_data_received', self.drag_data_received)

    def get_from_handle(self, handle):
        """ return the object given the handle
        """
        return self.db.get_source_from_handle(handle)

    def get_label(self, source):
        return "%s [%s]" % (source.get_title(), source.gramps_id)

    def call_editor(self, obj=None):
        if obj is None:
            source = Source()
            func = self.obj_added
        else:
            source = obj
            func = self.after_edit
        try:
            EditSource(self.dbstate, self.uistate, self.track, 
                       source, func)
        except WindowActiveError:
            pass

    def call_selector(self):
        cls = SelectorFactory('Source')
        return cls(self.dbstate, self.uistate, self.track)

# FIXME isn't used anywhere
class MediaEntry(ObjEntry):
    """
    Handles the selection of a existing or new media. Supports Drag and Drop
    to select a media object.
    """
    EMPTY_TEXT = "<i>%s</i>" % _('To select a media object, use drag-and-drop '
                                 'or use the buttons')
    EMPTY_TEXT_RED = "<i>%s</i>" % _('No image given, click button to select one')
    EDIT_STR = _('Edit media object')
    SHARE_STR = _('Select an existing media object')
    ADD_STR = _('Add a new media object')
    DEL_STR = _('Remove media object')
    
    def __init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share):
        ObjEntry.__init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share)

    def _init_dnd(self):
        """connect drag and drop of places
        """
        self.label.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        tglist = Gtk.TargetList.new([])
        tglist.add(DdTargets.MEDIAOBJ.atom_drag_type, DdTargets.MEDIAOBJ.target_flags,
                   DdTargets.MEDIAOBJ.app_id)
        self.label.drag_dest_set_target_list(tglist)
        self.label.connect('drag_data_received', self.drag_data_received)

    def get_from_handle(self, handle):
        """ return the object given the hande
        """
        return self.db.get_object_from_handle(handle)

    def get_label(self, object):
        return "%s [%s]" % (object.get_description(), object.gramps_id)

    def call_editor(self, obj=None):
        if obj is None:
            object = MediaObject()
            func = self.obj_added
        else:
            object = obj
            func = self.after_edit
        try:
            EditMedia(self.dbstate, self.uistate, self.track, 
                      object, func)
        except WindowActiveError:
            pass

    def call_selector(self):
        cls = SelectorFactory('MediaObject')
        return cls(self.dbstate, self.uistate, self.track)
    
# FIXME isn't used anywhere
class NoteEntry(ObjEntry):
    """
    Handles the selection of a existing or new Note. Supports Drag and Drop
    to select a Note.
        """
    EMPTY_TEXT = "<i>%s</i>" % _('To select a note, use drag-and-drop '
                                 'or use the buttons')
    EMPTY_TEXT_RED = "<i>%s</i>" % _('No note given, click button to select one')
    EDIT_STR = _('Edit Note')
    SHARE_STR = _('Select an existing note')
    ADD_STR = _('Add a new note')
    DEL_STR = _('Remove note')
    
    def __init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share):
        ObjEntry.__init__(self, dbstate, uistate, track, label, set_val, 
                 get_val, add_edt, share)
        self.notetype = None

    def set_notetype(self, type):
        """ set a notetype to use in new notes
        """
        self.notetype = type

    def get_notetype(self):
        """ return the set notetype
        """
        return self.notetype

    def _init_dnd(self):
        """connect drag and drop of places
        """
        self.label.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        tglist = Gtk.TargetList.new([])
        tglist.add(DdTargets.NOTE_LINK.atom_drag_type, DdTargets.NOTE_LINK.target_flags,
                   DdTargets.NOTE_LINK.app_id)
        self.label.drag_dest_set_target_list(tglist)
        self.label.connect('drag_data_received', self.drag_data_received)

    def get_from_handle(self, handle):
        """ return the object given the hande
        """
        return self.db.get_note_from_handle(handle)

    def get_label(self, note):
        txt = " ".join(note.get().split())
        if len(txt) > 35:
            txt = txt[:35] + "..."
        return "%s [%s]" % (txt, note.gramps_id)

    def call_editor(self, obj=None):
        if obj is None:
            note = Note()
            note.set_type(self.get_notetype())
            func = self.obj_added
        else:
            note = obj
            func = self.after_edit
        try:
            EditNote(self.dbstate, self.uistate, self.track, 
                         note, func)
        except WindowActiveError:
            pass

    def call_selector(self):
        cls = SelectorFactory('Note')
        return cls(self.dbstate, self.uistate, self.track)

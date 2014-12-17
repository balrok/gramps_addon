# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2011 Nick Hall
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

from gramps.gen.plug import Gramplet
from gramps.gui.widgets import Photo
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.utils.place import conv_lat_lon
from gramps.gen.utils.file import media_path_full
from gramps.gen.utils.location import get_location_list
from gi.repository import Gtk
from gi.repository import Pango

class PlaceDetails(Gramplet):
    """
    Displays details for a place.
    """
    def init(self):
        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.gui.WIDGET)

    def build_gui(self):
        """
        Build the GUI interface.
        """
        self.top = Gtk.HBox()
        vbox = Gtk.VBox()
        self.photo = Photo(self.uistate.screen_height() < 1000)
        self.title = Gtk.Label()
        self.title.set_alignment(0, 0)
        self.title.modify_font(Pango.FontDescription('sans bold 12'))
        vbox.pack_start(self.title, False, True, 7)
        self.table = Gtk.Table(n_rows=1, n_columns=2)
        vbox.pack_start(self.table, False, True, 0)
        self.top.pack_start(self.photo, False, True, 5)
        self.top.pack_start(vbox, False, True, 10)
        self.top.show_all()
        return self.top

    def add_row(self, title, value):
        """
        Add a row to the table.
        """
        label = Gtk.Label(label=title + ':')
        label.set_alignment(1, 0)
        label.show()
        value = Gtk.Label(label=value)
        value.set_alignment(0, 0)
        value.show()
        rows = self.table.get_property('n-rows')
        rows += 1
        self.table.resize(rows, 2)
        self.table.attach(label, 0, 1, rows, rows + 1, xoptions=Gtk.AttachOptions.FILL,
                                                       xpadding=10)
        self.table.attach(value, 1, 2, rows, rows + 1)
        
    def clear_table(self):
        """
        Remove all the rows from the table.
        """
        list(map(self.table.remove, self.table.get_children()))
        self.table.resize(1, 2)

    def db_changed(self):
        self.dbstate.db.connect('place-update', self.update)
        self.connect_signal('Place', self.update)

    def update_has_data(self): 
        active_handle = self.get_active('Person')
        if active_handle:
            active_person = self.dbstate.db.get_person_from_handle(active_handle)
            self.set_has_data(active_person is not None)
        else:
            self.set_has_data(False)

    def main(self):
        self.display_empty()
        active_handle = self.get_active('Place')
        if active_handle:
            place = self.dbstate.db.get_place_from_handle(active_handle)
            self.top.hide()
            if place:
                self.display_place(place)
                self.set_has_data(True)
            else:
                self.set_has_data(False)
            self.top.show()
        else:
            self.set_has_data(False)

    def display_place(self, place):
        """
        Display details of the active place.
        """
        self.load_place_image(place)
        self.title.set_text(place.get_title())

        self.clear_table()
        self.display_location(place)
        self.display_separator()
        lat, lon = conv_lat_lon(place.get_latitude(),
                                place.get_longitude(),
                                format='DEG')
        if lat:
            self.add_row(_('Latitude'), lat)
        if lon:
            self.add_row(_('Longitude'), lon)

    def display_location(self, place):
        """
        Display a location.
        """
        lines = get_location_list(self.dbstate.db, place)
        self.add_row(_('Location'), '\n'.join(lines))

    def display_empty(self):
        """
        Display empty details when no repository is selected.
        """
        self.photo.set_image(None)
        self.photo.set_uistate(None, None)
        self.title.set_text('')
        self.clear_table()

    def display_separator(self):
        """
        Display an empty row to separate groupd of entries.
        """
        label = Gtk.Label(label='')
        label.modify_font(Pango.FontDescription('sans 4'))
        label.show()
        rows = self.table.get_property('n-rows')
        rows += 1
        self.table.resize(rows, 2)
        self.table.attach(label, 0, 1, rows, rows + 1, xoptions=Gtk.AttachOptions.FILL)

    def load_place_image(self, place):
        """
        Load the primary image if it exists.
        """
        media_list = place.get_media_list()
        if media_list:
            media_ref = media_list[0]
            object_handle = media_ref.get_reference_handle()
            obj = self.dbstate.db.get_object_from_handle(object_handle)
            full_path = media_path_full(self.dbstate.db, obj.get_path())
            mime_type = obj.get_mime_type()
            if mime_type and mime_type.startswith("image"):
                self.photo.set_image(full_path, mime_type,
                                     media_ref.get_rectangle())
                self.photo.set_uistate(self.uistate, object_handle)
            else:
                self.photo.set_image(None)
                self.photo.set_uistate(None, None)
        else:
            self.photo.set_image(None)
            self.photo.set_uistate(None, None)

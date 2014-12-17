#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
# Copyright (C) 2010       Nick Hall
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
# python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
import logging
log = logging.getLogger(".")

#-------------------------------------------------------------------------
#
# GNOME/GTK modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gramps.gen.datehandler import displayer, format_time
from gramps.gen.lib import Date, MediaObject
from gramps.gen.constfunc import cuni, conv_to_unicode, UNITYPE
from gramps.gen.const import GRAMPS_LOCALE as glocale
from .flatbasemodel import FlatBaseModel

#-------------------------------------------------------------------------
#
# MediaModel
#
#-------------------------------------------------------------------------
class MediaModel(FlatBaseModel):

    def __init__(self, db, scol=0, order=Gtk.SortType.ASCENDING, search=None,
                 skip=set(), sort_map=None):
        self.gen_cursor = db.get_media_cursor
        self.map = db.get_raw_object_data
        
        self.fmap = [
            self.column_description,
            self.column_id,
            self.column_mime,
            self.column_path,
            self.column_date,
            self.column_private,
            self.column_tags,
            self.column_change,
            self.column_tag_color,
            ]
        
        self.smap = [
            self.column_description,
            self.column_id,
            self.column_mime,
            self.column_path,
            self.sort_date,
            self.column_private,
            self.column_tags,
            self.sort_change,
            self.column_tag_color,
            ]
        FlatBaseModel.__init__(self, db, scol, order, search=search, skip=skip,
                               sort_map=sort_map)

    def destroy(self):
        """
        Unset all elements that can prevent garbage collection
        """
        self.db = None
        self.gen_cursor = None
        self.map = None
        self.fmap = None
        self.smap = None
        FlatBaseModel.destroy(self)

    def color_column(self):
        """
        Return the color column.
        """
        return 8

    def on_get_n_columns(self):
        return len(self.fmap)+1

    def column_description(self, data):
        descr = data[4]
        if isinstance(descr, UNITYPE):
            return descr
        try:
            return cuni(descr)
        except:
            return conv_to_unicode(descr, 'latin1')

    def column_path(self, data):
        path = data[2]
        if isinstance(path, UNITYPE):
            return path
        try:
            return cuni(path)
        except:
            return cuni(path.encode('iso-8859-1'))

    def column_mime(self, data):
        mime = data[3]
        if mime and isinstance(mime, UNITYPE):
            return mime
        if mime:
            return cuni(mime)
        else:
            return _('Note')

    def column_id(self,data):
        return cuni(data[1])

    def column_date(self,data):
        if data[10]:
            date = Date()
            date.unserialize(data[10])
            return cuni(displayer.display(date))
        return ''

    def sort_date(self,data):
        obj = MediaObject()
        obj.unserialize(data)
        d = obj.get_date_object()
        if d:
            return "%09d" % d.get_sort_value()
        else:
            return ''

    def column_handle(self,data):
        return cuni(data[0])

    def column_private(self, data):
        if data[12]:
            return 'gramps-lock'
        else:
            # There is a problem returning None here.
            return ''

    def sort_change(self,data):
        return "%012x" % data[9]

    def column_change(self,data):
        return format_time(data[9])

    def column_tooltip(self,data):
        return cuni('Media tooltip')

    def get_tag_name(self, tag_handle):
        """
        Return the tag name from the given tag handle.
        """
        return self.db.get_tag_from_handle(tag_handle).get_name()
        
    def column_tag_color(self, data):
        """
        Return the tag color.
        """
        tag_color = "#000000000000"
        tag_priority = None
        for handle in data[11]:
            tag = self.db.get_tag_from_handle(handle)
            this_priority = tag.get_priority()
            if tag_priority is None or this_priority < tag_priority:
                tag_color = tag.get_color()
                tag_priority = this_priority
        return tag_color

    def column_tags(self, data):
        """
        Return the sorted list of tags.
        """
        tag_list = list(map(self.get_tag_name, data[11]))
        return ', '.join(sorted(tag_list, key=glocale.sort_key))

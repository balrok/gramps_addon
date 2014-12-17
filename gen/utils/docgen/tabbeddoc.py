#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2003  Donald N. Allingham
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

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
class TabbedDoc(object):
    def __init__(self, columns):
        self.columns = columns
        self.name = ""

    def creator(self, name):
        self.name = name

    def open(self,filename):
        pass

    def close(self):
        pass

    def start_page(self):
        pass

    def end_page(self):
        pass

    def start_paragraph(self):
        pass

    def end_paragraph(self):
        pass

    def start_table(self):
        pass

    def end_table(self):
        pass

    def start_row(self):
        pass

    def end_row(self):
        pass

    def write_cell(self, text):
        pass

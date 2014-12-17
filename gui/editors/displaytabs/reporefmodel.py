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
# GTK libraries
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# GRAMPS classes
#
#-------------------------------------------------------------------------


#-------------------------------------------------------------------------
#
# RepoRefModel
#
#-------------------------------------------------------------------------
class RepoRefModel(Gtk.ListStore):

    def __init__(self, ref_list, db):
        Gtk.ListStore.__init__(self, str, str, str, str, bool, object)
        self.db = db
        for ref in ref_list:
            repo = self.db.get_repository_from_handle(ref.ref)
            self.append(row=[
                repo.gramps_id,
                repo.name,
                ref.call_number, 
                str(repo.get_type()),
                ref.get_privacy(),
                ref, ])

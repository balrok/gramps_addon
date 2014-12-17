#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2007  Donald N. Allingham
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
# Standard Python modules
#
#-------------------------------------------------------------------------
from ....const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .. import Rule
from ._matchesfilter import MatchesFilter

#-------------------------------------------------------------------------
#
# IsParentOfFilterMatch
#
#-------------------------------------------------------------------------
class IsParentOfFilterMatch(Rule):
    """Rule that checks for a person that is a parent
    of someone matched by a filter"""

    labels      = [ _('Filter name:') ]
    name        = _('Parents of <filter> match')
    category    = _('Family filters')
    description = _("Matches parents of anybody matched by a filter")

    def prepare(self,db):
        self.db = db
        self.map = set()
        filt = MatchesFilter(self.list)
        filt.requestprepare(db)
        for person in db.iter_people():
            if filt.apply(db, person):
                self.init_list(person)
        filt.requestreset()

    def reset(self):
        self.map.clear()

    def apply(self,db,person):
        return person.handle in self.map

    def init_list(self,person):
        for fam_id in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_id)
            if fam:
                self.map.update(parent_id
                                for parent_id in [fam.get_father_handle(), 
                                                  fam.get_mother_handle()]
                                if parent_id)
                

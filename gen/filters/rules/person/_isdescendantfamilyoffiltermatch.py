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
from ._isdescendantfamilyof import IsDescendantFamilyOf
from ._matchesfilter import MatchesFilter

#-------------------------------------------------------------------------
#
# IsDescendantFamilyOfFilterMatch
#
#-------------------------------------------------------------------------
class IsDescendantFamilyOfFilterMatch(IsDescendantFamilyOf):
    """Rule that checks for a person that is a descendant
    of someone matched by a filter"""

    labels      = [ _('Filter name:') ]
    name        = _('Descendant family members of <filter> match')
    category    = _('Descendant filters')
    description = _("Matches people that are descendants or the spouse "
                    "of anybody matched by a filter")
    
    def prepare(self,db):
        self.db = db
        self.matches = set()

        filt = MatchesFilter(self.list[0:1])
        filt.requestprepare(db)
        for person in db.iter_people():
            if filt.apply(db, person):
                self.add_matches(person)
        filt.requestreset()


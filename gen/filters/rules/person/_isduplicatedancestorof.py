#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
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
# gen.filters.rules/Person/_IsDuplicatedAncestorOf.py

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

#-------------------------------------------------------------------------
#
# IsDuplicatedAncestorOf
#
#-------------------------------------------------------------------------
class IsDuplicatedAncestorOf(Rule):
    """Rule that checks for a person that is a duplicated ancestor of
    a specified person"""

    labels      = [ _('ID:')]
    name        = _('Duplicated ancestors of <person>')
    category    = _("Ancestral filters")
    description = _("Matches people that are ancestors twice or more "
                    "of a specified person")

    def prepare(self, db):
        self.db = db
        self.map = set()
        self.map2 = set()
        root_person = db.get_person_from_gramps_id(self.list[0])
        if root_person:
            self.init_ancestor_list(db,root_person)

    def reset(self):
        self.map.clear()
        self.map2.clear()

    def apply(self, db, person):
        return person.handle in self.map2

    def init_ancestor_list(self, db, person):
        fam_id = person.get_main_parents_family_handle()
        fam = db.get_family_from_handle(fam_id)
        if fam:
            f_id = fam.get_father_handle()
            m_id = fam.get_mother_handle()
            if m_id:
                self.mother_side(db, db.get_person_from_handle(m_id))
            if f_id:
                self.father_side(db, db.get_person_from_handle(f_id))

    def mother_side(self, db, person):
        if person and person.handle in self.map:
            self.map2.add((person.handle))
        self.map.add((person.handle))
        self.init_ancestor_list(db, person)

    def father_side(self, db, person):
        if person and person.handle in self.map:
            self.map2.add((person.handle))
        self.map.add((person.handle))
        self.init_ancestor_list(db, person)

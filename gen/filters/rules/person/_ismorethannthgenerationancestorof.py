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
# IsMoreThanNthGenerationAncestorOf
#
#-------------------------------------------------------------------------
class IsMoreThanNthGenerationAncestorOf(Rule):
    """Rule that checks for a person that is an ancestor of a specified person
    at least N generations away"""

    labels      = [ _('ID:'), _('Number of generations:') ]
    name        = _('Ancestors of <person> at least <N> generations away')
    category    = _("Ancestral filters")
    description = _("Matches people that are ancestors "
                    "of a specified person at least N generations away")

    def prepare(self,db):
        self.db = db
        self.map = set()
        try:
            root_handle = db.get_person_from_gramps_id(self.list[0]).get_handle()
            self.init_ancestor_list(root_handle,0)
        except:
            pass

    def reset(self):
        self.map.clear()
    
    def apply(self,db,person):
        return person.handle in self.map

    def init_ancestor_list(self, handle, gen):
#        if p.get_handle() in self.map:
#            loop_error(self.orig,p)
        if not handle:
            return
        if gen >= int(self.list[1]):
            self.map.add(handle)
        
        p = self.db.get_person_from_handle(handle)
        fam_id = p.get_main_parents_family_handle()
        fam = self.db.get_family_from_handle(fam_id)
        if fam:
            f_id = fam.get_father_handle()
            m_id = fam.get_mother_handle()
        
            if f_id:
                self.init_ancestor_list(f_id, gen+1)
            if m_id:
                self.init_ancestor_list(m_id, gen+1)

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2010  Michiel D. Nauta
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

"""
Provide merge capabilities for families.
"""

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from ..db import DbTxn
from ..const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from ..errors import MergeError
from . import MergePersonQuery

#-------------------------------------------------------------------------
#
# MergeFamilyQuery
#
#-------------------------------------------------------------------------
class MergeFamilyQuery(object):
    """
    Create database query to merge two families.
    """
    def __init__(self, database, phoenix, titanic, phoenix_fh=None,
                 phoenix_mh=None):
        self.database = database
        self.phoenix = phoenix
        self.titanic = titanic
        if phoenix_fh is None:
            self.phoenix_fh = self.phoenix.get_father_handle()
        else:
            self.phoenix_fh = phoenix_fh
        if phoenix_mh is None:
            self.phoenix_mh = self.phoenix.get_mother_handle()
        else:
            self.phoenix_mh = phoenix_mh

        if self.phoenix.get_father_handle() == self.phoenix_fh:
            self.titanic_fh = self.titanic.get_father_handle()
            self.father_swapped = False
        else:
            assert self.phoenix_fh == self.titanic.get_father_handle()
            self.titanic_fh = self.phoenix.get_father_handle()
            self.father_swapped = True
        if self.phoenix.get_mother_handle() == self.phoenix_mh:
            self.titanic_mh = self.titanic.get_mother_handle()
            self.mother_swapped = False
        else:
            assert self.phoenix_mh == self.titanic.get_mother_handle()
            self.titanic_mh = self.phoenix.get_mother_handle()
            self.mother_swapped = True

    def merge_person(self, phoenix_person, titanic_person, parent, trans):
        """
        Merge two persons even if they are None; no families are merged!
        """
        new_handle = self.phoenix.get_handle()
        old_handle = self.titanic.get_handle()

        if parent == 'father':
            swapped = self.father_swapped
            family_add_person_handle = (
                (self.phoenix if swapped else self.titanic).set_father_handle)
        elif parent == 'mother':
            swapped = self.mother_swapped
            family_add_person_handle = (
                (self.phoenix if swapped else self.titanic).set_mother_handle)
        else:
            raise ValueError(_("A parent should be a father or mother."))

        if phoenix_person is None:
            if titanic_person is not None:
                raise MergeError("""When merging people where one person """
                    """doesn't exist, that "person" must be the person that """
                    """will be deleted from the database.""")
            return
        elif titanic_person is None:
            if swapped:
                if any(childref.get_reference_handle() == phoenix_person.get_handle()
                        for childref in self.phoenix.get_child_ref_list()):

                    raise MergeError(_("A parent and child cannot be merged. "
                        "To merge these people, you must first break the "
                        "relationship between them."))

                phoenix_person.add_family_handle(new_handle)
                family_add_person_handle(phoenix_person.get_handle())
                self.database.commit_family(self.phoenix, trans)
            else:
                if any(childref.get_reference_handle() == phoenix_person.get_handle()
                        for childref in self.titanic.get_child_ref_list()):

                    raise MergeError(_("A parent and child cannot be merged. "
                        "To merge these people, you must first break the "
                        "relationship between them."))

                phoenix_person.add_family_handle(old_handle)
                family_add_person_handle(phoenix_person.get_handle())
                self.database.commit_family(self.titanic, trans)

            self.database.commit_person(phoenix_person, trans)
        else:
            query = MergePersonQuery(self.database, phoenix_person,
                                     titanic_person)
            query.execute(family_merger=False, trans=trans)

    def execute(self):
        """
        Merges two families into a single family.
        """
        new_handle = self.phoenix.get_handle()
        old_handle = self.titanic.get_handle()

        with DbTxn(_('Merge Family'), self.database) as trans:

            phoenix_father = self.database.get_person_from_handle(self.phoenix_fh)
            titanic_father = self.database.get_person_from_handle(self.titanic_fh)
            self.merge_person(phoenix_father, titanic_father, 'father', trans)

            phoenix_mother = self.database.get_person_from_handle(self.phoenix_mh)
            titanic_mother = self.database.get_person_from_handle(self.titanic_mh)
            self.phoenix = self.database.get_family_from_handle(new_handle)
            self.titanic = self.database.get_family_from_handle(old_handle)
            self.merge_person(phoenix_mother, titanic_mother, 'mother', trans)

            phoenix_father = self.database.get_person_from_handle(self.phoenix_fh)
            phoenix_mother = self.database.get_person_from_handle(self.phoenix_mh)
            self.phoenix = self.database.get_family_from_handle(new_handle)
            self.titanic = self.database.get_family_from_handle(old_handle)
            self.phoenix.merge(self.titanic)
            self.database.commit_family(self.phoenix, trans)
            for childref in self.titanic.get_child_ref_list():
                child = self.database.get_person_from_handle(
                        childref.get_reference_handle())
                if new_handle in child.parent_family_list:
                    child.remove_handle_references('Family', [old_handle])
                else:
                    child.replace_handle_reference('Family', old_handle,
                                                   new_handle)
                self.database.commit_person(child, trans)
            if phoenix_father:
                phoenix_father.remove_family_handle(old_handle)
                self.database.commit_person(phoenix_father, trans)
            if phoenix_mother:
                phoenix_mother.remove_family_handle(old_handle)
                self.database.commit_person(phoenix_mother, trans)
            # replace the family in lds ordinances
            for (dummy, person_handle) in self.database.find_backlink_handles(
                    old_handle, ['Person']):
                person = self.database.get_person_from_handle(person_handle)
                person.replace_handle_reference('Family', old_handle,new_handle)
                self.database.commit_person(person, trans)
            self.database.remove_family(old_handle, trans)

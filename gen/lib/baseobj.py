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

"""
Base Object class for Gramps
"""

#-------------------------------------------------------------------------
#
# standard python modules
#
#-------------------------------------------------------------------------
import re

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from ..constfunc import cuni

#-------------------------------------------------------------------------
#
# Base Object
#
#-------------------------------------------------------------------------
class BaseObject(object):
    """
    The BaseObject is the base class for all data objects in Gramps,
    whether primary or not. 
    
    Its main goal is to provide common capabilites to all objects, such as 
    searching through all available information.
    """
    
    def serialize(self):
        """
        Convert the object to a serialized tuple of data.
        """
        assert False, "Needs to be overridden in the derived class"

    def unserialize(self, data):
        """
        Convert a serialized tuple of data to an object.
        """
        assert False, "Needs to be overridden in the derived class"
        return self
    
    def to_struct(self):
        """
        Convert the data held in this object to a structure (eg,
        struct) that represents all the data elements.
        
        This method is used to recursively convert the object into a
        self-documenting form that can easily be used for various
        purposes, including diffs and queries.

        These structures may be primitive Python types (string,
        integer, boolean, etc.) or complex Python types (lists,
        tuples, or dicts). If the return type is a dict, then the keys
        of the dict match the fieldname of the object. If the return
        struct (or value of a dict key) is a list, then it is a list
        of structs. Otherwise, the struct is just the value of the
        attribute.

        :returns: Returns a struct containing the data of the object.
        """
        assert False, "Needs to be overridden in the derived class"

    def from_struct(self, struct):
        """
        Given a struct data representation, return an object of this type.

        These structures may be primitive Python types (string,
        integer, boolean, etc.) or complex Python types (lists,
        tuples, or dicts). If the return type is a dict, then the keys
        of the dict match the fieldname of the object. If the return
        struct (or value of a dict key) is a list, then it is a list
        of structs. Otherwise, the struct is just the value of the
        attribute.

        :returns: Returns an object of this type.
        """
        assert False, "Needs to be overridden in the derived class"

    def matches_string(self, pattern, case_sensitive=False):
        """
        Return True if any text data in the object or any of it's child
        objects matches a given pattern.

        :param pattern: The pattern to match.
        :type pattern: str
        :param case_sensitive: Whether the match is case-sensitive.
        :type case_sensitive: bool
        :returns: Returns whether any text data in the object or any of it's
                  child objects matches a given pattern.
        :rtype: bool
        """
        # Run through its own items
        patern_upper = pattern.upper()
        for item in self.get_text_data_list():
        # Some items are strings, which will fail in item.upper(), and some items are unicode.
        # Convert all items to unicode and the item.upper().find(patern_upper) will work OK.
            item = cuni(item)
            if not item:
                continue
            if case_sensitive:
                if item.find(pattern) != -1:
                    return True
            else:
                if item.upper().find(patern_upper) != -1:
                    return True

        # Run through child objects
        for obj in self.get_text_data_child_list():
            if obj.matches_string(pattern, case_sensitive):
                return True

        return False

    def matches_regexp(self, pattern, case_sensitive=False):
        """
        Return True if any text data in the object or any of it's child
        objects matches a given regular expression.

        :param pattern: The pattern to match.
        :type pattern: str
        :returns: Returns whether any text data in the object or any of it's
                  child objects matches a given regexp.
        :rtype: bool
        """

        # Run through its own items
        if case_sensitive:
            pattern_obj = re.compile(pattern)
        else:
            pattern_obj = re.compile(pattern, re.IGNORECASE)
        for item in self.get_text_data_list():
            if item and pattern_obj.match(item):
                return True

        # Run through child objects
        for obj in self.get_text_data_child_list():
            if obj.matches_regexp(pattern, case_sensitive):
                return True

        return False

    def get_text_data_list(self):
        """
        Return the list of all textual attributes of the object.

        :returns: Returns the list of all textual attributes of the object.
        :rtype: list
        """
        return []

    def get_text_data_child_list(self):
        """
        Return the list of child objects that may carry textual data.

        :returns: Returns the list of child objects that may carry textual data.
        :rtype: list
        """
        return []

    def get_referenced_handles(self):
        """
        Return the list of (classname, handle) tuples for all directly
        referenced primary objects.
        
        :returns: Returns the list of (classname, handle) tuples for referenced
                  objects.
        :rtype: list
        """
        return []

    def get_handle_referents(self):
        """
        Return the list of child objects which may, directly or through
        their children, reference primary objects.
        
        :returns: Returns the list of objects referencing primary objects.
        :rtype: list
        """
        return []

    def get_referenced_handles_recursively(self):
        """
        Return the list of (classname, handle) tuples for all referenced
        primary objects, whether directly or through child objects.
        
        :returns: Returns the list of (classname, handle) tuples for referenced
                  objects.
        :rtype: list
        """
        ret = self.get_referenced_handles()
        
        # Run through child objects
        for obj in self.get_handle_referents():
            ret += obj.get_referenced_handles_recursively()
        return ret

    def merge(self, acquisition):
        """
        Merge content of this object with that of acquisition.

        There are two sides to merger. First, the content of acquisition needs
        to be incorporated. Second, handles that reference acquisition (if
        there are any) need to be updated. Only the first part is handled in
        gen.lib, the second part needs access to the database and should be
        done in its own routines.

        :param acquisition: The object to incorporate.
        :type acquisition: BaseObject
        """
        pass

    @classmethod
    def create(cls, data):
        return cls().unserialize(data)

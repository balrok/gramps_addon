#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2005  Donald N. Allingham
# Copyright (C) 2010       Michiel D. Nauta
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
PrivacyBase Object class for Gramps.
"""

#-------------------------------------------------------------------------
#
# PrivacyBase Object
#
#-------------------------------------------------------------------------
class PrivacyBase(object):
    """
    Base class for privacy-aware objects.
    """

    def __init__(self, source=None):
        """
        Initialize a PrivacyBase. 
        
        If the source is not None, then object is initialized from values of 
        the source object.

        :param source: Object used to initialize the new object
        :type source: PrivacyBase
        """
        
        if source:
            self.private = source.private
        else:
            self.private = False

    def serialize(self):
        """
        Convert the object to a serialized tuple of data.
        """
        return self.private

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
        :rtype: bool
        """
        return self.private

    @classmethod
    def from_struct(cls, struct):
        """
        Given a struct data representation, return a serialized object.

        :returns: Returns a serialized object
        """
        return struct

    def unserialize(self, data):
        """
        Convert a serialized tuple of data to an object.
        """
        self.private = data
        return self

    def set_privacy(self, val):
        """
        Set or clears the privacy flag of the data.

        :param val: value to assign to the privacy flag. True indicates that 
            the record is private, False indicates that it is public.
        :type val: bool
        """
        self.private = val

    def get_privacy(self):
        """
        Return the privacy level of the data. 

        :returns: True indicates that the record is private
        :rtype: bool
        """
        return self.private

    def _merge_privacy(self, other):
        """
        Merge the privacy level of this object with that of other.

        :returns: Privacy of merged objects.
        :rtype: bool
        """
        self.private = self.private or other.private

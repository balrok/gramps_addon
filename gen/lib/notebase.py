#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
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
NoteBase class for Gramps.
"""

from .handle import Handle

#-------------------------------------------------------------------------
#
# NoteBase class
#
#-------------------------------------------------------------------------
class NoteBase(object):
    """
    Base class for storing notes.

    Starting in 3.0 branch, the objects may have multiple notes.
    Internally, this class maintains a list of Note handles,
    as a note_list attribute of the NoteBase object.
    """
    def __init__(self, source=None):
        """
        Create a new NoteBase, copying from source if not None.
        
        :param source: Object used to initialize the new object
        :type source: NoteBase
        """
        self.note_list = list(source.note_list) if source else []

    def serialize(self):
        """
        Convert the object to a serialized tuple of data.
        """
        return self.note_list

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
        :rtype: list
        """
        return [Handle("Note", n) for n in self.note_list]

    @classmethod
    def from_struct(cls, struct):
        """
        Given a struct data representation, return a serialized object.

        :returns: Returns a serialized object
        """
        return [Handle.from_struct(n) for n in struct]
        
    def unserialize(self, data):
        """
        Convert a serialized tuple of data to an object.
        """
        self.note_list = list(data)

    def add_note(self, handle):
        """
        Add the :class:`~.note.Note` handle to the list of note handles.

        :param handle: :class:`~.note.Note` handle to add the list of notes
        :type handle: str

        :returns: True if handle was added, False if it already was in the list
        :rtype: bool
        """
        if handle in self.note_list:
            return False
        else:
            self.note_list.append(handle)
            return True

    def remove_note(self, handle):
        """
        Remove the specified handle from the list of note handles, and all
        secondary child objects.

        :param handle: :class:`~.note.Note` handle to remove from the list of
                       notes
        :type handle: str
        """
        if handle in self.note_list:
            self.note_list.remove(handle)
        for item in self.get_note_child_list():
            item.remove_note(handle)
    
    def get_note_child_list(self):
        """
        Return the list of child secondary objects that may refer notes.
        
        All methods which inherit from NoteBase and have other child objects
        with notes, should return here a list of child objects which are 
        NoteBase

        :returns: Returns the list of child secondary child objects that may 
                refer notes.
        :rtype: list
        """
        return []

    def get_note_list(self):
        """
        Return the list of :class:`~.note.Note` handles associated with the
        object.

        :returns: The list of :class:`~.note.Note` handles
        :rtype: list
        """
        return self.note_list

    def has_note_reference(self, note_handle):
        """
        Return True if the object or any of its child objects has reference 
        to this note handle.

        :param note_handle: The note handle to be checked.
        :type note_handle: str
        :returns: Returns whether the object or any of its child objects has
                  reference to this note handle.
        :rtype: bool
        """
        for note_ref in self.note_list:
            if note_ref == note_handle:
                return True

        for item in self.get_note_child_list():
            if item.has_note_reference(note_handle):
                return True

        return False

    def set_note_list(self, note_list):
        """
        Assign the passed list to be object's list of :class:`~.note.Note`
        handles.

        :param note_list: List of :class:`~.note.Note` handles to be set on the
                          object
        :type note_list: list
        """
        self.note_list = note_list

    def _merge_note_list(self, acquisition):
        """
        Merge the list of notes from acquisition with our own.

        :param acquisition: The note list of this object will be merged with
                            the current note list.
        :rtype acquisition: NoteBase
        """
        for addendum in acquisition.note_list:
            self.add_note(addendum)

    def get_referenced_note_handles(self):
        """
        Return the list of (classname, handle) tuples for all referenced notes.
        
        This method should be used to get the :class:`~.note.Note` portion of
        the list by objects that store note lists.
        
        :returns: List of (classname, handle) tuples for referenced objects.
        :rtype: list
        """
        return [('Note', handle) for handle in self.note_list]

    def replace_note_references(self, old_handle, new_handle):
        """
        Replace references to note handles in the list of this object and
        all child objects and merge equivalent entries.

        :param old_handle: The note handle to be replaced.
        :type old_handle: str
        :param new_handle: The note handle to replace the old one with.
        :type new_handle: str
        """
        refs_list = self.note_list[:]
        new_ref = None
        if new_handle in self.note_list:
            new_ref = new_handle
        n_replace = refs_list.count(old_handle)
        for ix_replace in range(n_replace):
            idx = refs_list.index(old_handle)
            if new_ref:
                self.note_list.pop(idx)
                refs_list.pop(idx)
            else:
                self.note_list[idx] = new_handle

        for item in self.get_note_child_list():
            item.replace_note_references(old_handle, new_handle)

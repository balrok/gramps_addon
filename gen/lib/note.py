#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2010       Michiel D. Nauta
# Copyright (C) 2010       Nick Hall
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
Note class for Gramps.
"""

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .primaryobj import BasicPrimaryObject
from .tagbase import TagBase
from .notetype import NoteType
from .styledtext import StyledText
from .styledtexttagtype import StyledTextTagType
from ..constfunc import cuni
from .handle import Handle

#-------------------------------------------------------------------------
#
# Class for notes used throughout the majority of GRAMPS objects
#
#-------------------------------------------------------------------------
class Note(BasicPrimaryObject):
    """Define a text note.
    
    Starting from Gramps 3.1 Note object stores the text in
    :class:`~.styledtext.StyledText` instance, thus it can have text formatting
    information.

    To get and set only the clear text of the note use the :meth:`get` and
    :meth:`set` methods.
    
    To get and set the formatted version of the Note's text use the
    :meth:`get_styledtext` and :meth:`set_styledtext` methods.
    
    The note may be 'preformatted' or 'flowed', which indicates that the
    text string is considered to be in paragraphs, separated by newlines.
    
    :cvar FLOWED: indicates flowed format
    :cvar FORMATTED: indicates formatted format (respecting whitespace needed)
    :cvar POS_<x>: (int) Position of <x> attribute in the serialized format of
        an instance.

    .. warning:: The POS_<x> class variables reflect the serialized object,
                 they have to be updated in case the data structure or the
                 :meth:`serialize` method changes!
    """
    (FLOWED, FORMATTED) = list(range(2))
    
    (POS_HANDLE,
     POS_ID,
     POS_TEXT,
     POS_FORMAT,
     POS_TYPE,
     POS_CHANGE,
     POS_TAGS,
     POS_PRIVATE,) = list(range(8))

    def __init__(self, text=""):
        """Create a new Note object, initializing from the passed string."""
        BasicPrimaryObject.__init__(self)
        self.text = StyledText(text)
        self.format = Note.FLOWED
        self.type = NoteType()

    def serialize(self):
        """Convert the object to a serialized tuple of data.
        
        :returns: The serialized format of the instance.
        :rtype: tuple
        
        """
        return (self.handle, self.gramps_id, self.text.serialize(), self.format,
                self.type.serialize(), self.change, TagBase.serialize(self),
                self.private)

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
        :rtype: dict
        """
        return {"_class": "Note",
                "handle": Handle("Note", self.handle), 
                "gramps_id": self.gramps_id, 
                "text": self.text.to_struct(), 
                "format": self.format,
                "type": self.type.to_struct(), 
                "change": self.change, 
                "tag_list": TagBase.to_struct(self),
                "private": self.private}

    @classmethod
    def from_struct(cls, struct):
        """
        Given a struct data representation, return a serialized object.

        :returns: Returns a serialized object
        """
        default = Note()
        return (Handle.from_struct(struct.get("handle", default.handle)),
                struct.get("gramps_id", default.gramps_id),
                StyledText.from_struct(struct.get("text", {})),
                struct.get("format", default.format),
                NoteType.from_struct(struct.get("type", {})), 
                struct.get("change", default.change),
                TagBase.from_struct(struct.get("tag_list", default.tag_list)),
                struct.get("private", default.private))

    def unserialize(self, data):
        """Convert a serialized tuple of data to an object.
        
        :param data: The serialized format of a Note.
        :type: data: tuple
        """
        (self.handle, self.gramps_id, the_text, self.format,
         the_type, self.change, tag_list, self.private) = data

        self.text = StyledText()
        self.text.unserialize(the_text)
        self.type = NoteType()
        self.type.unserialize(the_type)
        TagBase.unserialize(self, tag_list)
        return self

    def get_text_data_list(self):
        """Return the list of all textual attributes of the object.

        :returns: The list of all textual attributes of the object.
        :rtype: list
        """
        return [str(self.text)]

    def get_referenced_handles(self):
        """
        Return the list of (classname, handle) tuples for all directly
        referenced primary objects.
        
        :returns: List of (classname, handle) tuples for referenced objects.
        :rtype: list
        """
        return self.get_referenced_tag_handles()
        
    def merge(self, acquisition):
        """
        Merge the content of acquisition into this note.

        Lost: handle, id, type, format, text and styles of acquisition.

        :param acquisition: The note to merge with the present note.
        :type acquisition: Note
        """
        self._merge_privacy(acquisition)
        self._merge_tag_list(acquisition)

    def set(self, text):
        """Set the text associated with the note to the passed string.

        :param text: The *clear* text defining the note contents.
        :type text: str
        """
        self.text = StyledText(text)

    def get(self):
        """Return the text string associated with the note.

        :returns: The *clear* text of the note contents.
        :rtype: unicode
        """
        return cuni(self.text)

    def set_styledtext(self, text):
        """Set the text associated with the note to the passed string.

        :param text: The *formatted* text defining the note contents.
        :type text: :class:`~.styledtext.StyledText`
        """
        self.text = text
        
    def get_styledtext(self):
        """Return the text string associated with the note.

        :returns: The *formatted* text of the note contents.
        :rtype: :class:`~.styledtext.StyledText`
        """
        return self.text
    
    def append(self, text):
        """Append the specified text to the text associated with the note.

        :param text: Text string to be appended to the note.
        :type text: str or :class:`~.styledtext.StyledText`
        """
        self.text = self.text + text

    def set_format(self, format):
        """Set the format of the note to the passed value. 
        
        :param format: The value can either indicate Flowed or Preformatted.
        :type format: int
        """
        self.format = format

    def get_format(self):
        """Return the format of the note. 
        
        The value can either indicate Flowed or Preformatted.

        :returns: 0 indicates Flowed, 1 indicates Preformated
        :rtype: int
        """
        return self.format

    def set_type(self, the_type):
        """Set descriptive type of the Note.
        
        :param the_type: descriptive type of the Note
        :type the_type: str
        """
        self.type.set(the_type)

    def get_type(self):
        """Get descriptive type of the Note.
        
        :returns: the descriptive type of the Note
        :rtype: str
        """
        return self.type

    def get_links(self):
        """
        Get the jump links from this note. Links can be external, to
        urls, or can be internal to gramps objects.

        Return examples::

            [("gramps", "Person", "handle", "7657626365362536"),
             ("external", "www", "url", "http://example.com")]

        :returns: list of [(domain, type, propery, value), ...]
        :rtype: list
        """
        retval = []
        for styledtext_tag in self.text.get_tags():
            if int(styledtext_tag.name) == StyledTextTagType.LINK:
                if styledtext_tag.value.startswith("gramps://"):
                    object_class, prop, value = styledtext_tag.value[9:].split("/", 2)
                    retval.append(("gramps", object_class, prop, value))
                else:
                    retval.append(("external", "www", "url", styledtext_tag.value))
        return retval

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2008       Zsolt Foldvari
# Copyright (C) 2013       Doug Blank <doug.blank@gmail.com>
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

"Handling formatted ('rich text') strings"

from __future__ import print_function

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .styledtexttag import StyledTextTag
from ..constfunc import cuni, STRTYPE

#-------------------------------------------------------------------------
#
# StyledText class
#
#-------------------------------------------------------------------------
class StyledText(object):
    """Helper class to enable character based text formatting.
    
    :py:class:`StyledText` is a wrapper class binding the clear text string and
    it's formatting tags together.
    
    :py:class:`StyledText` provides several string methods in order to
    manipulate formatted strings, such as :py:meth:`join`, :py:meth:`replace`, 
    :py:meth:`split`, and also supports the '+' operation (:py:meth:`__add__`).
    
    To get the clear text of the :py:class:`StyledText` use the built-in
    :py:func:`str()` function. To get the list of formatting tags use the
    :py:meth:`get_tags` method.
    
    StyledText supports the *creation* of formatted texts too. This feature
    is intended to replace (or extend) the current report interface.
    To be continued... FIXME
    
    :ivar string: (str) The clear text part.
    :ivar tags: (list of :py:class:`.StyledTextTag`) Text tags holding
                formatting information for the string.

    :cvar POS_TEXT: Position of *string* attribute in the serialized format of
                    an instance.
    :cvar POS_TAGS: (int) Position of *tags* attribute in the serialized format
                    of an instance.

    .. warning:: The POS_<x> class variables reflect the serialized object,
      they have to be updated in case the data structure or the 
      :py:meth:`serialize` method changes!
    
    .. note::
     1. There is no sanity check of tags in :py:meth:`__init__`, because when a
        :py:class:`StyledText` is displayed it is passed to a
        :py:class:`.StyledTextBuffer`, which in turn will 'eat' all invalid 
        tags (including out-of-range tags too).
     2. After string methods the tags can become fragmented. That means the same
        tag may appear more than once in the tag list with different ranges.
        There could be a 'merge_tags' functionality in :py:meth:`__init__`, 
        however :py:class:`StyledTextBuffer` will merge them automatically if
        the text is displayed.
    """
    (POS_TEXT, POS_TAGS) = list(range(2))
    
    def __init__(self, text="", tags=None):
        """Setup initial instance variable values."""
        self._string = text

        if tags:
            self._tags = tags
        else:
            self._tags = []

    # special methods
    
    def __str__(self): return self._string.__str__()
    def __repr__(self): return self._string.__repr__()

    def __add__(self, other):
        """Implement '+' operation on the class.
        
        :param other: string to concatenate to self
        :type other: basestring or :py:class:`StyledText`
        :return: concatenated strings
        :rtype: :py:class:`StyledText`
        
        """
        offset = len(self._string)

        if isinstance(other, StyledText):
            # need to join strings and merge tags
            for tag in other._tags:
                tag.ranges = [(start + offset, end + offset)
                              for (start, end) in tag.ranges]
            
            return self.__class__("".join([self._string, other._string]),
                                  self._tags + other._tags)
        elif isinstance(other, STRTYPE):
            # tags remain the same, only text becomes longer
            return self.__class__("".join([self._string, other]), self._tags)
        else:
            return self.__class__("".join([self._string, str(other)]),
                                  self._tags)

    def __eq__(self, other):
        return self._string == other._string and self._tags == other._tags

    def __ne__(self, other):
        return self._string != other._string or self._tags != other._tags

    def __lt__(self, other):
        return self._string < other._string

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    def __mod__(self, other):
        """Implement '%' operation on the class."""

        # test whether the formatting operation is valid at all
        self._string % other

        result = self.__class__(self._string, self._tags)

        i0 = 0
        while True:
            i1 = result._string.find('%', i0)
            if i1 < 0:
                break
            if result._string[i1+1] == '(':
                i2 = result._string.find(')', i1+3)
                param_name = result._string[i1+2:i2]
            else:
                i2 = i1
                param_name = None
            for i3 in range(i2+1, len(result._string)):
                if result._string[i3] in 'diouxXeEfFgGcrs%':
                    break
            if param_name is not None:
                param = other[param_name]
            elif isinstance(other, tuple):
                param = other[0]
                other = other[1:]
            else:
                param = other
            if not isinstance(param, StyledText):
                param = StyledText('%' + result._string[i2+1:i3+1] % param)
            (before, after) = result.split(result._string[i1:i3+1], 1)
            result = before + param + after
            i0 = i3 + 1

        return result

    # private methods
    

    # string methods in alphabetical order:

    def join(self, seq):
        """
        Emulate :py:meth:`__builtin__.str.join` method.
        
        :param seq: list of strings to join
        :type seq: basestring or :py:class:`StyledText`
        :return: joined strings
        :rtype: :py:class:`StyledText`
        """
        new_string = self._string.join([str(string) for string in seq])
        
        offset = 0
        new_tags = []
        self_len = len(self._string)
        
        for text in seq:
            if isinstance(text, StyledText):
                for tag in text._tags:
                    tag.ranges = [(start + offset, end + offset)
                                  for (start, end) in tag.ranges]
                    new_tags += [tag]
            
            offset = offset + len(str(text)) + self_len
        
        return self.__class__(new_string, new_tags)
    
    def replace(self, old, new, count=-1):
        """
        Emulate :py:meth:`__builtin__.str.replace` method.
        
        :param old: substring to be replaced
        :type old: basestring or :py:class:`StyledText`
        :param new: substring to replace by
        :type new: :py:class:`StyledText`
        :param count: if given, only the first count occurrences are replaced
        :type count: int
        :return: copy of the string with replaced substring(s)
        :rtype: :py:class:`StyledText`
        
        .. warning:: by the correct implementation parameter *new* should be
                     :py:class:`StyledText` or basestring, however only
                     :py:class:`StyledText` is currently supported.
        """
        # quick and dirty solution: works only if new.__class__ == StyledText
        return new.join(self.split(old, count))
    
    def split(self, sep=None, maxsplit=-1):
        """
        Emulate :py:meth:`__builtin__.str.split` method.
        
        :param sep: the delimiter string
        :type seq: basestring or :py:class:`StyledText`
        :param maxsplit: if given, at most maxsplit splits are done
        :type maxsplit: int
        :return: a list of the words in the string
        :rtype: list of :py:class:`StyledText`
        """
        # split the clear text first
        if sep is not None:
            sep = str(sep)
        string_list = self._string.split(sep, maxsplit)
        
        # then split the tags too
        end_string = 0
        styledtext_list = []
        
        for string in string_list:
            start_string = self._string.find(string, end_string)
            end_string = start_string + len(string)

            new_tags = []
            
            for tag in self._tags:
                new_tag = StyledTextTag(int(tag.name), tag.value)
                for (start_tag, end_tag) in tag.ranges:
                    start = max(start_string, start_tag)
                    end = min(end_string, end_tag)

                    if start < end:
                        new_tag.ranges.append((start - start_string,
                                               end - start_string))
                        
                if new_tag.ranges:
                    new_tags.append(new_tag)
            
            styledtext_list.append(self.__class__(string, new_tags))
                                   
        return styledtext_list

    # other public methods
    
    def serialize(self):
        """
        Convert the object to a serialized tuple of data.
        
        :return: Serialized format of the instance.
        :rtype: tuple
        """
        if self._tags:
            the_tags = [tag.serialize() for tag in self._tags]
        else:
            the_tags = []
            
        return (self._string, the_tags)
    
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

        :return: Returns a struct containing the data of the object.
        :rtype: dict
        """
        if self._tags:
            the_tags = [tag.to_struct() for tag in self._tags]
        else:
            the_tags = []
            
        return {"_class": "StyledText",
                "string": self._string, 
                "tags": the_tags}
    
    @classmethod
    def from_struct(cls, struct):
        """
        Given a struct data representation, return a serialized object.

        :return: Returns a serialized object
        """
        default = StyledText()
        return (struct.get("string", default.string),
                    [StyledTextTag.from_struct(t) 
                    for t in struct.get("tags", default.tags)])

    def unserialize(self, data):
        """
        Convert a serialized tuple of data to an object.
        
        :param data: Serialized format of instance variables.
        :type data: tuple
        """
        (self._string, the_tags) = data
        
        # I really wonder why this doesn't work... it does for all other types
        #self._tags = [StyledTextTag().unserialize(tag) for tag in the_tags]
        for tag in the_tags:
            stt = StyledTextTag()
            stt.unserialize(tag)
            self._tags.append(stt)
        return self
    
    def get_tags(self):
        """
        Return the list of formatting tags.
        
        :return: The formatting tags applied on the text.
        :rtype: list of 0 or more :py:class:`.StyledTextTag` instances.
        """
        return self._tags

    def get_string(self):
        """
        Accessor for the associated string.
        """
        return self._string

    tags = property(get_tags)
    string = property(get_string)

if __name__ == '__main__':
    from .styledtexttagtype import StyledTextTagType
    T1 = StyledTextTag(StyledTextTagType(1), 'v1', [(0, 2), (2, 4), (4, 6)])
    T2 = StyledTextTag(StyledTextTagType(2), 'v2', [(1, 3), (3, 5), (0, 7)])
    
    A = StyledText('123X456', [T1])
    B = StyledText("abcXdef", [T2])
    
    C = StyledText('\n')
    
    S = 'cleartext'
    
    C = C.join([A, S, B])
    L = C.split()
    C = C.replace('X', StyledText('_'))
    A = A + B

    print(A)

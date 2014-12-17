#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2003  Donald N. Allingham
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
Provide soundex calculation
"""

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
import sys
import unicodedata
if sys.version_info[0] < 3:
    import string

#-------------------------------------------------------------------------
#
# constants
#
#-------------------------------------------------------------------------
IGNORE = "HW~!@#$%^&*()_+=-`[]\|;:'/?.,<>\" \t\f\v"
if sys.version_info[0] < 3:
    TABLE  = string.maketrans('ABCDEFGIJKLMNOPQRSTUVXYZ',
                              '012301202245501262301202')
else:
    TABLE  = bytes.maketrans(b'ABCDEFGIJKLMNOPQRSTUVXYZ',
                             b'012301202245501262301202')

from .constfunc import conv_to_unicode_direct

#-------------------------------------------------------------------------
#
# soundex - returns the soundex value for the specified string
#
#-------------------------------------------------------------------------
def soundex(strval):
    "Return the soundex value to a string argument."

    strval = unicodedata.normalize('NFKD', 
        conv_to_unicode_direct(strval.upper().strip())).encode('ASCII', 'ignore')
    if not strval:
        return "Z000"
    if sys.version_info[0] < 3:
        strval = strval.encode('iso-8859-1') # Really?
        str2 = strval[0]
        strval = strval.translate(TABLE, IGNORE)
    else:
        strval = strval.decode('ASCII', 'ignore')
        str2 = strval[0]
        strval = strval.translate(TABLE)
    if not strval:
        return "Z000"
    prev = strval[0]
    for character in strval[1:]:
        if character != prev and character != "0":
            str2 = str2 + character
        prev = character
    # pad with zeros
    str2 = str2+"0000"
    return str2[:4]

#-------------------------------------------------------------------------
#
# compare - compares the soundex values of two strings
#
#-------------------------------------------------------------------------
def compare(str1, str2):
    "1 if strings are close. 0 otherwise."
    return soundex(str1) == soundex(str2)

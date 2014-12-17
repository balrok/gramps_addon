#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
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
Provide the different Source Attribute Types for Gramps.
"""

#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------
from ..const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from .grampstype import GrampsType

class SrcAttributeType(GrampsType):

    UNKNOWN     = -1
    CUSTOM      = 0

    _CUSTOM = CUSTOM
    _DEFAULT = UNKNOWN

    _DATAMAP = [
        (UNKNOWN     , _("Unknown"), "Unknown"),
        (CUSTOM      , _("Custom"), "Custom"),
        ]

    def __init__(self, value=None):
        GrampsType.__init__(self, value)

    def get_ignore_list(self, exception=None):
        """
        Return a list of the types to ignore and not include in default lists.
        
        Exception is a sublist of types that may not be ignored
        
        :param exception: list of integer values corresponding with types that
                          have to be excluded from the ignore list
        :type exception: list
        :returns: list of integers corresponding with the types to ignore when 
                  showing a list of different types
        :rtype: list
        
        """
        return []

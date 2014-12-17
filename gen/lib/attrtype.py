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
Provide the different Attribute Types for Gramps.
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
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .grampstype import GrampsType

class AttributeType(GrampsType):

    UNKNOWN     = -1
    CUSTOM      = 0
    CASTE       = 1
    DESCRIPTION = 2
    ID          = 3
    NATIONAL    = 4
    NUM_CHILD   = 5
    SSN         = 6
    NICKNAME    = 7
    CAUSE       = 8
    AGENCY      = 9
    AGE         = 10
    FATHER_AGE  = 11
    MOTHER_AGE  = 12
    WITNESS     = 13
    TIME        = 14

    _CUSTOM = CUSTOM
    _DEFAULT = ID

    _DATAMAP = [
        (UNKNOWN     , _("Unknown"), "Unknown"),
        (CUSTOM      , _("Custom"), "Custom"),
        (CASTE       , _("Caste"), "Caste"),
        (DESCRIPTION , _("Description"), "Description"),
        (ID          , _("Identification Number"), "Identification Number"),
        (NATIONAL    , _("National Origin"), "National Origin"),
        (NUM_CHILD   , _("Number of Children"), "Number of Children"),
        (SSN         , _("Social Security Number"), "Social Security Number"),
        (NICKNAME    , _("Nickname"), "Nickname"),
        (CAUSE       , _("Cause"), "Cause"),
        (AGENCY      , _("Agency"), "Agency"),
        (AGE         , _("Age"), "Age"),
        (FATHER_AGE  , _("Father's Age"), "Father Age"),
        (MOTHER_AGE  , _("Mother's Age"), "Mother Age"),
        (WITNESS     , _("Witness"), "Witness"),
        (TIME        , _("Time"), "Time"),
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

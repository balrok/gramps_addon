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
from ...const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from ...lib.attrtype import AttributeType
from . import Rule

#-------------------------------------------------------------------------
#
# HasAttribute
#
#-------------------------------------------------------------------------
class HasAttributeBase(Rule):
    """
    Rule that checks for an object with a particular attribute.
    """

    labels      = [ 'Attribute:', 'Value:' ]
    name        = 'Objects with the <attribute>'
    description = "Matches objects with the given attribute " \
                   "of a particular value"
    category    = _('General filters')
    allow_regex = True

    def apply(self, db, obj):
        if not self.list[0]:
            return False
        for attr in obj.get_attribute_list():
            specified_type = AttributeType()
            specified_type.set_from_xml_str(self.list[0])
            name_match = attr.get_type() == specified_type

            if name_match:
                return self.match_substring(1, attr.get_value())
        return False

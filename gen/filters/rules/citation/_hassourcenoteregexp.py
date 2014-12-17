#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2014       Nick Hall
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
Filter rule to match citations whose source notes contain a substring or
match a regular expression.
"""

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
from ....const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from .._hasnoteregexbase import HasNoteRegexBase

#-------------------------------------------------------------------------
#
# HasSourceNoteRegexp
#
#-------------------------------------------------------------------------
class HasSourceNoteRegexp(HasNoteRegexBase):
    """
    Rule that checks if a citation has a source note that contains a
    substring or matches a regular expression.
    """

    name        = _('Citations having source notes containing <text>')
    description = _("Matches citations whose source notes contain a substring "
                    "or match a regular expression")
    category    = _('Source filters')

    def apply(self, db, citation):
        source = db.get_source_from_handle(citation.get_reference_handle())
        if HasNoteRegexBase.apply(self, db, source):
            return True
        return False

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

# gen.filters.rules/Family/_ChangedSince.py

#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------
from ....const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .._changedsincebase import ChangedSinceBase

#-------------------------------------------------------------------------
#
# ChangedSince
#
#-------------------------------------------------------------------------
class ChangedSince(ChangedSinceBase):
    """Rule that checks for families changed since a specific time."""

    labels      = [ _('Changed after:'), _('but before:') ]
    name        = _('Families changed after <date time>')
    description = _("Matches family records changed after a specified "
                    "date-time (yyyy-mm-dd hh:mm:ss) or in the range, if a second "
                    "date-time is given.")

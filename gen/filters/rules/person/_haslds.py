#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2008  Brian G. Matherly
# Copyright (C) 2008  Jerome Rapinat
# Copyright (C) 2008  Benny Malengier
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
# gen.filters.rules/Person/_HasLDS.py

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

from .._hasldsbase import HasLDSBase

#-------------------------------------------------------------------------
#
# HasLDS
#
#-------------------------------------------------------------------------
class HasLDS(HasLDSBase):
    """Rule that checks for a person with a LDS event"""

    name        = _('People with <count> LDS events')
    description = _("Matches people with a certain number of LDS events")

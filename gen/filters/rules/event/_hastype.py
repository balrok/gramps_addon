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
from ....const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from ....lib.eventtype import EventType
from .. import Rule

#-------------------------------------------------------------------------
#
# HasType
#
#-------------------------------------------------------------------------
class HasType(Rule):
    """Rule that checks for an event of a particular type."""

    labels      = [ _('Event type:') ]
    name        = _('Events with the particular type')
    description = _("Matches events with the particular type ")
    category    = _('General filters')

    def apply(self, db, event):
        if not self.list[0]:
            return False
        else:
            specified_type = EventType()
            specified_type.set_from_xml_str(self.list[0])
            return event.get_type() == specified_type

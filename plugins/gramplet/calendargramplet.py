# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2009  Douglas S. Blank <doug.blank@gmail.com>
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

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from gramps.gui.plug.quick import run_quick_report_by_name
from gramps.gen.lib import Date

#------------------------------------------------------------------------
#
# CalendarGramplet class
#
#------------------------------------------------------------------------
class CalendarGramplet(Gramplet):
    def init(self):
        from gi.repository import Gtk
        self.set_tooltip(_("Double-click a day for details"))
        self.gui.calendar = Gtk.Calendar()
        self.gui.calendar.connect('day-selected-double-click', self.double_click)
        self.gui.calendar.set_display_options(
                                    Gtk.CalendarDisplayOptions.SHOW_HEADING)
        self.gui.get_container_widget().remove(self.gui.textview)
        vbox = Gtk.VBox(homogeneous=False, spacing=0)
        vbox.pack_start(self.gui.calendar, False, False, 0)
        self.gui.get_container_widget().add_with_viewport(vbox)
        vbox.show_all()
        #self.gui.calendar.show()

    def post_init(self):
        self.disconnect("active-changed")

    def double_click(self, obj):
        # bring up events on this day
        year, month, day = self.gui.calendar.get_date()
        date = Date()
        date.set_yr_mon_day(year, month + 1, day)
        run_quick_report_by_name(self.gui.dbstate, 
                                 self.gui.uistate, 
                                 'onthisday', 
                                 date)

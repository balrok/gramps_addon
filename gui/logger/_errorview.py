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

#-------------------------------------------------------------------------
#
# GNOME modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import URL_MANUAL_PAGE
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from ._errorreportassistant import ErrorReportAssistant
from ..display import display_help

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
WIKI_HELP_PAGE = '%s_-_FAQ' % URL_MANUAL_PAGE
WIKI_HELP_SEC = _('manual|General')

class ErrorView(object):
    """
    A Dialog for displaying errors.
    """
    
    def __init__(self, error_detail, rotate_handler):
        """
        Initialize the handler with the buffer size.
        """

        self._error_detail = error_detail
        self._rotate_handler = rotate_handler
        
        self.draw_window()
        self.run()

    def run(self):
        response = Gtk.ResponseType.HELP
        while response == Gtk.ResponseType.HELP:
            response = self.top.run()
            if response == Gtk.ResponseType.HELP:
                self.help_clicked()
            elif response == Gtk.ResponseType.YES:
                self.top.destroy()
                ErrorReportAssistant(error_detail = self._error_detail,
                                     rotate_handler = self._rotate_handler,
                                     ownthread=True)
            elif response == Gtk.ResponseType.CANCEL:
                self.top.destroy()

    def help_clicked(self):
        """Display the relevant portion of GRAMPS manual"""
        
        display_help(WIKI_HELP_PAGE, WIKI_HELP_SEC)

    def draw_window(self):
        title = "%s - Gramps" % _("Error Report")
        self.top = Gtk.Dialog(title)
        vbox = self.top.get_content_area()
        vbox.set_spacing(5)
        self.top.set_border_width(12)
        hbox = Gtk.HBox()
        hbox.set_spacing(12)
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_DIALOG_ERROR, Gtk.IconSize.DIALOG)
        label = Gtk.Label(label='<span size="larger" weight="bold">%s</span>'
                          % _("Gramps has experienced an unexpected error"))
        label.set_use_markup(True)

        hbox.pack_start(image, False, True, 0)
        hbox.add(label)

        vbox.pack_start(hbox, False, False, 5)

        instructions_label = Gtk.Label(label=
            _("Your data will be safe but it would be advisable to restart Gramps immediately. "\
              "If you would like to report the problem to the Gramps team "\
              "please click Report and the Error Reporting Wizard will help you "\
              "to make a bug report."))
        instructions_label.set_line_wrap(True)
        instructions_label.set_use_markup(True)

        vbox.pack_start(instructions_label, False, False, 5)
        
        tb_frame = Gtk.Frame(label=_("Error Detail"))
        tb_frame.set_border_width(6)
        tb_label = Gtk.TextView()
        tb_label.get_buffer().set_text(self._error_detail.get_formatted_log())
        tb_label.set_border_width(6)
        tb_label.set_editable(False)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 60)
        
        tb_frame.add(scroll)
        scroll.add_with_viewport(tb_label)

        tb_expander = Gtk.Expander(label='<span weight="bold">%s</span>' % _("Error Detail"))
        tb_expander.set_use_markup(True)
        tb_expander.add(tb_frame)
        
        vbox.pack_start(tb_expander, True, True, 5)


        self.top.add_button(Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL)
        self.top.add_button(_("Report"),Gtk.ResponseType.YES)
        self.top.add_button(Gtk.STOCK_HELP,Gtk.ResponseType.HELP)
        
        self.top.show_all()

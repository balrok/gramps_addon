#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2012       Nick Hall
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
# Python modules
#
#-------------------------------------------------------------------------
from __future__ import unicode_literals

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import cairo
import sys, os

from gramps.gen.config import config
if config.get('preferences.use-bsddb3') or sys.version_info[0] >= 3:
    import bsddb3 as bsddb
else:
    import bsddb
    
#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import ICON, SPLASH, GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.constfunc import get_env_var
from gramps.version import VERSION
from ..display import display_help, display_url

#-------------------------------------------------------------------------
#
# ErrorReportAssistant
#
#-------------------------------------------------------------------------
class ErrorReportAssistant(Gtk.Assistant):
    """
    Give the user an opportunity to report an error on the Gramps bug
    reporting system.
    """
    def __init__(self, error_detail, rotate_handler, ownthread=False):
        GObject.GObject.__init__(self)

        try:
            # did we get a handler wrapping the error detail?
            self._error_detail = error_detail.get_formatted_log()
        except AttributeError:
            self._error_detail = error_detail

        self._rotate_handler = rotate_handler

        self._sys_information_text_buffer = None
        self._user_information_text_buffer = None
        self._error_details_text_buffer = None
        self._final_report_text_buffer = None

        self.set_title(_("Error Report Assistant"))
        self.connect('close', self.close)
        self.connect('cancel', self.close)
        self.connect('prepare', self.prepare)

        #create the assistant pages
        self.create_page_intro()
        self.build_page1()
        self.build_page2()
        self.build_page3()
        self.build_page4()
        self.build_page5()
        self.create_page_summary()
        self.show_all()

        self.ownthread = ownthread
        if self.ownthread:
            Gtk.main()

    def close(self, *obj):
        """
        Close the assistant.
        """
        self.hide()
        if self.ownthread:
            Gtk.main_quit()

    def prepare(self, assistant, page):
        """
        Prepare pages prior to display.
        """
        self.page4_update()
        self.set_page_complete(page, True)

    def _copy_to_clipboard(self, obj=None):
        """
        Copy the bug report to the clipboard.
        """
        clipboard = Gtk.Clipboard.get_for_display(Gdk.Display.get_default(), 
                    Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(
            self._final_report_text_buffer.get_text(
              self._final_report_text_buffer.get_start_iter(),
              self._final_report_text_buffer.get_end_iter(), True), -1)
        
        clipboard = t = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        clipboard.set_text(
            self._final_report_text_buffer.get_text(
              self._final_report_text_buffer.get_start_iter(),
              self._final_report_text_buffer.get_end_iter(), True), -1)

    def _start_email_client(self, obj=None):
        """
        Start an email client to send the report.
        """
        display_url('mailto:gramps-bugs@lists.sourceforge.net?subject='
                          '"bug report"&body="%s"' \
                          % self._final_report_text_buffer.get_text(
                        self._final_report_text_buffer.get_start_iter(),
                        self._final_report_text_buffer.get_end_iter(), True))
        
    def _start_gramps_bts_in_browser(self, obj=None):
        """
        Start a web browser to report the bug.
        """
        display_url('http://bugs.gramps-project.org/bug_report_page.php')

    def _get_sys_information(self):
        """
        Get relevant system information.
        """
        if hasattr(os, "uname"):
            operatingsystem = os.uname()[0]
            distribution = os.uname()[2]
        else:
            operatingsystem = sys.platform
            distribution = " "

        return "Python version: %s \n"\
               "BSDDB version: %s \n"\
               "Gramps version: %s \n"\
               "LANG: %s\n"\
               "OS: %s\n"\
               "Distribution: %s\n\n"\
               "GTK version    : %s\n"\
               "gobject version: %s\n"\
               "cairo version  : %s"\
               % (str(sys.version).replace('\n',''),
                  str(bsddb.__version__) + " " + str(bsddb.db.version()),
                  str(VERSION),
                  get_env_var('LANG',''),
                  operatingsystem,
                  distribution,
                  '%d.%d.%d' % (Gtk.get_major_version(), 
                            Gtk.get_minor_version(), Gtk.get_micro_version()),
                  '%d.%d.%d' % GObject.pygobject_version,
                  cairo.version_info)

    def _reset_error_details(self, obj=None):
        """
        Reset the error details buffer to its original contents. 
        """
        self._error_details_text_buffer.set_text(
            "\n".join(self._rotate_handler.get_formatted_log(
                        self._error_detail)))

    def _clear_error_details(self, obj=None):
        """
        Clear the error details buffer.
        """
        self._error_details_text_buffer.delete(
            self._error_details_text_buffer.get_start_iter(),
            self._error_details_text_buffer.get_end_iter())

    def _reset_sys_information(self, obj=None):
        """
        Reset the system information buffer to its original contents. 
        """
        self._sys_information_text_buffer.set_text(
            self._get_sys_information())

    def _clear_sys_information(self, obj=None):
        """
        Clear the system information buffer.
        """
        self._sys_information_text_buffer.delete(
            self._sys_information_text_buffer.get_start_iter(),
            self._sys_information_text_buffer.get_end_iter())

    def _clear_user_information(self, obj=None):
        """
        Clear the user information buffer.
        """
        self._user_information_text_buffer.delete(
            self._user_information_text_buffer.get_start_iter(),
            self._user_information_text_buffer.get_end_iter())

    def create_page_intro(self):
        """
        Create the introduction page.
        """
        label = Gtk.Label(label=self.get_intro_text())
        label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(SPLASH)

        box = Gtk.VBox()
        box.pack_start(image, False, False, 5)
        box.pack_start(label, False, False, 5)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _('Report a bug'))
        self.set_page_type(page, Gtk.AssistantPageType.INTRO)

    def get_intro_text(self):
        """
        Return the text of the introduction page.
        """
        return _("This is the Bug Reporting Assistant. It will "
              "help you to make a bug report to the Gramps "
              "developers that will be as detailed as possible.\n\n"
              "The assistant will ask you a few questions and will "
              "gather some information about the error that has "
              "occured and the operating environment. "
              "At the end of the assistant you will be asked to "
              "file a bug report on the Gramps bug tracking system. "
              "The assistant will place the bug report on the clip board so "
              "that you can paste it into the form on the bug tracking "
              "website and review exactly what information you want to "
              "include.")

    def build_page1(self):
        """
        Build the error details page.
        """
        label = Gtk.Label(label=_("If you can see that there is any personal "
                            "information included in the error please remove "
                            "it."))
        label.set_alignment(0.01, 0.5)
        label.set_padding(0, 4)
        label.set_line_wrap(True)

        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        textview = Gtk.TextView()

        self._error_details_text_buffer = textview.get_buffer()
        self._reset_error_details()
            
        swin.add(textview)

        sw_frame = Gtk.Frame()
        sw_frame.add(swin)
        
        reset = Gtk.Button("Reset")
        reset.connect('clicked', self._reset_error_details)
        clear = Gtk.Button("Clear")
        clear.connect('clicked', self._clear_error_details)

        button_box = Gtk.HButtonBox()
        button_box.set_border_width(6)
        button_box.set_spacing(6)
        button_box.set_layout(Gtk.ButtonBoxStyle.END)

        button_box.pack_end(reset, False, False, 0)
        button_box.pack_end(clear, False, False, 0)

        error_details_box = Gtk.VBox()
        error_details_box.pack_start(label, False, False, 0)
        error_details_box.pack_start(sw_frame, True, True, 0)
        error_details_box.pack_start(button_box, False, False, 0)

        error_details_align = Gtk.Alignment.new(0, 0, 1, 1)
        error_details_align.set_padding(0, 0, 11, 0)
        error_details_align.add(error_details_box)
        
        error_details_frame = Gtk.Frame()
        error_details_frame.set_border_width(3)
        error_details_frame.set_label("<b>%s</b>" % _("Error Details"))
        error_details_frame.get_label_widget().set_use_markup(True)

        error_details_frame.add(error_details_align)

        side_label = Gtk.Label(_("This is the detailed Gramps error "
                                 "information, don't worry if you do not "
                                 "understand it. You will have the opportunity "
                                 "to add further detail about the error "
                                 "in the following pages of the assistant."))

        side_label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(ICON)

        heading = Gtk.HBox()
        heading.pack_start(side_label, True, True, 5)
        heading.pack_start(image, False, False, 5)

        box = Gtk.VBox()
        box.pack_start(heading, False, False, 5)
        box.pack_start(error_details_frame, True, True, 0)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _("Error Details"))
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)

    def build_page2(self):
        """
        Build the system information page.
        """
        label = Gtk.Label(label=_("Please check the information below and correct "
                            "anything that you know to be wrong or remove "
                            "anything that you would rather not have included "
                            "in the bug report."))
        label.set_alignment(0.01, 0.5)
        label.set_padding(0, 4)
        label.set_line_wrap(True)

        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        textview = Gtk.TextView()

        self._sys_information_text_buffer = textview.get_buffer()
        self._reset_sys_information()

        swin.add(textview)

        sw_frame = Gtk.Frame()
        sw_frame.add(swin)
        
        reset = Gtk.Button("Reset")
        reset.connect('clicked', self._reset_sys_information)
        clear = Gtk.Button("Clear")
        clear.connect('clicked', self._clear_sys_information)


        button_box = Gtk.HButtonBox()
        button_box.set_border_width(6)
        button_box.set_spacing(6)
        button_box.set_layout(Gtk.ButtonBoxStyle.END)

        button_box.pack_end(reset, False, False, 0)
        button_box.pack_end(clear, False, False, 0)

        sys_information_box = Gtk.VBox()
        sys_information_box.pack_start(label, False, False, 0)
        sys_information_box.pack_start(sw_frame, True, True, 0)
        sys_information_box.pack_start(button_box, False, False, 0)

        sys_information_align = Gtk.Alignment.new(0, 0, 1, 1)
        sys_information_align.set_padding(0, 0, 11, 0)
        sys_information_align.add(sys_information_box)
        
        sys_information_frame = Gtk.Frame()
        sys_information_frame.set_border_width(3)
        sys_information_frame.set_label("<b>%s</b>" % _("System Information"))
        sys_information_frame.get_label_widget().set_use_markup(True)

        sys_information_frame.add(sys_information_align)

        side_label = Gtk.Label(label=_("This is the information about your system "
                                 "that will help the developers to fix the "
                                 "bug."))

        side_label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(ICON)

        heading = Gtk.HBox()
        heading.pack_start(side_label, True, True, 5)
        heading.pack_start(image, False, False, 5)

        box = Gtk.VBox()
        box.pack_start(heading, False, False, 5)
        box.pack_start(sys_information_frame, True, True, 0)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _("System Information"))
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)

    def build_page3(self):
        """
        Build the further information page.
        """
        label = Gtk.Label(label=_("Please provide as much information as you can "
                             "about what you were doing when the error "
                             "occured."))
        label.set_alignment(0.01, 0.5)
        label.set_padding(0, 4)
        label.set_line_wrap(True)

        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        textview = Gtk.TextView()

        self._user_information_text_buffer = textview.get_buffer()

        swin.add(textview)

        sw_frame = Gtk.Frame()
        sw_frame.add(swin)
        
        clear = Gtk.Button("Clear")
        clear.connect('clicked', self._clear_user_information)

        button_box = Gtk.HButtonBox()
        button_box.set_border_width(6)
        button_box.set_spacing(6)
        button_box.set_layout(Gtk.ButtonBoxStyle.END)

        button_box.pack_end(clear, False, False, 0)

        user_information_box = Gtk.VBox()
        user_information_box.pack_start(label, False, False, 0)
        user_information_box.pack_start(sw_frame, True, True, 0)
        user_information_box.pack_start(button_box, False, False, 0)

        user_information_align = Gtk.Alignment.new(0, 0, 1, 1)
        user_information_align.set_padding(0, 0, 11, 0)
        user_information_align.add(user_information_box)
        
        user_information_frame = Gtk.Frame()
        user_information_frame.set_border_width(3)
        user_information_frame.set_label("<b>%s</b>" % _("Further Information"))
        user_information_frame.get_label_widget().set_use_markup(True)

        user_information_frame.add(user_information_align)

        side_label = Gtk.Label(label=_("This is your opportunity to describe what "
                                 "you were doing when the error occured."))

        side_label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(ICON)

        heading = Gtk.HBox()
        heading.pack_start(side_label, True, True, 5)
        heading.pack_start(image, False, False, 5)

        box = Gtk.VBox()
        box.pack_start(heading, False, False, 5)
        box.pack_start(user_information_frame, True, True, 0)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _("Further Information"))
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)

    def build_page4(self):
        """
        Build the bug report summary page.
        """
        label = Gtk.Label(_("Please check that the information is correct, "
                            "do not worry if you don't understand the detail "
                            "of the error information. Just make sure that it "
                            "does not contain anything that you do not want "
                            "to be sent to the developers."))
        label.set_alignment(0.01, 0.5)
        label.set_padding(0, 4)
        label.set_line_wrap(True)

        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)

        self._final_report_text_buffer = textview.get_buffer()        

        swin.add(textview)

        sw_frame = Gtk.Frame()
        sw_frame.add(swin)
        
        summary_box = Gtk.VBox()
        summary_box.pack_start(label, False, False, 0)
        summary_box.pack_start(sw_frame, True, True, 0)

        summary_align = Gtk.Alignment.new(0, 0, 1, 1)
        summary_align.set_padding(0, 0, 11, 0)
        summary_align.add(summary_box)
        
        summary_frame = Gtk.Frame()
        summary_frame.set_border_width(3)
        summary_frame.set_label("<b>%s</b>" % _("Bug Report Summary"))
        summary_frame.get_label_widget().set_use_markup(True)

        summary_frame.add(summary_align)

        side_label = Gtk.Label(label=_("This is the completed bug report. The next "
                                 "page of the assistant will help you to file "
                                 "a bug on the Gramps bug tracking system "
                                 "website."))

        side_label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(ICON)

        heading = Gtk.HBox()
        heading.pack_start(side_label, True, True, 5)
        heading.pack_start(image, False, False, 5)

        box = Gtk.VBox()
        box.pack_start(heading, False, False, 5)
        box.pack_start(summary_frame, True, True, 0)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _("Bug Report Summary"))
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)

    def build_page5(self):
        """
        Build the send bug report page.
        """
        label = Gtk.Label(label=
            "%s <i>%s</i>" %
            (_("Use the two buttons below to first copy the bug report to the "
               "clipboard and then open a webbrowser to file a bug report at "),
               "http://bugs.gramps-project.org/bug_report_page.php."))
        label.set_alignment(0.01, 0.5)
        label.set_padding(0, 4)
        label.set_line_wrap(True)
        label.set_use_markup(True)


        url_label = Gtk.Label(label=_("Use this button to start a web browser and "
                                "file a bug report on the Gramps bug tracking "
                                "system."))
        url_label.set_alignment(0.01, 0.5)
        url_label.set_padding(0, 4)
        url_label.set_line_wrap(True)
        url_label.set_size_request(200, -1)

        url_button = Gtk.Button("File bug report")
        url_button.connect('clicked', self._start_gramps_bts_in_browser)
        url_button_vbox = Gtk.VBox()
        url_button_vbox.pack_start(url_button, True, False, 0)
        
        url_box = Gtk.HBox()
        url_box.pack_start(url_label, True, True, 0)
        url_box.pack_start(url_button_vbox, False, False, 0)


        url_align = Gtk.Alignment.new(0, 0, 1, 1)
        url_align.set_padding(0, 0, 11, 0)
        url_align.add(url_box)

        url_frame = Gtk.Frame()
        url_frame.add(url_align)
        
        clip_label = Gtk.Label(_("Use this button "
                                 "to copy the bug report onto the clipboard. "
                                 "Then go to the bug tracking website by using "
                                 "the button below, paste the report and click "
                                 "submit report"))
        clip_label.set_alignment(0.01, 0.5)
        clip_label.set_padding(0, 4)
        clip_label.set_line_wrap(True)
        clip_label.set_size_request(200, -1)

        clip_button = Gtk.Button("Copy to clipboard")
        clip_button.connect('clicked', self._copy_to_clipboard)
        clip_button_vbox = Gtk.VBox()
        clip_button_vbox.pack_start(clip_button, True, False, 0)
        
        clip_box = Gtk.HBox()
        clip_box.pack_start(clip_label, True, True, 0)
        clip_box.pack_start(clip_button_vbox, False, False, 0)


        clip_align = Gtk.Alignment.new(0, 0, 1, 1)
        clip_align.set_padding(0, 0, 11, 0)
        clip_align.add(clip_box)

        clip_frame = Gtk.Frame()
        clip_frame.add(clip_align)
        

        inner_box = Gtk.VBox()
        inner_box.pack_start(label, False, False, 0)
        inner_box.pack_start(clip_frame, False, False, 0)
        inner_box.pack_start(url_frame, False, False, 0)

        inner_align = Gtk.Alignment.new(0, 0, 1, 1)
        inner_align.set_padding(0, 0, 11, 0)
        inner_align.add(inner_box)
        
        outer_frame = Gtk.Frame()
        outer_frame.set_border_width(3)
        outer_frame.set_label("<b>%s</b>" % _("Send Bug Report"))
        outer_frame.get_label_widget().set_use_markup(True)

        outer_frame.add(inner_align)

        side_label = Gtk.Label(label=_("This is the final step. Use the buttons on "
                                 "this page to start a web browser and file a "
                                 "bug report on the Gramps bug tracking "
                                 "system."))

        side_label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(ICON)

        heading = Gtk.HBox()
        heading.pack_start(side_label, True, True, 5)
        heading.pack_start(image, False, False, 5)

        box = Gtk.VBox()
        box.pack_start(heading, False, False, 5)
        box.pack_start(outer_frame, True, True, 0)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _("Send Bug Report"))
        self.set_page_type(page, Gtk.AssistantPageType.CONTENT)

    def create_page_summary(self):
        """
        Create the summary page.
        """
        text = _('Gramps is an Open Source project. Its success '
                 'depends on its users. User feedback is important. '
                 'Thank you for taking the time to submit a bug report.')
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)

        image = Gtk.Image()
        image.set_from_file(SPLASH)

        box = Gtk.VBox()
        box.pack_start(image, False, False, 5)
        box.pack_start(label, False, False, 5)

        page = box

        page.show_all()
        self.append_page(page)
        self.set_page_title(page, _('Complete'))
        self.set_page_type(page, Gtk.AssistantPageType.SUMMARY)

    def page4_update(self):
        """
        Update the contents of page 4 with any changes made.
        """
        self._final_report_text_buffer.set_text(
            "User Information: \n" +
            "===================\n\n" +
            self._user_information_text_buffer.get_text(
              self._user_information_text_buffer.get_start_iter(),
              self._user_information_text_buffer.get_end_iter(), True) +

            "\n\n\nError Details: \n" +
            "===================\n\n" +

            self._error_details_text_buffer.get_text(
              self._error_details_text_buffer.get_start_iter(),
              self._error_details_text_buffer.get_end_iter(), True) +

            "\n\nSystem Information: \n" +
            "===================\n\n" +

            self._sys_information_text_buffer.get_text(
              self._sys_information_text_buffer.get_start_iter(),
              self._sys_information_text_buffer.get_end_iter(), True)             
            )

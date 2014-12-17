# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2003-2006  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2012       Paul Franklin
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

# Written by Alex Roitman, 
# largely based on the SimpleBookTitle.py by Don Allingham

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#------------------------------------------------------------------------
#
# gtk
#
#------------------------------------------------------------------------

#------------------------------------------------------------------------
#
# gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.plug.menu import TextOption
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.docgen import (FontStyle, ParagraphStyle, FONT_SANS_SERIF, 
                             PARA_ALIGN_CENTER, IndexMark, INDEX_TYPE_TOC)

#------------------------------------------------------------------------
#
# CustomText
#
#------------------------------------------------------------------------
class CustomText(Report):

    def __init__(self, database, options, user):
        """
        Create CustomText object that produces the report.
        
        The arguments are:

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        This report needs the following parameters (class variables)
        that come in the options class.
        
        top   - Text on the top.
        mid   - Text in the middle.
        bot   - Text on the bottom.
        """
        Report.__init__(self, database, options, user)

        menu = options.menu
        self.top_text = menu.get_option_by_name('top').get_value()
        self.middle_text = menu.get_option_by_name('mid').get_value()
        self.bottom_text = menu.get_option_by_name('bot').get_value()
        
    def write_report(self):
        mark_text = _("Custom Text")
        if self.top_text[0]:
            mark_text = "%s (%s)" % (_("Custom Text"), self.top_text[0])
        elif self.middle_text[0]:
            mark_text = "%s (%s)" % (_("Custom Text"), self.middle_text[0])
        elif self.bottom_text[0]:
            mark_text = "%s (%s)" % (_("Custom Text"), self.bottom_text[0])
        mark = IndexMark(mark_text, INDEX_TYPE_TOC, 1)
        self.doc.start_paragraph('CBT-Initial')
        for line in self.top_text:
            self.doc.write_text(line, mark)
            self.doc.write_text("\n")
        self.doc.end_paragraph()

        self.doc.start_paragraph('CBT-Middle')
        for line in self.middle_text:
            self.doc.write_text(line)
            self.doc.write_text("\n")
        self.doc.end_paragraph()

        self.doc.start_paragraph('CBT-Final')
        for line in self.bottom_text:
            self.doc.write_text(line)
            self.doc.write_text("\n")
        self.doc.end_paragraph()

#------------------------------------------------------------------------
#
# CustomTextOptions
#
#------------------------------------------------------------------------
class CustomTextOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """
    
    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)
        
    def add_menu_options(self, menu):
        
        category_name = _("Text")
        
        top = TextOption(_("Initial Text"), [""] )
        top.set_help(_("Text to display at the top."))
        menu.add_option(category_name, "top", top)
        
        mid = TextOption(_("Middle Text"), [""] )
        mid.set_help(_("Text to display in the middle"))
        menu.add_option(category_name, "mid", mid)
        
        bot = TextOption(_("Final Text"), [""] )
        bot.set_help(_("Text to display last."))
        menu.add_option(category_name, "bot", bot)

    def make_default_style(self,default_style):
        """Make the default output style for the Custom Text report."""
        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=12, bold=0, italic=0)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set(pad=0.5)
        para.set_description(_('The style used for the first portion of the custom text.'))
        default_style.add_paragraph_style("CBT-Initial", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=12, bold=0, italic=0)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(pad=0.5)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_('The style used for the middle portion of the custom text.'))
        default_style.add_paragraph_style("CBT-Middle", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=12, bold=0, italic=0)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set(pad=0.5)
        para.set_description(_('The style used for the last portion of the custom text.'))
        default_style.add_paragraph_style("CBT-Final", para)

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2013       Paul Franklin
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
Reports/Text Reports/Database Summary Report.
"""

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import posixpath

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.lib import Person
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle,
                                    FONT_SANS_SERIF, INDEX_TYPE_TOC,
                                    PARA_ALIGN_CENTER)
from gramps.gen.utils.file import media_path_full
from gramps.gen.datehandler import get_date

#------------------------------------------------------------------------
#
# SummaryReport
#
#------------------------------------------------------------------------
class SummaryReport(Report):
    """
    This report produces a summary of the objects in the database.
    """
    def __init__(self, database, options, user):
        """
        Create the SummaryReport object that produces the report.
        
        The arguments are:

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        """
        Report.__init__(self, database, options, user)
        self.__db = database
        
        lang = options.menu.get_option_by_name('trans').get_value()
        self.set_locale(lang)

    def write_report(self):
        """
        Overridden function to generate the report.
        """
        self.doc.start_paragraph("SR-Title")
        title = self._("Database Summary Report")
        mark = IndexMark(title, INDEX_TYPE_TOC, 1)
        self.doc.write_text(title, mark)
        self.doc.end_paragraph()
        
        self.summarize_people()
        self.summarize_families()
        self.summarize_media()
            
    def summarize_people(self):
        """
        Write a summary of all the people in the database.
        """
        with_media = 0
        incomp_names = 0
        disconnected = 0
        missing_bday = 0
        males = 0
        females = 0
        unknowns = 0
        namelist = []
        
        self.doc.start_paragraph("SR-Heading")
        self.doc.write_text(self._("Individuals"))
        self.doc.end_paragraph()
        
        num_people = 0
        for person in self.__db.iter_people():
            num_people += 1
            
            # Count people with media.
            length = len(person.get_media_list())
            if length > 0:
                with_media += 1
            
            # Count people with incomplete names.
            for name in [person.get_primary_name()] + person.get_alternate_names():
                if name.get_first_name().strip() == "":
                    incomp_names += 1
                else:
                    if name.get_surname_list():
                        for surname in name.get_surname_list():
                            if surname.get_surname().strip() == "":
                                incomp_names += 1
                    else:
                        incomp_names += 1
                    
            # Count people without families.
            if (not person.get_main_parents_family_handle() and
               not len(person.get_family_handle_list())):
                disconnected += 1
            
            # Count missing birthdays.
            birth_ref = person.get_birth_ref()
            if birth_ref:
                birth = self.__db.get_event_from_handle(birth_ref.ref)
                if not get_date(birth):
                    missing_bday += 1
            else:
                missing_bday += 1
                
            # Count genders.
            if person.get_gender() == Person.FEMALE:
                females += 1
            elif person.get_gender() == Person.MALE:
                males += 1
            else:
                unknowns += 1
                
            # Count unique surnames
            for name in [person.get_primary_name()] + person.get_alternate_names():
                if not name.get_surname().strip() in namelist \
                    and not name.get_surname().strip() == "":
                    namelist.append(name.get_surname().strip())
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Number of individuals: %d") % num_people)
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Males: %d") % males)
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Females: %d") % females)
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Individuals with unknown gender: %d") % 
                            unknowns)
        self.doc.end_paragraph()
                            
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Incomplete names: %d") % incomp_names)
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Individuals missing birth dates: %d") % 
                            missing_bday)
        self.doc.end_paragraph()

        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Disconnected individuals: %d") % 
                            disconnected)
        self.doc.end_paragraph()
                            
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Unique surnames: %d") % len(namelist))
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Individuals with media objects: %d") % 
                            with_media)
        self.doc.end_paragraph()

    def summarize_families(self):
        """
        Write a summary of all the families in the database.
        """
        self.doc.start_paragraph("SR-Heading")
        self.doc.write_text(self._("Family Information"))
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Number of families: %d") % 
                            self.__db.get_number_of_families())
        self.doc.end_paragraph()

    def summarize_media(self):
        """
        Write a summary of all the media in the database.
        """
        total_media = 0
        size_in_bytes = 0
        notfound = []
        
        self.doc.start_paragraph("SR-Heading")
        self.doc.write_text(self._("Media Objects"))
        self.doc.end_paragraph()
        
        total_media = len(self.__db.get_media_object_handles())
        mbytes = "0"
        for media_id in self.__db.get_media_object_handles():
            media = self.__db.get_object_from_handle(media_id)
            try:
                size_in_bytes += posixpath.getsize(
                                 media_path_full(self.__db, media.get_path()))
                length = len(str(size_in_bytes))
                if size_in_bytes <= 999999:
                    mbytes = self._("less than 1")
                else:
                    mbytes = str(size_in_bytes)[:(length-6)]
            except:
                notfound.append(media.get_path())
                
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Number of unique media objects: %d") % 
                            total_media)
        self.doc.end_paragraph()
        
        self.doc.start_paragraph("SR-Normal")
        self.doc.write_text(self._("Total size of media objects: %s MB") % 
                            mbytes)
        self.doc.end_paragraph()
    
        if len(notfound) > 0:
            self.doc.start_paragraph("SR-Heading")
            self.doc.write_text(self._("Missing Media Objects"))
            self.doc.end_paragraph()

            for media_path in notfound:
                self.doc.start_paragraph("SR-Normal")
                self.doc.write_text(media_path)
                self.doc.end_paragraph()

#------------------------------------------------------------------------
#
# SummaryOptions
#
#------------------------------------------------------------------------
class SummaryOptions(MenuReportOptions):
    """
    SummaryOptions provides the options for the SummaryReport.
    """
    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)
        
    def add_menu_options(self, menu):
        """
        Add options to the menu for the summary report.
        """
        category_name = _("Report Options")
        stdoptions.add_localization_option(menu, category_name)

    def make_default_style(self, default_style):
        """Make the default output style for the Summary Report."""
        font = FontStyle()
        font.set_size(16)
        font.set_type_face(FONT_SANS_SERIF)
        font.set_bold(1)
        para = ParagraphStyle()
        para.set_header_level(1)
        para.set_bottom_border(1)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_font(font)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_("The style used for the title of the page."))
        default_style.add_paragraph_style("SR-Title", para)
        
        font = FontStyle()
        font.set_size(12)
        font.set_bold(True)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_top_margin(0)
        para.set_description(_('The basic style used for sub-headings.'))
        default_style.add_paragraph_style("SR-Heading", para)
        
        font = FontStyle()
        font.set_size(12)
        para = ParagraphStyle()
        para.set(first_indent=-0.75, lmargin=.75)
        para.set_font(font)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("SR-Normal", para)

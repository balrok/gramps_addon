# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008-2009  Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2012-2013  Paul Franklin
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
#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
from __future__ import unicode_literals
from functools import partial
import datetime
import time

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.const import URL_HOMEPAGE
from gramps.gen.display.name import displayer as _nd 
from gramps.gen.errors import ReportError
from gramps.gen.plug.docgen import (FontStyle, ParagraphStyle, GraphicsStyle,
                                    FONT_SERIF, PARA_ALIGN_CENTER,
                                    PARA_ALIGN_LEFT, PARA_ALIGN_RIGHT,
                                    IndexMark, INDEX_TYPE_TOC)
from gramps.gen.plug.docgen.fontscale import string_trim
from gramps.gen.plug.menu import (BooleanOption, StringOption, NumberOption, 
                                  EnumeratedListOption, FilterOption,
                                  PersonOption)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.utils.alive import probably_alive
from gramps.gen.datehandler import displayer as _dd
from gramps.gen.lib import (Date, EventRoleType, EventType, Name, NameType,
                            Person, Surname)
from gramps.gen.lib.date import gregorian

import gramps.plugins.lib.libholiday as libholiday
from gramps.plugins.lib.libholiday import g2iso

#------------------------------------------------------------------------
#
# Constants
#
#------------------------------------------------------------------------
pt2cm = ReportUtils.pt2cm
cm2pt = ReportUtils.cm2pt

def _T_(value): # enable deferred translations (see Python docs 22.1.3.4)
    return value
# _T_ is a gramps-defined keyword -- see po/update_po.py and po/genpot.sh

_TITLE1 = _T_("My Calendar")
_TITLE2 = _T_("Produced with Gramps")

#------------------------------------------------------------------------
#
# Calendar
#
#------------------------------------------------------------------------
class Calendar(Report):
    """
    Create the Calendar object that produces the report.
    """
    def __init__(self, database, options, user):
        Report.__init__(self, database, options, user)
        menu = options.menu
        self._user = user
        get_value = lambda name: menu.get_option_by_name(name).get_value()
        
        self.year = get_value('year')
        self.name_format = get_value('name_format')
        self.country = get_value('country')
        self.anniversaries = get_value('anniversaries')
        self.start_dow = get_value('start_dow')
        self.maiden_name = get_value('maiden_name')
        self.alive = get_value('alive')
        self.birthdays = get_value('birthdays')
        self.text1 = get_value('text1')
        self.text2 = get_value('text2')
        self.text3 = get_value('text3')
        self.filter_option = menu.get_option_by_name('filter')
        self.filter = self.filter_option.get_filter()
        pid = get_value('pid')
        self.center_person = database.get_person_from_gramps_id(pid)
        if (self.center_person == None) :
            raise ReportError(_("Person %s is not in the Database") % pid )

        self._locale = self.set_locale(get_value('trans'))

    def get_name(self, person, maiden_name = None):
        """ Return person's name, unless maiden_name given, 
            unless married_name listed. 
        """
        # Get all of a person's names:
        primary_name = person.get_primary_name()
        married_name = None
        names = [primary_name] + person.get_alternate_names()
        for name in names:
            if int(name.get_type()) == NameType.MARRIED:
                married_name = name
                break # use first
        # Now, decide which to use:
        if maiden_name is not None:
            if married_name is not None:
                name = Name(married_name)
            else:
                name = Name(primary_name)
                surname = Surname()
                surname.set_surname(maiden_name)
                name.set_surname_list([surname])
        else:
            name = Name(primary_name)
        name.set_display_as(self.name_format)
        return _nd.display_name(name)
        
    def draw_rectangle(self, style, sx, sy, ex, ey):
        """ This should be in BaseDoc """
        self.doc.draw_line(style, sx, sy, sx, ey)
        self.doc.draw_line(style, sx, sy, ex, sy)
        self.doc.draw_line(style, ex, sy, ex, ey)
        self.doc.draw_line(style, sx, ey, ex, ey)

### The rest of these all have to deal with calendar specific things

    def add_day_item(self, text, month, day, format="CAL-Text", marks=[None]):
        """ Add an item to a day. """
        month_dict = self.calendar.get(month, {})
        day_list = month_dict.get(day, [])
        day_list.append((format, text, marks))
        month_dict[day] = day_list
        self.calendar[month] = month_dict

    def __get_holidays(self):
        """ Get the holidays for the specified country and year """
        holiday_table = libholiday.HolidayTable()
        country = holiday_table.get_countries()[self.country]
        holiday_table.load_holidays(self.year, country)
        for month in range(1, 13):
            for day in range(1, 32):
                holiday_names = holiday_table.get_holidays(month, day) 
                for holiday_name in holiday_names:
                    self.add_day_item(self._(holiday_name), month, day,
                                      "CAL-Holiday")
                    # FIXME translation only works for a limited set of things
                    # (the right fix is to somehow feed the locale into the
                    # HolidayTable class in plugins/lib/libholiday.py and then
                    # probably changing all the holiday code to somehow defer
                    # the translation of holidays, until it can be based
                    # on the passed-in locale, but since that would probably
                    # also mean checking every use of holidays I don't think
                    # it is advisable to do, with a release so imminent)
                    # it is also debatable whether it is worth bothering at
                    # all, since it is hard for me to imagine why a user would
                    # be wanting to generate a translated report with holidays
                    # since I believe its main use will be for dates of people

    def write_report(self):
        """
        The short method that runs through each month and creates a page.
        """
        # initialize the dict to fill:
        self.calendar = {}
        
        # get the information, first from holidays:
        if self.country != 0:
            self.__get_holidays()
            
        # get data from database:
        self.collect_data()
        # generate the report:
        with self._user.progress(_('Calendar Report'), 
                                 _('Formatting months...'),
                                 12) as step:
            for month in range(1, 13):
                step()
                self.print_page(month)

    def print_page(self, month):
        """
        This method actually writes the calendar page.
        """
        style_sheet = self.doc.get_style_sheet()
        ptitle = style_sheet.get_paragraph_style("CAL-Title")
        ptext = style_sheet.get_paragraph_style("CAL-Text")
        pdaynames = style_sheet.get_paragraph_style("CAL-Daynames")
        pnumbers = style_sheet.get_paragraph_style("CAL-Numbers")
        numpos = pt2cm(pnumbers.get_font().get_size())
        ptext1style = style_sheet.get_paragraph_style("CAL-Text1style")
        long_days = self._dd.long_days

        self.doc.start_page()
        width = self.doc.get_usable_width()
        height = self.doc.get_usable_height()
        header = 2.54 # one inch
        mark = None
        if month == 1:
            mark = IndexMark(self._('Calendar Report'), INDEX_TYPE_TOC, 1)
        self.draw_rectangle("CAL-Border", 0, 0, width, height)
        self.doc.draw_box("CAL-Title", "", 0, 0, width, header, mark)
        self.doc.draw_line("CAL-Border", 0, header, width, header)
        year = self.year
        # TRANSLATORS: see 
        # http://gramps-project.org/wiki/index.php?title=Translating_Gramps#Translating_dates
        # to learn how to select proper inflection for your language.
        title = self._("{long_month} {year}").format(
                                long_month = self._dd.long_months[month],
                                year = year
                                ).capitalize()
        mark = IndexMark(title, INDEX_TYPE_TOC, 2)
        font_height = pt2cm(ptitle.get_font().get_size())
        self.doc.center_text("CAL-Title", title,
                             width/2, font_height * 0.25, mark)
        cell_width = width / 7
        cell_height = (height - header)/ 6
        current_date = datetime.date(year, month, 1)
        spacing = pt2cm(1.25 * ptext.get_font().get_size()) # 158
        if current_date.isoweekday() != g2iso(self.start_dow + 1):
            # Go back to previous first day of week, and start from there
            current_ord = (current_date.toordinal() -
                           ((current_date.isoweekday() + 7) -
                            g2iso(self.start_dow + 1)) % 7)
        else:
            current_ord = current_date.toordinal()
        for day_col in range(7):
            font_height = pt2cm(pdaynames.get_font().get_size())
            self.doc.center_text("CAL-Daynames", 
                                 long_days[(day_col+ g2iso(self.start_dow + 1))
                                                        % 7 + 1].capitalize(), 
                                 day_col * cell_width + cell_width/2, 
                                 header - font_height * 1.5)
        for week_row in range(6):
            something_this_week = 0
            for day_col in range(7):
                thisday = current_date.fromordinal(current_ord)
                if thisday.month == month:
                    something_this_week = 1
                    self.draw_rectangle("CAL-Border", day_col * cell_width, 
                                        header + week_row * cell_height, 
                                        (day_col + 1) * cell_width, 
                                        header + (week_row + 1) * cell_height)
                    last_edge = (day_col + 1) * cell_width
                    self.doc.center_text("CAL-Numbers", str(thisday.day), 
                                         day_col * cell_width + cell_width/2, 
                                         header + week_row * cell_height)
                    list_ = self.calendar.get(month, {}).get(thisday.day, [])
                    list_.sort() # to get CAL-Holiday on bottom
                    position = spacing
                    for (format, p, m_list) in list_:
                        for line in reversed(p.split("\n")):
                            # make sure text will fit:
                            if position - 0.1 >= cell_height - numpos: # font daynums
                                break
                            font = ptext.get_font()
                            line = string_trim(font, line, cm2pt(cell_width + 0.2))
                            self.doc.draw_text(format, line, 
                                               day_col * cell_width + 0.1, 
                                               header + (week_row + 1) * cell_height - position - 0.1, m_list[0])
                            if len(m_list) > 1: # index the spouse too
                                self.doc.draw_text(format, "",0,0, m_list[1])
                            position += spacing
                current_ord += 1
        if not something_this_week:
            last_edge = 0
        font_height = pt2cm(1.5 * ptext1style.get_font().get_size())
        x = last_edge + (width - last_edge)/2
        text1 = str(self.text1)
        if text1 == _(_TITLE1):
            text1 = self._(_TITLE1)
        self.doc.center_text("CAL-Text1style", text1,
                             x, height - font_height * 3) 
        text2 = str(self.text2)
        if text2 == _(_TITLE2):
            text2 = self._(_TITLE2)
        self.doc.center_text("CAL-Text2style", text2,
                             x, height - font_height * 2) 
        self.doc.center_text("CAL-Text3style", self.text3,
                             x, height - font_height * 1) 
        self.doc.end_page()

    def collect_data(self):
        """
        This method runs through the data, and collects the relevant dates
        and text.
        """
        db = self.database
        people = db.iter_person_handles()
        with self._user.progress(_('Calendar Report'), 
                                 _('Applying Filter...'), 
                                 db.get_number_of_people()) as step:
            people = self.filter.apply(self.database, people, step)

        ngettext = self._locale.translation.ngettext # to see "nearby" comments

        with self._user.progress(_('Calendar Report'), 
                                 _('Reading database...'),
                                 len(people)) as step:
            for person_handle in people:
                step()
                person = db.get_person_from_handle(person_handle)
                mark = ReportUtils.get_person_mark(db, person)
                birth_ref = person.get_birth_ref()
                birth_date = None
                if birth_ref:
                    birth_event = db.get_event_from_handle(birth_ref.ref)
                    birth_date = birth_event.get_date_object()

                if (self.birthdays and birth_date is not None and birth_date.is_valid()):
                    birth_date = gregorian(birth_date)

                    year = birth_date.get_year()
                    month = birth_date.get_month()
                    day = birth_date.get_day()

                    prob_alive_date = Date(self.year, month, day)

                    nyears = self.year - year
                    # add some things to handle maiden name:
                    father_lastname = None # husband, actually
                    if self.maiden_name in ['spouse_first', 'spouse_last']: # get husband's last name:
                        if person.get_gender() == Person.FEMALE:
                            family_list = person.get_family_handle_list()
                            if family_list:
                                if self.maiden_name == 'spouse_first':
                                    fhandle = family_list[0]
                                else:
                                    fhandle = family_list[-1]
                                fam = db.get_family_from_handle(fhandle)
                                father_handle = fam.get_father_handle()
                                mother_handle = fam.get_mother_handle()
                                if mother_handle == person_handle:
                                    if father_handle:
                                        father = db.get_person_from_handle(father_handle)
                                        if father:
                                            father_lastname = father.get_primary_name().get_surname()
                    short_name = self.get_name(person, father_lastname)
                    alive = probably_alive(person, db, prob_alive_date)

                    if  not self.alive or alive:
                        if nyears == 0:
                            text = self._('%(person)s, birth') % {
                                                'person' : short_name }
                        else:
                            # translators: leave all/any {...} untranslated
                            text = ngettext('{person}, {age}',
                                            '{person}, {age}',
                                            nyears).format(person=short_name,
                                                           age=nyears)
                        self.add_day_item(text, month, day, marks=[mark])
                if self.anniversaries:
                    family_list = person.get_family_handle_list()
                    for fhandle in family_list: 
                        fam = db.get_family_from_handle(fhandle)
                        father_handle = fam.get_father_handle()
                        mother_handle = fam.get_mother_handle()
                        if father_handle == person.get_handle():
                            spouse_handle = mother_handle
                        else:
                            continue # with next person if the father is not "person"
                                     # this will keep from duplicating the anniversary
                        if spouse_handle:
                            spouse = db.get_person_from_handle(spouse_handle)
                            if spouse:
                                s_m = ReportUtils.get_person_mark(db, spouse)
                                spouse_name = self.get_name(spouse)
                                short_name = self.get_name(person)
                                # TEMP: this will handle ordered events
                                # GRAMPS 3.0 will have a new mechanism for start/stop events
                                are_married = None
                                for event_ref in fam.get_event_ref_list():
                                    event = db.get_event_from_handle(event_ref.ref)
                                    et = EventType
                                    rt = EventRoleType
                                    if event.type in [et.MARRIAGE, 
                                                      et.MARR_ALT] and \
                                        (event_ref.get_role() == rt.FAMILY or 
                                         event_ref.get_role() == rt.PRIMARY ):
                                        are_married = event
                                    elif event.type in [et.DIVORCE, 
                                                        et.ANNULMENT, 
                                                        et.DIV_FILING] and \
                                        (event_ref.get_role() == rt.FAMILY or 
                                         event_ref.get_role() == rt.PRIMARY ):
                                        are_married = None
                                if are_married is not None:
                                    for event_ref in fam.get_event_ref_list():
                                        event = db.get_event_from_handle(event_ref.ref)
                                        event_obj = event.get_date_object()

                                        if event_obj.is_valid():
                                            event_obj = gregorian(event_obj)

                                            year = event_obj.get_year()
                                            month = event_obj.get_month()
                                            day = event_obj.get_day()

                                            prob_alive_date = Date(self.year, month, day)
        
                                            nyears = self.year - year
                                            if nyears == 0:
                                                text = self._('%(spouse)s and\n %(person)s, wedding') % {
                                                        'spouse' : spouse_name,
                                                        'person' : short_name,
                                                        }
                                            else:
                                                # translators: leave all/any {...} untranslated
                                                text = ngettext("{spouse} and\n {person}, {nyears}", 
                                                                "{spouse} and\n {person}, {nyears}",
                                                                nyears).format(spouse=spouse_name, person=short_name, nyears=nyears)

                                            alive1 = probably_alive(person,
                                                        self.database,
                                                        prob_alive_date)
                                            alive2 = probably_alive(spouse,
                                                        self.database,
                                                        prob_alive_date)
                                            if ((self.alive and alive1 and alive2) or not self.alive):
                                                self.add_day_item(text, month, day,
                                                                  marks=[mark,s_m])

#------------------------------------------------------------------------
#
# CalendarOptions
#
#------------------------------------------------------------------------
class CalendarOptions(MenuReportOptions):
    """ Calendar options for graphic calendar """
    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        self.__filter = None
        MenuReportOptions.__init__(self, name, dbase)
    
    def add_menu_options(self, menu):
        """ Add the options for the graphical calendar """

        ##########################
        category_name = _("Report Options")
        add_option = partial(menu.add_option, category_name)
        ##########################

        year = NumberOption(_("Year of calendar"), time.localtime()[0], 
                            1000, 3000)
        year.set_help(_("Year of calendar"))
        add_option("year", year)

        self.__filter = FilterOption(_("Filter"), 0)
        self.__filter.set_help(
               _("Select filter to restrict people that appear on calendar"))
        add_option("filter", self.__filter)
        
        self.__pid = PersonOption(_("Center Person"))
        self.__pid.set_help(_("The center person for the report"))
        add_option("pid", self.__pid)
        self.__pid.connect('value-changed', self.__update_filters)
        
        self.__update_filters()

        stdoptions.add_name_format_option(menu, category_name)

        country = EnumeratedListOption(_("Country for holidays"), 0)
        holiday_table = libholiday.HolidayTable()
        countries = holiday_table.get_countries()
        countries.sort()
        if (len(countries) == 0 or 
            (len(countries) > 0 and countries[0] != '')):
            countries.insert(0, '')
        count = 0
        for c in countries:
            country.add_item(count, c)
            count += 1
        country.set_help(_("Select the country to see associated holidays"))
        add_option("country", country)

        start_dow = EnumeratedListOption(_("First day of week"), 1)
        long_days = _dd.long_days
        for count in range(1, 8):
            # conversion between gramps numbering (sun=1) and iso numbering (mon=1) of weekdays below
            start_dow.add_item((count+5) % 7 + 1, long_days[count].capitalize()) 
        start_dow.set_help(_("Select the first day of the week for the calendar"))
        add_option("start_dow", start_dow) 

        maiden_name = EnumeratedListOption(_("Birthday surname"), "own")
        maiden_name.add_item("spouse_first", _("Wives use husband's surname (from first family listed)"))
        maiden_name.add_item("spouse_last", _("Wives use husband's surname (from last family listed)"))
        maiden_name.add_item("own", _("Wives use their own surname"))
        maiden_name.set_help(_("Select married women's displayed surname"))
        add_option("maiden_name", maiden_name)

        alive = BooleanOption(_("Include only living people"), True)
        alive.set_help(_("Include only living people in the calendar"))
        add_option("alive", alive)

        birthdays = BooleanOption(_("Include birthdays"), True)
        birthdays.set_help(_("Include birthdays in the calendar"))
        add_option("birthdays", birthdays)

        anniversaries = BooleanOption(_("Include anniversaries"), True)
        anniversaries.set_help(_("Include anniversaries in the calendar"))
        add_option("anniversaries", anniversaries)

        stdoptions.add_localization_option(menu, category_name)

        category_name = _("Text Options")
        add_option = partial(menu.add_option, _("Text Options"))

        text1 = StringOption(_("Text Area 1"), _(_TITLE1)) 
        text1.set_help(_("First line of text at bottom of calendar"))
        add_option("text1", text1)

        text2 = StringOption(_("Text Area 2"), _(_TITLE2))
        text2.set_help(_("Second line of text at bottom of calendar"))
        add_option("text2", text2)

        text3 = StringOption(_("Text Area 3"), URL_HOMEPAGE)
        text3.set_help(_("Third line of text at bottom of calendar"))
        add_option("text3", text3)
        
    def __update_filters(self):
        """
        Update the filter list based on the selected person
        """
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        filter_list = ReportUtils.get_person_filters(person, False)
        self.__filter.set_filters(filter_list)

    def make_my_style(self, default_style, name, description, 
                      size=9, font=FONT_SERIF, justified ="left", 
                      color=None, align=PARA_ALIGN_CENTER, 
                      shadow = None, italic=0, bold=0, borders=0, indent=None):
        """ Create paragraph and graphic styles of the same name """
        # Paragraph:
        f = FontStyle()
        f.set_size(size)
        f.set_type_face(font)
        f.set_italic(italic)
        f.set_bold(bold)
        p = ParagraphStyle()
        p.set_font(f)
        p.set_alignment(align)
        p.set_description(description)
        p.set_top_border(borders)
        p.set_left_border(borders)
        p.set_bottom_border(borders)
        p.set_right_border(borders)
        if indent:
            p.set(first_indent=indent)
        if justified == "left":
            p.set_alignment(PARA_ALIGN_LEFT)       
        elif justified == "right":
            p.set_alignment(PARA_ALIGN_RIGHT)       
        elif justified == "center":
            p.set_alignment(PARA_ALIGN_CENTER)       
        default_style.add_paragraph_style(name, p)
        # Graphics:
        g = GraphicsStyle()
        g.set_paragraph_style(name)
        if shadow:
            g.set_shadow(*shadow)
        if color is not None:
            g.set_fill_color(color)
        if not borders:
            g.set_line_width(0)
        default_style.add_draw_style(name, g)
        
    def make_default_style(self, default_style):
        """ Add the styles used in this report """
        self.make_my_style(default_style, "CAL-Title", 
                           _('Title text and background color'), 20, 
                           bold=1, italic=1, 
                           color=(0xEA, 0xEA, 0xEA))
        self.make_my_style(default_style, "CAL-Numbers", 
                           _('Calendar day numbers'), 13, 
                           bold=1)
        self.make_my_style(default_style, "CAL-Text", 
                           _('Daily text display'), 9)
        self.make_my_style(default_style, "CAL-Holiday", 
                           _('Holiday text display'), 9,
                           bold=1, italic=1)
        self.make_my_style(default_style, "CAL-Daynames", 
                           _('Days of the week text'), 12, 
                           italic=1, bold=1, 
                           color = (0xEA, 0xEA, 0xEA))
        self.make_my_style(default_style, "CAL-Text1style", 
                           _('Text at bottom, line 1'), 12)
        self.make_my_style(default_style, "CAL-Text2style", 
                           _('Text at bottom, line 2'), 12)
        self.make_my_style(default_style, "CAL-Text3style", 
                           _('Text at bottom, line 3'), 9)
        self.make_my_style(default_style, "CAL-Border", 
                           _('Borders'), borders=True)

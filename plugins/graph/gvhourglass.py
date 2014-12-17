#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2008 Brian G. Matherly
# Copyright (C) 2008      Stephane Charette <stephanecharette@gmail.com>
# Contribution 2009 by    Bob Ham <rah@bash.sh>
# Copyright (C) 2010      Jakim Friant
# Copyright (C) 2013      Paul Franklin
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
Generate an hourglass graph using the GraphViz generator.
"""
#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.errors import ReportError
from gramps.gen.plug.menu import (PersonOption, BooleanOption, NumberOption, 
                                  EnumeratedListOption)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.datehandler import get_date
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback

#------------------------------------------------------------------------
#
# Constant options items
#
#------------------------------------------------------------------------
_COLORS = [ { 'name' : _("B&W outline"),     'value' : "outline" },
            { 'name' : _("Colored outline"), 'value' : "colored" },
            { 'name' : _("Color fill"),      'value' : "filled"  }]


#------------------------------------------------------------------------
#
# HourGlassReport
#
#------------------------------------------------------------------------
class HourGlassReport(Report):
    """
    An hourglass report displays ancestors and descendants of a center person.
    """
    def __init__(self, database, options, user):
        """
        Create HourGlass object that produces the report.
        """
        Report.__init__(self, database, options, user)
        
        # Would be nice to get rid of these 2 hard-coded arrays of colours
        # and instead allow the user to pick-and-choose whatever colour they
        # want.  When/if this is done, take a look at the colour-selection
        # widget and code used in the FamilyLines graph.
        colored = {
            'male': 'dodgerblue4',
            'female': 'deeppink',
            'unknown': 'black',
            'family': 'darkgreen'
        }
        filled = {
            'male': 'lightblue',
            'female': 'lightpink',
            'unknown': 'lightgray',
            'family': 'lightyellow'
        }

        self.__db = database
        self.__used_people = []
        
        menu = options.menu
        self.max_descend = menu.get_option_by_name('maxdescend').get_value()
        self.max_ascend  = menu.get_option_by_name('maxascend').get_value()
        pid = menu.get_option_by_name('pid').get_value()
        self.center_person = database.get_person_from_gramps_id(pid)
        if (self.center_person == None) :
            raise ReportError(_("Person %s is not in the Database") % pid )
        self.colorize = menu.get_option_by_name('color').get_value()
        if self.colorize == 'colored':
            self.colors = colored
        elif self.colorize == 'filled':
            self.colors = filled
        self.roundcorners = menu.get_option_by_name('roundcorners').get_value()

        self.set_locale(menu.get_option_by_name('trans').get_value())

        name_format = menu.get_option_by_name("name_format").get_value()
        if name_format != 0:
            self._name_display.set_default_format(name_format)

    def write_report(self):
        """
        Generate the report.
        """
        self.add_person(self.center_person)
        self.traverse_up(self.center_person, 1)
        self.traverse_down(self.center_person, 1)
        
    def traverse_down(self, person, gen):
        """
        Recursively find the descendants of the given person.
        """
        if gen > self.max_descend:
            return
        for family_handle in person.get_family_handle_list():
            family = self.__db.get_family_from_handle(family_handle)
            self.add_family(family)
            self.doc.add_link( person.get_gramps_id(), family.get_gramps_id() )
            for child_ref in family.get_child_ref_list():
                child_handle = child_ref.get_reference_handle()
                if child_handle not in self.__used_people:
                    # Avoid going down paths twice when descendant cousins marry
                    self.__used_people.append(child_handle)
                    child = self.__db.get_person_from_handle(child_handle)
                    self.add_person(child)
                    self.doc.add_link(family.get_gramps_id(), 
                                      child.get_gramps_id() )
                    self.traverse_down(child, gen+1)
                
    def traverse_up(self, person, gen):
        """
        Recursively find the ancestors of the given person.
        """
        if gen > self.max_ascend:
            return
        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self.__db.get_family_from_handle(family_handle)
            family_id = family.get_gramps_id()
            self.add_family(family)
            self.doc.add_link( family_id, person.get_gramps_id(), 
                               head='none', tail='normal' )
            father_handle = family.get_father_handle()
            if father_handle and father_handle not in self.__used_people:
                self.__used_people.append(father_handle)
                father = self.__db.get_person_from_handle(father_handle)
                self.add_person(father)
                self.doc.add_link( father.get_gramps_id(), family_id, 
                                   head='none', tail='normal' )
                self.traverse_up(father, gen+1)
            mother_handle = family.get_mother_handle()
            if mother_handle and mother_handle not in self.__used_people:
                self.__used_people.append(mother_handle)
                mother = self.__db.get_person_from_handle( mother_handle )
                self.add_person( mother )
                self.doc.add_link( mother.get_gramps_id(), family_id, 
                                   head='none', tail='normal' )
                self.traverse_up( mother, gen+1 )

    def add_person(self, person):
        """
        Add a person to the Graph. The node id will be the person's gramps id.
        """
        p_id = person.get_gramps_id()
        name = self._name_display.display(person)
        
        birth_evt = get_birth_or_fallback(self.__db, person)
        if birth_evt:
            birth = self._get_date(birth_evt.get_date_object())
        else:
            birth = ""
        
        death_evt = get_death_or_fallback(self.__db, person)
        if death_evt:
            death = self._get_date(death_evt.get_date_object())
        else:
            death = ""

        label = "%s \\n(%s - %s)" % (name, birth, death)
            
        (shape, style, color, fill) = self.get_gender_style(person)
        self.doc.add_node(p_id, label, shape, color, style, fill)
        
    def add_family(self, family):
        """
        Add a family to the Graph. The node id will be the family's gramps id.
        """
        family_id = family.get_gramps_id()
        label = ""
        marriage = ReportUtils.find_marriage(self.__db, family)
        if marriage:
            label = self._get_date(marriage.get_date_object())
        color = ""
        fill = ""
        style = "solid"
        if self.colorize == 'colored':
            color = self.colors['family']
        elif self.colorize == 'filled':
            fill = self.colors['family']
            style = "filled"
        self.doc.add_node(family_id, label, "ellipse", color, style, fill)

    def get_gender_style(self, person):
        "return gender specific person style"
        gender = person.get_gender()
        shape = "box"
        style = "solid"
        color = ""
        fill = ""

        if gender == person.FEMALE and self.roundcorners:
            style = "rounded"
        elif gender == person.UNKNOWN:
            shape = "hexagon"

        if self.colorize == 'colored':
            if gender == person.MALE:
                color = self.colors['male']
            elif gender == person.FEMALE:
                color = self.colors['female']
            else:
                color = self.colors['unknown']
        elif self.colorize == 'filled':
            style += ",filled"
            if gender == person.MALE:
                fill = self.colors['male']
            elif gender == person.FEMALE:
                fill = self.colors['female']
            else:
                fill = self.colors['unknown']
        return(shape, style, color, fill)


#------------------------------------------------------------------------
#
# HourGlassOptions
#
#------------------------------------------------------------------------
class HourGlassOptions(MenuReportOptions):
    """
    Defines options for the HourGlass report.
    """
    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)
        
    def add_menu_options(self, menu):
        """
        Create all the menu options for this report.
        """
        category_name = _("Options")
        
        pid = PersonOption(_("Center Person"))
        pid.set_help(_("The Center person for the graph"))
        menu.add_option(category_name, "pid", pid)
        
        stdoptions.add_name_format_option(menu, category_name)

        max_gen = NumberOption(_('Max Descendant Generations'), 10, 1, 15)
        max_gen.set_help(_("The number of generations of descendants to "
                           "include in the graph"))
        menu.add_option(category_name, "maxdescend", max_gen)
        
        max_gen = NumberOption(_('Max Ancestor Generations'), 10, 1, 15)
        max_gen.set_help(_("The number of generations of ancestors to "
                           "include in the graph"))
        menu.add_option(category_name, "maxascend", max_gen)

        stdoptions.add_localization_option(menu, category_name)

        ################################
        category_name = _("Graph Style")
        ################################

        color = EnumeratedListOption(_("Graph coloring"), "filled")
        for i in range( 0, len(_COLORS) ):
            color.add_item(_COLORS[i]["value"], _COLORS[i]["name"])
        color.set_help(_("Males will be shown with blue, females "
                         "with red.  If the sex of an individual "
                         "is unknown it will be shown with gray."))
        menu.add_option(category_name, "color", color)

        roundedcorners = BooleanOption(     # see bug report #2180
                    _("Use rounded corners"), False)
        roundedcorners.set_help(
                    _("Use rounded corners to differentiate "
                      "between women and men."))
        menu.add_option(category_name, "roundcorners", roundedcorners)

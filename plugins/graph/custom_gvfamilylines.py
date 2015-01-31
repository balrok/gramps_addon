#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2008  Stephane Charette
# Copyright (C) 2007-2008  Brian G. Matherly
# Copyright (C) 2009-2010  Gary Burton 
# Contribution 2009 by     Bob Ham <rah@bash.sh>
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2011-2013  Paul Franklin
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
Family Lines, a GraphViz-based plugin for Gramps.
"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
from __future__ import unicode_literals
from functools import partial

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
log = logging.getLogger(".FamilyLines")
#------------------------------------------------------------------------
#
# GRAMPS module
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.lib import EventRoleType, EventType, Person, PlaceType, NameType
from gramps.gen.utils.file import media_path_full
from gramps.gui.thumbnails import get_thumbnail_path
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.plug.menu import (TextOption, NumberOption, ColorOption, BooleanOption,
                                  EnumeratedListOption, PersonListOption,
                                  SurnameColorOption)
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback
from gramps.gen.utils.location import get_main_location
from gramps.plugins.lib.libsubstkeyword import SubstKeywords
from gramps.plugins.lib.libtreebase import CalcLines
#------------------------------------------------------------------------
#
# Constant options items
#
#------------------------------------------------------------------------
_COLORS = [ { 'name' : _("B&W outline"),     'value' : "outline" },
            { 'name' : _("Colored outline"), 'value' : "colored" },
            { 'name' : _("Color fill"),      'value' : "filled"  }]

_BORN = _("birth abbreviation|b."),
_DIED = _("death abbreviation|d."),
_MARR = _("marriage abbreviation|m."),

#------------------------------------------------------------------------
#
# A quick overview of the classes we'll be using:
#
#   class FamilyLinesOptions(MenuReportOptions)
#       - this class is created when the report dialog comes up
#       - all configuration controls for the report are created here
#       - see src/ReportBase/_ReportOptions.py for more information
#
#   class FamilyLinesReport(Report)
#       - this class is created only after the user clicks on "OK"
#       - the actual report generation is done by this class
#       - see src/ReportBase/_Report.py for more information
#
# Likely to be of additional interest is register_report() at the
# very bottom of this file.
#
#------------------------------------------------------------------------

class FamilyLinesOptions(MenuReportOptions):
    """
    Defines all of the controls necessary
    to configure the FamilyLines reports.
    """
    def __init__(self, name, dbase):
        self.limit_parents = None
        self.max_parents = None
        self.limit_children = None
        self.max_children = None
        self.include_images = None
        self.image_location = None
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):

        # --------------------------------
        category_name = _('People of Interest')
        add_option = partial(menu.add_option, category_name)
        # --------------------------------

        person_list = PersonListOption(_('People of interest'))
        person_list.set_help(_('People of interest are used as a starting '
                               'point when determining "family lines".'))
        add_option('gidlist', person_list)

        stdoptions.add_name_format_option(menu, category_name)

        followpar = BooleanOption(
                           _('Follow parents to determine family lines'), True)
        followpar.set_help(_('Parents and their ancestors will be '
                             'considered when determining "family lines".'))
        add_option('followpar', followpar)

        followchild = BooleanOption(_('Follow children to determine '
                                      '"family lines"'), True)
        followchild.set_help(_('Children will be considered when '
                               'determining "family lines".'))
        add_option('followchild', followchild)

        remove_extra_people = BooleanOption(
                             _('Try to remove extra people and families'), True)
        remove_extra_people.set_help(_('People and families not directly '
                                       'related to people of interest will '
                                       'be removed when determining '
                                       '"family lines".'))
        add_option('removeextra', remove_extra_people)

        stdoptions.add_localization_option(menu, category_name)

        # ----------------------------
        add_option = partial(menu.add_option, _('Family Colors'))
        # ----------------------------

        surname_color = SurnameColorOption(_('Family colors'))
        surname_color.set_help(_('Colors to use for various family lines.'))
        add_option('surnamecolors', surname_color)

        # -------------------------
        add_option = partial(menu.add_option, _('Individuals'))
        # -------------------------

        color_males = ColorOption(_('Males'), '#e0e0ff')
        color_males.set_help(_('The color to use to display men.'))
        add_option('colormales', color_males)

        color_females = ColorOption(_('Females'), '#ffe0e0')
        color_females.set_help(_('The color to use to display women.'))
        add_option('colorfemales', color_females)

        color_unknown = ColorOption(_('Unknown'), '#e0e0e0')
        color_unknown.set_help(_('The color to use '
                                 'when the gender is unknown.'))
        add_option('colorunknown', color_unknown)

        color_family = ColorOption(_('Families'), '#ffffe0')
        color_family.set_help(_('The color to use to display families.'))
        add_option('colorfamilies', color_family)

        self.limit_parents = BooleanOption(_('Limit the number of ancestors'), 
                                           False)
        self.limit_parents.set_help(_('Whether to '
                                      'limit the number of ancestors.'))
        add_option('limitparents', self.limit_parents)
        self.limit_parents.connect('value-changed', self.limit_changed)

        self.max_parents = NumberOption('', 50, 10, 9999)
        self.max_parents.set_help(_('The maximum number '
                                    'of ancestors to include.'))
        add_option('maxparents', self.max_parents)

        self.limit_children = BooleanOption(_('Limit the number '
                                              'of descendants'), 
                                            False)
        self.limit_children.set_help(_('Whether to '
                                       'limit the number of descendants.'))
        add_option('limitchildren', self.limit_children)
        self.limit_children.connect('value-changed', self.limit_changed)

        self.max_children = NumberOption('', 50, 10, 9999)
        self.max_children.set_help(_('The maximum number '
                                     'of descendants to include.'))
        add_option('maxchildren', self.max_children)

        # --------------------
        add_option = partial(menu.add_option, _('Images'))
        # --------------------

        self.include_images = BooleanOption(_('Include '
                                              'thumbnail images of people'),
                                            True)
        self.include_images.set_help(_('Whether to '
                                       'include thumbnail images of people.'))
        add_option('incimages', self.include_images)
        self.include_images.connect('value-changed', self.images_changed)

        self.image_location = EnumeratedListOption(_('Thumbnail location'), 0)
        self.image_location.add_item(0, _('Above the name'))
        self.image_location.add_item(1, _('Beside the name'))
        self.image_location.set_help(_('Where the thumbnail image '
                                       'should appear relative to the name'))
        add_option('imageonside', self.image_location)

        # ---------------------
        add_option = partial(menu.add_option, _('Options'))
        # ---------------------

        color = EnumeratedListOption(_("Graph coloring"), "filled")
        for i in range(len(_COLORS)):
            color.add_item(_COLORS[i]["value"], _COLORS[i]["name"])
        color.set_help(_("Males will be shown with blue, females "
                         "with red, unless otherwise set above for filled. "
                         "If the sex of an individual "
                         "is unknown it will be shown with gray."))
        add_option("color", color)

        use_roundedcorners = BooleanOption(_('Use rounded corners'), False)
        use_roundedcorners.set_help(_('Use rounded corners to differentiate '
                                      'between women and men.'))
        add_option("useroundedcorners", use_roundedcorners)

        self.include_dates = BooleanOption(_('Include dates'), True)
        self.include_dates.set_help(_('Whether to include dates for people '
                                      'and families.'))
        add_option('incdates', self.include_dates)
        self.include_dates.connect('value-changed', self.include_dates_changed)

        self.justyears = BooleanOption(_("Limit dates to years only"), False)
        self.justyears.set_help(_("Prints just dates' year, neither "
                                  "month or day nor date approximation "
                                  "or interval are shown."))
        add_option("justyears", self.justyears)

        include_places = BooleanOption(_('Include places'), True)
        include_places.set_help(_('Whether to include placenames for people '
                                  'and families.'))
        add_option('incplaces', include_places)

        include_num_children = BooleanOption(
                                      _('Include the number of children'), True)
        include_num_children.set_help(_('Whether to include the number of '
                                        'children for families with more '
                                        'than 1 child.'))
        add_option('incchildcnt', include_num_children)

        include_private = BooleanOption(_('Include private records'), False)
        include_private.set_help(_('Whether to include names, dates, and '
                                   'families that are marked as private.'))
        add_option('incprivate', include_private)


        # --------------------
        add_option = partial(menu.add_option, _('Custom Options'))

        include_extra_childs = BooleanOption(_('Include extra children'), False)
        include_private.set_help(_('Whether to include extra children, which come from another, not displayed, family'))
        add_option('inc_extra_child', include_extra_childs)

        include_extra_childs_num = NumberOption('Full display of how many extra children', 1, 1, 9999)
        include_extra_childs_num.set_help(_('How many extra children are printed with name and date'))
        add_option('inc_extra_child_num', include_extra_childs_num)

        include_extra_gchilds = BooleanOption(_('Include extra grandchildren'), False)
        include_extra_gchilds.set_help(_('Whether to include extra grandchildren, which come from another, not displayed, family'))
        add_option('inc_extra_gchild', include_extra_gchilds)

        include_extra_gchilds_num = NumberOption('Full display of how many extra grandchildren', 1, 1, 9999)
        include_extra_gchilds_num.set_help(_('How many extra grandchildren are printed with name and date'))
        add_option('inc_extra_gchild_num', include_extra_gchilds_num)

        include_extra_gchilds_num = NumberOption('Full display of how many extra grandchildren', 1, 1, 9999)
        include_extra_gchilds_num.set_help(_('How many extra grandchildren are printed with name and date'))
        add_option('inc_extra_gchild_num', include_extra_gchilds_num)


        disp_text_person = TextOption(_("Person\nDisplay Format"),
                           ["$n",
                            "%s $b" %_BORN,
                            "-{%s $d}" %_DIED] )
        disp_text_person.set_help(_("Display format for the fathers box."))
        add_option("person_disp", disp_text_person)

        # --------------------
        
        self.limit_changed()
        self.images_changed()

    def limit_changed(self):
        """
        Handle the change of limiting parents and children.
        """
        self.max_parents.set_available(self.limit_parents.get_value())
        self.max_children.set_available(self.limit_children.get_value())

    def images_changed(self):
        """
        Handle the change of including images.
        """
        self.image_location.set_available(self.include_images.get_value())

    def include_dates_changed(self):
        """
        Enable/disable menu items if dates are required
        """
        if self.include_dates.get_value():
            self.justyears.set_available(True)
        else:
            self.justyears.set_available(False)

#------------------------------------------------------------------------
#
# FamilyLinesReport -- created once the user presses 'OK'
#
#------------------------------------------------------------------------
class FamilyLinesReport(Report):
    def __init__(self, database, options, user):
        """
        Create FamilyLinesReport object that eventually produces the report.
        
        The arguments are:

        database    - the GRAMPS database instance
        options     - instance of the FamilyLinesOptions class for this report
        user        - a gen.user.User() instance
        """
        Report.__init__(self, database, options, user)

        # initialize several convenient variables
        self._db = database
        self._people = set() # handle of people we need in the report
        self._families = set() # handle of families we need in the report
        self._deleted_people = 0
        self._deleted_families = 0
        self._user = user
        
        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()
        
        self._followpar = get_value('followpar')
        self._followchild = get_value('followchild')
        self._removeextra = get_value('removeextra')
        self._gidlist = get_value('gidlist')
        self._colormales = get_value('colormales')
        self._colorfemales = get_value('colorfemales')
        self._colorunknown = get_value('colorunknown')
        self._colorfamilies = get_value('colorfamilies')
        self._limitparents = get_value('limitparents')
        self._maxparents = get_value('maxparents')
        self._limitchildren = get_value('limitchildren')
        self._maxchildren = get_value('maxchildren')
        self._incimages = get_value('incimages')
        self._imageonside = get_value('imageonside')
        self._useroundedcorners = get_value('useroundedcorners')
        self._usesubgraphs = get_value('usesubgraphs')
        self._incdates = get_value('incdates')
        self._just_years = get_value('justyears')
        self._incplaces = get_value('incplaces')
        self._incchildcount = get_value('incchildcnt')
        self._incprivate = get_value('incprivate')
        self._inc_extra_child = get_value('inc_extra_child')
        self._inc_extra_child_num = get_value('inc_extra_child_num')
        self._inc_extra_gchild = get_value('inc_extra_gchild')
        self._inc_extra_gchild_num = get_value('inc_extra_gchild_num')
        self._person_disp = get_value('person_disp')

        # the gidlist is annoying for us to use since we always have to convert
        # the GIDs to either Person or to handles, so we may as well convert the
        # entire list right now and not have to deal with it ever again
        self._interest_set = set()
        if not self._gidlist:
            self._user.warn(_('Empty report'),
                            _('You did not specify anybody'))
        for gid in self._gidlist.split():
            person = self._db.get_person_from_gramps_id(gid)
            print gid
            if person:
                #option can be from another family tree, so person can be None
                self._interest_set.add(person.get_handle())

        lang = menu.get_option_by_name('trans').get_value()
        self._locale = self.set_locale(lang)

        name_format = menu.get_option_by_name("name_format").get_value()
        if name_format != 0:
            self._name_display.set_default_format(name_format)

        # convert the 'surnamecolors' string to a dictionary of names and colors
        self._surnamecolors = {}
        tmp = get_value('surnamecolors')
        if (tmp.find('\xb0') >= 0):
            tmp = tmp.split('\xb0')    # new style delimiter (see bug report #2162)
        else:
            tmp = tmp.split(' ')        # old style delimiter

        while len(tmp) > 1:
            surname = tmp.pop(0).encode('iso-8859-1', 'xmlcharrefreplace')
            colour = tmp.pop(0)
            self._surnamecolors[surname] = colour

        self._colorize = get_value('color')

    def begin_report(self):
        """
        Inherited method; called by report() in _ReportDialog.py
        
        This is where we'll do all of the work of figuring out who
        from the database is going to be output into the report
        """

        # starting with the people of interest, we then add parents:
        self._people.clear()
        self._families.clear()
        if self._followpar:
            self.findParents()

            if self._removeextra:
                self.removeUninterestingParents()

        # ...and/or with the people of interest we add their children:
        if self._followchild:
            self.findChildren()
        # once we get here we have a full list of people
        # and families that we need to generate a report


    def write_report(self):
        """
        Inherited method; called by report() in _ReportDialog.py
        """
        
        # now that begin_report() has done the work, output what we've
        # obtained into whatever file or format the user expects to use

        self.doc.add_comment('# Number of people in database:    %d' 
                             % self._db.get_number_of_people())
        self.doc.add_comment('# Number of people of interest:    %d' 
                             % len(self._people))
        self.doc.add_comment('# Number of families in database:  %d' 
                             % self._db.get_number_of_families())
        self.doc.add_comment('# Number of families of interest:  %d' 
                             % len(self._families))
        if self._removeextra:
            self.doc.add_comment('# Additional people removed:       %d' 
                                 % self._deleted_people)
            self.doc.add_comment('# Additional families removed:     %d' 
                                 % self._deleted_families)
        self.doc.add_comment('# Initial list of people of interest:')
        for handle in self._interest_set:
            person = self._db.get_person_from_handle(handle)
            gid = person.get_gramps_id()
            name = person.get_primary_name().get_regular_name()
            self.doc.add_comment('# -> %s, %s' % (gid, name))

        self.writePeople()
        self.writeFamilies()


    def findParents(self):
        # we need to start with all of our "people of interest"
        ancestorsNotYetProcessed = set(self._interest_set)

        # now we find all the immediate ancestors of our people of interest

        while ancestorsNotYetProcessed:
            handle = ancestorsNotYetProcessed.pop()

            # One of 2 things can happen here:
            #   1) we've already know about this person and he/she is already 
            #      in our list
            #   2) this is someone new, and we need to remember him/her
            #
            # In the first case, there isn't anything else to do, so we simply 
            # go back to the top and pop the next person off the list.
            #
            # In the second case, we need to add this person to our list, and 
            # then go through all of the parents this person has to find more 
            # people of interest.

            if handle not in self._people:

                person = self._db.get_person_from_handle(handle)


                # if this is a private record, and we're not
                # including private records, then go back to the
                # top of the while loop to get the next person
                if person.private and not self._incprivate:
                    continue

                # remember this person!
                self._people.add(handle)

                # see if a family exists between this person and someone else
                # we have on our list of people we're going to output -- if
                # there is a family, then remember it for when it comes time
                # to link spouses together
                for family_handle in person.get_family_handle_list():
                    family = self._db.get_family_from_handle(family_handle)
                    spouse_handle = ReportUtils.find_spouse(person, family)
                    if spouse_handle:
                        if (spouse_handle in self._people or
                           spouse_handle in ancestorsNotYetProcessed):
                            self._families.add(family_handle)

                # if we have a limit on the number of people, and we've
                # reached that limit, then don't attempt to find any
                # more ancestors
                if self._limitparents and (self._maxparents < 
                        len(ancestorsNotYetProcessed) + len(self._people)):
                    # get back to the top of the while loop so we can finish
                    # processing the people queued up in the "not yet 
                    # processed" list
                    continue

                # queue the parents of the person we're processing
                for family_handle in person.get_parent_family_handle_list():
                    family = self._db.get_family_from_handle(family_handle)

                    if not family.private or self._incprivate:
                        father = self._db.get_person_from_handle(
                                                 family.get_father_handle())
                        mother = self._db.get_person_from_handle(
                                                 family.get_mother_handle())
                        if father:
                            if not father.private or self._incprivate:
                                ancestorsNotYetProcessed.add(
                                                 family.get_father_handle())
                                self._families.add(family_handle)
                        if mother:
                            if not mother.private or self._incprivate:
                                ancestorsNotYetProcessed.add(
                                                 family.get_mother_handle())
                                self._families.add(family_handle)

    def removeUninterestingParents(self):
        # start with all the people we've already identified
        unprocessed_parents = set(self._people)

        while len(unprocessed_parents) > 0:
            handle = unprocessed_parents.pop()
            person = self._db.get_person_from_handle(handle)

            # There are a few things we're going to need,
            # so look it all up right now; such as:
            # - who is the child?
            # - how many children?
            # - parents?
            # - spouse?
            # - is a person of interest?
            # - spouse of a person of interest?
            # - same surname as a person of interest?
            # - spouse has the same surname as a person of interest?

            child_handle = None
            child_count = 0
            spouse_handle = None
            spouse_count = 0
            father_handle = None
            mother_handle = None
            spouse_father_handle = None
            spouse_mother_handle = None
            spouse_surname = ""
            surname = person.get_primary_name().get_surname()
            surname = surname.encode('iso-8859-1','xmlcharrefreplace')

            # first we get the person's father and mother
            for family_handle in person.get_parent_family_handle_list():
                family = self._db.get_family_from_handle(family_handle)
                handle = family.get_father_handle()
                if handle in self._people:
                    father_handle = handle
                handle = family.get_mother_handle()
                if handle in self._people:
                    mother_handle = handle

            # now see how many spouses this person has
            for family_handle in person.get_family_handle_list():
                family = self._db.get_family_from_handle(family_handle)
                handle = ReportUtils.find_spouse(person, family)
                if handle in self._people:
                    spouse_count += 1
                    spouse = self._db.get_person_from_handle(handle)
                    spouse_handle = handle
                    spouse_surname = spouse.get_primary_name().get_surname()
                    spouse_surname = spouse_surname.encode(
                                        'iso-8859-1', 'xmlcharrefreplace'
                                        )

                    # see if the spouse has parents
                    if not spouse_father_handle and not spouse_mother_handle:
                        for family_handle in \
                          spouse.get_parent_family_handle_list():
                            family = self._db.get_family_from_handle(
                                                              family_handle)
                            handle = family.get_father_handle()
                            if handle in self._people:
                                spouse_father_handle = handle
                            handle = family.get_mother_handle()
                            if handle in self._people:
                                spouse_mother_handle = handle

            # get the number of children that we think might be interesting
            for family_handle in person.get_family_handle_list():
                family = self._db.get_family_from_handle(family_handle)
                for child_ref in family.get_child_ref_list():
                    if child_ref.ref in self._people:
                        child_count += 1
                        child_handle = child_ref.ref

            # we now have everything we need -- start looking for reasons
            # why this is a person we need to keep in our list, and loop
            # back to the top as soon as a reason is discovered

            # if this person has many children of interest, then we
            # automatically keep this person
            if child_count > 1:
                continue

            # if this person has many spouses of interest, then we
            # automatically keep this person
            if spouse_count > 1:
                continue

            # if this person has parents, then we automatically keep
            # this person
            if father_handle is not None or mother_handle is not None:
                continue

            # if the spouse has parents, then we automatically keep
            # this person
            if spouse_father_handle is not None or spouse_mother_handle is not None:
                continue

            # if this is a person of interest, then we automatically keep
            if person.get_handle() in self._interest_set:
                continue

            # if the spouse is a person of interest, then we keep
            if spouse_handle in self._interest_set:
                continue

            # if the surname (or the spouse's surname) matches a person
            # of interest, then we automatically keep this person
            bKeepThisPerson = False
            for personOfInterestHandle in self._interest_set:
                personOfInterest = self._db.get_person_from_handle(personOfInterestHandle)
                surnameOfInterest = personOfInterest.get_primary_name().get_surname().encode('iso-8859-1','xmlcharrefreplace')
                if surnameOfInterest == surname or surnameOfInterest == spouse_surname:
                    bKeepThisPerson = True
                    break

            if bKeepThisPerson:
                continue

            # if we have a special colour to use for this person,
            # then we automatically keep this person
            if surname in self._surnamecolors:
                continue

            # if we have a special colour to use for the spouse,
            # then we automatically keep this person
            if spouse_surname in self._surnamecolors:
                continue

            # took us a while, but if we get here, then we can remove this person
            self._deleted_people += 1
            self._people.remove(person.get_handle())

            # we can also remove any families to which this person belonged
            for family_handle in person.get_family_handle_list():
                if family_handle in self._families:
                    self._deleted_families += 1
                    self._families.remove(family_handle)

            # if we have a spouse, then ensure we queue up the spouse
            if spouse_handle:
                if spouse_handle not in unprocessed_parents:
                    unprocessed_parents.add(spouse_handle)

            # if we have a child, then ensure we queue up the child
            if child_handle:
                if child_handle not in unprocessed_parents:
                    unprocessed_parents.add(child_handle)


    def findChildren(self):
        # we need to start with all of our "people of interest"
        childrenNotYetProcessed = set(self._interest_set)
        childrenToInclude = set()

        # now we find all the children of our people of interest

        while len(childrenNotYetProcessed) > 0:
            handle = childrenNotYetProcessed.pop()

            if handle not in childrenToInclude:

                person = self._db.get_person_from_handle(handle)

                if person.get_gramps_id() == 'I0057':
                    continue
                # if this is a private record, and we're not
                # including private records, then go back to the
                # top of the while loop to get the next person
                if person.private and not self._incprivate:
                    continue

                # remember this person!
                childrenToInclude.add(handle)

                # if we have a limit on the number of people, and we've
                # reached that limit, then don't attempt to find any
                # more children
                if self._limitchildren and (
                    self._maxchildren < (
                        len(childrenNotYetProcessed) + len(childrenToInclude)
                        )
                    ):
                    # get back to the top of the while loop so we can finish
                    # processing the people queued up in the "not yet processed" list
                    continue

                # iterate through this person's families
                for family_handle in person.get_family_handle_list():
                    family = self._db.get_family_from_handle(family_handle)
                    if (family.private and self._incprivate) or not family.private:

                        # queue up any children from this person's family
                        for childRef in family.get_child_ref_list():
                            child = self._db.get_person_from_handle(childRef.ref)
                            if (child.private and self._incprivate) or not child.private:
                                childrenNotYetProcessed.add(child.get_handle())
                                self._families.add(family_handle)

                        # include the spouse from this person's family
                        spouse_handle = ReportUtils.find_spouse(person, family)
                        if spouse_handle:
                            spouse = self._db.get_person_from_handle(spouse_handle)
                            if (spouse.private and self._incprivate) or not spouse.private:
                                childrenToInclude.add(spouse_handle)
                                self._families.add(family_handle)

        # we now merge our temp set "childrenToInclude" into our master set
        self._people.update(childrenToInclude)

    def getNameAndBirthDeath(self, person):
        bth_event = get_birth_or_fallback(self._db, person)
        dth_event = get_death_or_fallback(self._db, person)
        birthStr = None
        deathStr = None
        if bth_event and self._incdates:
            if not bth_event.private or self._incprivate:
                date = bth_event.get_date_object()
                birthStr = '%i' % date.get_year()
        if dth_event and self._incdates:
            if not dth_event.private or self._incprivate:
                date = dth_event.get_date_object()
                deathStr = '%i' % date.get_year()

        label = self._name_display.display(person)
        if birthStr or deathStr:
            label += ' ('
            if birthStr:
                label += '*%s' % birthStr
            if deathStr:
                label += '-%s' % deathStr
            label += ')'
        return label

    def getOccupations(self, person):
        occupations = []
        for event_ref in person.get_primary_event_ref_list():
            event = self._db.get_event_from_handle(event_ref.ref)
            if event.get_type() == EventType.OCCUPATION:
                if (event.private and self._incprivate) or not event.private:
                    occupations.append(event.description)
        return occupations


    # returns a list of tuple (person, string) with the child
    # 2nd parameter is a method to format the child
    # 3rd parameter is a method to filter the families
    def getChildList(self, person, formatting_method, filter_method):
        children = []
        for family_handle in person.get_family_handle_list():
            if filter_method(family_handle):
                continue
            family = self._db.get_family_from_handle(family_handle)
            if family.private and not self._incprivate:
                continue
            for childRef in family.get_child_ref_list():
                child = self._db.get_person_from_handle(childRef.ref)
                if (child.private and self._incprivate) or not child.private:
                    children.append((child, formatting_method(child)))
        return children

    def getExtraChildren(self, person, lineDelimiter):
        label = ''
        if not self._inc_extra_child:
            return label

        def filter_family(family_handle):
            return family_handle in self._families

        children = self.getChildList(person, self.getNameAndBirthDeath, filter_family)
        if len(children) > 0:
            # label += '<div style="text-align:left">'
            # TODO make translatable
            label += 'Mehr Kinder: '+ unicode(len(children))
            if len(children) < self._inc_extra_child_num:
                for i in children:
                    if i[1]:
                        label += lineDelimiter + i[1]

        if not self._inc_extra_gchild:
            return label

        grandChildren = []
        for i in children:
            grandChildren.extend(self.getChildList(i[0], self.getNameAndBirthDeath, filter_family))
        # TODO make translatable
        if len(grandChildren) > 0:
            label += lineDelimiter + 'Enkel: '+ unicode(len(grandChildren))
            if len(grandChildren) < self._inc_extra_gchild_num:
                for i in grandChildren:
                    if i[1]:
                        label += lineDelimiter + i[1]
        return label

    def getDisplayName(self, person, use_html = False):
        nameRepl = self._name_display.display(person)
        if int(person.get_primary_name().get_type()) != NameType.BIRTH:
            nameRepl += ' (geb. '+ self.getBirthSurname(person) + ')'
        if use_html:
            call_name = person.get_primary_name().get_call_name()
            if len(call_name) > 0:
                nameRepl = nameRepl.replace(call_name, '<B>' + call_name + '</B>')
        return nameRepl

    def getBirthSurname(self, person):
        for alt_name in person.get_alternate_names():
            if int(alt_name.get_type()) == NameType.BIRTH:
                return alt_name.get_surname()
        return '?'

    def writePeople(self):
        self.doc.add_comment('')
        # TODO there could be improvement and is still something wrong (wrong order)
        # also people should be sorted by their marriage - so first marriage, then 2nd marriage
        def personSorter(handle):
            person = self._db.get_person_from_handle(handle)

            #bth_event = get_birth_or_fallback(self._db, person)
            #if bth_event and not bth_event.private or self._incprivate:
            #    return bth_event.get_date_object().get_year()
            #return 1
            fHandle = person.get_main_parents_family_handle()
            if fHandle:
                family = self._db.get_family_from_handle(fHandle)
                if family:
                    childList = family.get_child_ref_list()
                    childListRef = []
                    for ch in childList:
                        childListRef.append(ch.ref)
                    try:
                        return childListRef.index(person.get_handle())
                    except:
                        pass
            return 0

        sorted_people = sorted(self._people, key=personSorter)
        for handle in sorted_people:
            person = self._db.get_person_from_handle(handle)
            print self.getDisplayName(person), personSorter(handle)

        for handle in sorted_people:
            person = self._db.get_person_from_handle(handle)

            # figure out what colour to use
            gender = person.get_gender()
            colour = self._colorunknown
            if gender == Person.MALE:
                colour = self._colormales
            elif gender == Person.FEMALE:
                colour = self._colorfemales

            # see if we have surname colours that match this person
            surname = person.get_primary_name().get_surname().encode('iso-8859-1','xmlcharrefreplace')
            if surname in self._surnamecolors:
                colour = self._surnamecolors[surname]

            occupations = self.getOccupations(person)

            # see if we have an image to use for this person
            imagePath = None
            if self._incimages:
                mediaList = person.get_media_list()
                if len(mediaList) > 0:
                    mediaHandle = mediaList[0].get_reference_handle()
                    media = self._db.get_object_from_handle(mediaHandle)
                    mediaMimeType = media.get_mime_type()
                    if mediaMimeType[0:5] == "image":
                        imagePath = get_thumbnail_path(
                                        media_path_full(self._db, 
                                                        media.get_path()),
                                        rectangle=mediaList[0].get_rectangle())

            # put the label together and output this person
            label = ""
            lineDelimiter = '<BR/>'

            # if we have an image, then start an HTML table;
            # remember to close the table afterwards!
            if imagePath:
                label = ('<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" '
                         'CELLBORDER="0"><TR><TD><IMG SRC="%s"/></TD>'
                            % imagePath
                        )
                if self._imageonside == 0:
                    label += '</TR><TR>'
                label += '<TD>'



            fHandle = person.get_main_parents_family_handle()
            display_repl = [] # self.get_val("replace_list")
            calc = CalcLines(self._db, display_repl, self._locale, self._name_display)
            replacedText = calc.calc_lines(person.get_handle(), fHandle, self._person_disp)

            occRepl = ''
            if len(occupations) > 0:
                plural = ''
                if len(occupations) > 1:
                    plural = 'e'
                occRepl = 'Beruf%s: %s' % (plural, ', '.join(occupations))
            newLabel = []
            for index, item in enumerate(replacedText):
                if 'NAME' in replacedText[index]:
                    replacedText[index] = replacedText[index].replace('NAME', self.getDisplayName(person, True))
                if 'OCCUPATION' in replacedText[index]:
                    if occRepl == '':
                        continue
                    replacedText[index] = replacedText[index].replace('OCCUPATION', occRepl)
                if 'MORE_CHILD' in replacedText[index]:
                    xchild = self.getExtraChildren(person, lineDelimiter)
                    if xchild == '':
                        continue
                    xchRepl = ''
                    #xchRepl += '</TD></TR><TR><TD style="font-size:3px">'
                    xchRepl += self.getExtraChildren(person, lineDelimiter)
                    #xchRepl += '</TD></TR><TR><TD>'
                    replacedText[index] = replacedText[index].replace('MORE_CHILD', xchRepl)
                newLabel.append(replacedText[index])

            label += lineDelimiter.join(newLabel)
            if imagePath:
                label += '</TD></TR></TABLE>'

            shape   = "box"
            style   = "solid"
            border  = colour
            fill    = colour

            # do not use colour if this is B&W outline
            if self._colorize == 'outline':
                border  = ""
                fill    = ""

            if gender == person.FEMALE and self._useroundedcorners:
                style = "rounded"
            elif gender == person.UNKNOWN:
                shape = "hexagon"

            # if we're filling the entire node:
            if self._colorize == 'filled':
                style += ",filled"
                border = ""


            # we're done -- add the node
            self.doc.add_node(person.get_gramps_id(),
                 label=label,
                 shape=shape,
                 color=border,
                 style=style,
                 fillcolor=fill,
                 htmloutput=True)

    def writeFamilies(self):
        self.doc.add_comment('')
        ngettext = self._locale.translation.ngettext # to see "nearby" comments

        # loop through all the families we need to output
        for family_handle in self._families:
            family = self._db.get_family_from_handle(family_handle)
            fgid = family.get_gramps_id()

            # figure out a wedding date or placename we can use
            hasWedding = False
            weddingDate = None
            weddingPlace = None
            if self._incdates or self._incplaces:
                for event_ref in family.get_event_ref_list():
                    event = self._db.get_event_from_handle(event_ref.ref)
                    if event.get_type() == EventType.MARRIAGE and \
                    (event_ref.get_role() == EventRoleType.FAMILY or 
                    event_ref.get_role() == EventRoleType.PRIMARY ):
                        # get the wedding date
                        if (event.private and self._incprivate) or not event.private:
                            hasWedding = True
                            if self._incdates:
                                date = event.get_date_object()
                                if self._just_years and date.get_year_valid():
                                    weddingDate = '%i' % date.get_year()
                                else:
                                    weddingDate = self._get_date(date)
                            # get the wedding location
                            if self._incplaces:
                                place = self._db.get_place_from_handle(event.get_place_handle())
                                if place:
                                    location = get_main_location(self._db, place)
                                    if location.get(PlaceType.CITY):
                                        weddingPlace = location.get(PlaceType.CITY)
                                    elif location.get(PlaceType.STATE):
                                        weddingPlace = location.get(PlaceType.STATE)
                                    elif location.get(PlaceType.COUNTRY):
                                        weddingPlace = location.get(PlaceType.COUNTRY)
                        break

            # figure out the number of children (if any)
            childrenStr = None
            if self._incchildcount:
                child_count = 0
                # to make sure only non-private people are counted and to save people who aren't displayed
                notDisplayedPeople = []
                allChild = ''
                for childRef in family.get_child_ref_list():
                    person = self._db.get_person_from_handle(childRef.ref)
                    if (person.private and self._incprivate) or not person.private:
                        child_count += 1
                        if childRef.ref not in self._people:
                            notDisplayedPeople.append(person)
                        allChild += "\n %d. %s" % (child_count, self.getNameAndBirthDeath(person))
                # child_count = len(family.get_child_ref_list())
                if child_count >= 1:
                    # translators: leave all/any {...} untranslated
                    childrenStr = ngettext("{number_of} child",
                                           "{number_of} children", child_count
                                          ).format(number_of=child_count)
                    if len(notDisplayedPeople) > 0:
                        childrenStr += allChild
                        #for childRef in family.get_child_ref_list():
                        #    person = self._db.get_person_from_handle(childRef.ref)
                        #    childLabel = self.getNameAndBirthDeath(person)
                        #    if childLabel:
                        #        childrenStr += "\n"+childLabel

            label = ''

            if hasWedding:
                if label != '':
                    label += '\\n'
                label += '&#8734;' # '&#9901;'
            if weddingDate:
                label += ' %s' % weddingDate
            if weddingPlace:
                if label != '':
                    label += '\\n'
                label += '%s' % weddingPlace
            if childrenStr:
                if label != '':
                    label += '\\n'
                label += '%s' % childrenStr

            shape   = "ellipse"
            style   = "solid"
            border  = self._colorfamilies
            fill    = self._colorfamilies

            # do not use colour if this is B&W outline
            if self._colorize == 'outline':
                border  = ""
                fill    = ""

            # if we're filling the entire node:
            if self._colorize == 'filled':
                style += ",filled"
                border = ""

            # we're done -- add the node
            self.doc.add_node(fgid, label, shape, border, style, fill)

        # now that we have the families written, go ahead and link the parents and children to the families
        for family_handle in self._families:

            # get the parents for this family
            family = self._db.get_family_from_handle(family_handle)
            fgid = family.get_gramps_id()
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()

            self.doc.add_comment('')

            if self._usesubgraphs and father_handle and mother_handle:
                self.doc.start_subgraph(fgid)

            # see if we have a father to link to this family
            if father_handle:
                if father_handle in self._people:
                    father = self._db.get_person_from_handle(father_handle)
                    comment = "father: %s" % father.get_primary_name().get_regular_name()
                    self.doc.add_link(father.get_gramps_id(), fgid, comment=comment)

            # see if we have a mother to link to this family
            if mother_handle:
                if mother_handle in self._people:
                    mother = self._db.get_person_from_handle(mother_handle)
                    comment = "mother: %s" % mother.get_primary_name().get_regular_name()
                    self.doc.add_link(mother.get_gramps_id(), fgid, comment=comment)

            if self._usesubgraphs and father_handle and mother_handle:
                self.doc.end_subgraph()

            # link the children to the family
            for childRef in family.get_child_ref_list():
                if childRef.ref in self._people:
                    child = self._db.get_person_from_handle(childRef.ref)
                    comment = "child:  %s" % child.get_primary_name().get_regular_name()
                    self.doc.add_link(fgid, child.get_gramps_id(), comment=comment)

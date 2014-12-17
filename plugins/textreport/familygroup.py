#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2007-2008  Brian G. Matherly
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

"""Reports/Text Reports/Family Group Report"""

#------------------------------------------------------------------------
#
# Python Library
#
#------------------------------------------------------------------------
from functools import partial

#------------------------------------------------------------------------
#
# GRAMPS 
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from gramps.gen.lib import EventRoleType, EventType, NoteType, Person
from gramps.gen.plug.menu import (BooleanOption, FamilyOption)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle,
                                    TableStyle, TableCellStyle,
                                    FONT_SANS_SERIF, FONT_SERIF, 
                                    INDEX_TYPE_TOC, PARA_ALIGN_CENTER)

#------------------------------------------------------------------------
#
# FamilyGroup
#
#------------------------------------------------------------------------
class FamilyGroup(Report):

    def __init__(self, database, options, user):
        """
        Create the FamilyGroup object that produces the report.
        
        The arguments are:

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        This report needs the following parameters (class variables)
        that come in the options class.
        
        family_handle - Handle of the family to write report on.
        includeAttrs  - Whether to include attributes
        name_format   - Preferred format to display names
        """
        Report.__init__(self, database, options, user)
        menu = options.menu

        self.family_handle = None

        family_id = menu.get_option_by_name('family_id').get_value()
        family = database.get_family_from_gramps_id(family_id)
        if family:
            self.family_handle = family.get_handle()
        else:
            self.family_handle = None

        get_option_by_name = menu.get_option_by_name
        get_value = lambda name:get_option_by_name(name).get_value()        
        self.recursive     = get_value('recursive')
        self.missingInfo   = get_value('missinginfo')
        self.generations   = get_value('generations')
        self.incParEvents  = get_value('incParEvents')
        self.incParAddr    = get_value('incParAddr')
        self.incParNotes   = get_value('incParNotes')
        self.incParNames   = get_value('incParNames')
        self.incParMar     = get_value('incParMar')
        self.incRelDates   = get_value('incRelDates')
        self.incChiMar     = get_value('incChiMar')
        self.includeAttrs  = get_value('incattrs')

        rlocale = self.set_locale(get_value('trans'))
        self._ = rlocale.translation.sgettext # needed for English

        name_format = menu.get_option_by_name("name_format").get_value()
        if name_format != 0:
            self._name_display.set_default_format(name_format)

    def dump_parent_event(self, name,event):
        place = ""
        date = ""
        descr = ""
        if event:
            date = self._get_date(event.get_date_object())
            place_handle = event.get_place_handle()
            place = ReportUtils.place_name(self.database,place_handle)
            descr = event.get_description()
            
            if self.includeAttrs:
                for attr in event.get_attribute_list():
                    if descr:
                        # translators: needed for Arabic, ignore otherwise
                        descr += self._("; ")
                    attr_type = self._get_type(attr.get_type())
                    # translators: needed for French, ignore otherwise
                    descr += self._("%(str1)s: %(str2)s") % {
                                          'str1' : self._(attr_type),
                                          'str2' : attr.get_value() }

        self.doc.start_row()
        self.doc.start_cell("FGR-TextContents")
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(name)
        self.doc.end_paragraph()
        self.doc.end_cell()
        
        if descr:
            self.doc.start_cell("FGR-TextContentsEnd",2)
            self.doc.start_paragraph('FGR-Normal')
            self.doc.write_text(descr)
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.end_row()
            
            if date or place:
                self.doc.start_row()
                self.doc.start_cell("FGR-TextContents")
                self.doc.start_paragraph('FGR-Normal')
                self.doc.end_paragraph()
                self.doc.end_cell()
                
        if (date or place) or not descr:
            self.doc.start_cell("FGR-TextContents")
            self.doc.start_paragraph('FGR-Normal')
            self.doc.write_text(date)
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.start_cell("FGR-TextContentsEnd")
            self.doc.start_paragraph('FGR-Normal')
            self.doc.write_text(place)
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.end_row()
        
    def dump_parent_parents(self,person):
        family_handle = person.get_main_parents_family_handle()
        father_name = ""
        mother_name = ""
        if family_handle:
            family = self.database.get_family_from_handle(family_handle)
            father_handle = family.get_father_handle() 
            if father_handle:
                father = self.database.get_person_from_handle(father_handle)
                father_name = self._name_display.display(father)
                if self.incRelDates:
                    birth_ref = father.get_birth_ref()
                    birth = "  "
                    if birth_ref:
                        event = self.database.get_event_from_handle(birth_ref.ref)
                        birth = self._get_date(event.get_date_object())
                    death_ref = father.get_death_ref()
                    death = "  "
                    if death_ref:
                        event = self.database.get_event_from_handle(death_ref.ref)
                        death = self._get_date(event.get_date_object())
                    if birth_ref or death_ref:
                        father_name = "%s (%s - %s)" % (father_name,birth,death)
            mother_handle = family.get_mother_handle() 
            if mother_handle:
                mother = self.database.get_person_from_handle(mother_handle)
                mother_name = self._name_display.display(mother)
                if self.incRelDates:
                    birth_ref = mother.get_birth_ref()
                    birth = "  "
                    if birth_ref:
                        event = self.database.get_event_from_handle(birth_ref.ref)
                        birth = self._get_date(event.get_date_object())
                    death_ref = mother.get_death_ref()
                    death = "  "
                    if death_ref:
                        event = self.database.get_event_from_handle(death_ref.ref)
                        death = self._get_date(event.get_date_object())
                    if birth_ref or death_ref:
                        mother_name = "%s (%s - %s)" % (mother_name,birth,death)
        
        if father_name != "":
            self.doc.start_row()
            self.doc.start_cell("FGR-TextContents")
            self.doc.start_paragraph('FGR-Normal')
            self.doc.write_text(self._("Father"))
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.start_cell("FGR-TextContentsEnd",2)
            self.doc.start_paragraph('FGR-Normal')
            mark = ReportUtils.get_person_mark(self.database,father)
            self.doc.write_text(father_name,mark)
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.end_row()
        elif self.missingInfo:
            self.dump_parent_line(self._("Father"), "")

        if mother_name != "":
            self.doc.start_row()
            self.doc.start_cell("FGR-TextContents")
            self.doc.start_paragraph('FGR-Normal')
            self.doc.write_text(self._("Mother"))
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.start_cell("FGR-TextContentsEnd",2)
            self.doc.start_paragraph('FGR-Normal')
            mark = ReportUtils.get_person_mark(self.database,mother)
            self.doc.write_text(mother_name,mark)
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.end_row()
        elif self.missingInfo:
            self.dump_parent_line(self._("Mother"), "")

    def dump_parent_line(self, name, text):
        self.doc.start_row()
        self.doc.start_cell("FGR-TextContents")
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(name)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.start_cell("FGR-TextContentsEnd",2)
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(text)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.end_row()

    def dump_parent_noteline(self, name, note):
        self.doc.start_row()
        self.doc.start_cell("FGR-TextContents")
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(name)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.start_cell("FGR-TextContentsEnd", 2)
        self.doc.write_styled_note(note.get_styledtext(),
                                   note.get_format(), 'FGR-Note',
                                   contains_html= (note.get_type() ==
                                       NoteType.HTML_CODE)
                                  )
        self.doc.end_cell()
        self.doc.end_row()
    
    def dump_parent(self,title,person_handle):

        if not person_handle and not self.missingInfo:
            return
        elif not person_handle:
            person = Person()
        else:
            person = self.database.get_person_from_handle(person_handle)
        name = self._name_display.display(person)
        
        self.doc.start_table(title,'FGR-ParentTable')
        self.doc.start_row()
        self.doc.start_cell('FGR-ParentHead',3)
        self.doc.start_paragraph('FGR-ParentName')
        self.doc.write_text(title + ': ')
        mark = ReportUtils.get_person_mark(self.database,person)
        self.doc.write_text(name,mark)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.end_row()

        birth_ref = person.get_birth_ref()
        birth = None
        evtName = self._("Birth")
        if birth_ref:
            birth = self.database.get_event_from_handle(birth_ref.ref)
        if birth or self.missingInfo:
            self.dump_parent_event(evtName,birth)

        death_ref = person.get_death_ref()
        death = None
        evtName = self._("Death")
        if death_ref:
            death = self.database.get_event_from_handle(death_ref.ref)
        if death or self.missingInfo:
            self.dump_parent_event(evtName,death)

        self.dump_parent_parents(person)

        if self.incParEvents:
            for event_ref in person.get_primary_event_ref_list():
                if event_ref != birth_ref and event_ref != death_ref:
                    event = self.database.get_event_from_handle(event_ref.ref)
                    event_type = self._get_type(event.get_type())
                    self.dump_parent_event(self._(event_type),event)

        if self.incParAddr:
            addrlist = person.get_address_list()[:]
            for addr in addrlist:
                location = ReportUtils.get_address_str(addr)
                date = self._get_date(addr.get_date_object())
                
                self.doc.start_row()
                self.doc.start_cell("FGR-TextContents")
                self.doc.start_paragraph('FGR-Normal')
                self.doc.write_text(self._("Address"))
                self.doc.end_paragraph()
                self.doc.end_cell()
                self.doc.start_cell("FGR-TextContents")
                self.doc.start_paragraph('FGR-Normal')
                self.doc.write_text(date)
                self.doc.end_paragraph()
                self.doc.end_cell()
                self.doc.start_cell("FGR-TextContentsEnd")
                self.doc.start_paragraph('FGR-Normal')
                self.doc.write_text(location)
                self.doc.end_paragraph()
                self.doc.end_cell()
                self.doc.end_row()

        if self.incParNotes:
            for notehandle in person.get_note_list():
                note = self.database.get_note_from_handle(notehandle)
                self.dump_parent_noteline(self._("Note"), note)
                
        if self.includeAttrs:
            for attr in person.get_attribute_list():
                attr_type = self._get_type(attr.get_type())
                self.dump_parent_line(self._(attr_type),attr.get_value())

        if self.incParNames:
            for alt_name in person.get_alternate_names():
                name_type = self._get_type(alt_name.get_type())
                name = self._name_display.display_name(alt_name)
                self.dump_parent_line(self._(name_type), name)

        self.doc.end_table()

    def dump_marriage(self,family):

        if not family:
            return

        m = None
        family_list = family.get_event_ref_list()
        for event_ref in family_list:
            if event_ref:
                event = self.database.get_event_from_handle(event_ref.ref)
                if event.get_type() == EventType.MARRIAGE and \
                (event_ref.get_role() == EventRoleType.FAMILY or 
                event_ref.get_role() == EventRoleType.PRIMARY):
                    m = event
                    break

        if len(family_list) > 0 or self.missingInfo or self.includeAttrs:
            self.doc.start_table("MarriageInfo",'FGR-ParentTable')
            self.doc.start_row()
            self.doc.start_cell('FGR-ParentHead',3)
            self.doc.start_paragraph('FGR-ParentName')
            self.doc.write_text(self._("Marriage:"))
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.end_row()

            self.dump_parent_event(self._("Marriage"),m)
            
            for event_ref in family_list:
                if event_ref:
                    event = self.database.get_event_from_handle(event_ref.ref)
                    if event.get_type() != EventType.MARRIAGE:
                        event_type = self._get_type(event.get_type())
                        self.dump_parent_event(self._(event_type),event)
            
            if self.includeAttrs:
                for attr in family.get_attribute_list():
                    attr_type = self._get_type(attr.get_type())
                    self.dump_parent_line(self._(attr_type),attr.get_value())

            self.doc.end_table()

    def dump_child_event(self,text, name,event):
        date = ""
        place = ""
        if event:
            date = self._get_date(event.get_date_object())
            place_handle = event.get_place_handle()
            if place_handle:
                place = self.database.get_place_from_handle(place_handle).get_title()

        self.doc.start_row()
        self.doc.start_cell(text)
        self.doc.start_paragraph('FGR-Normal')
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.start_cell('FGR-TextContents')
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(name)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.start_cell('FGR-TextContents')
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(date)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.start_cell('FGR-TextContentsEnd')
        self.doc.start_paragraph('FGR-Normal')
        self.doc.write_text(place)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.end_row()
        
    def dump_child(self,index,person_handle):

        person = self.database.get_person_from_handle(person_handle)
        families = len(person.get_family_handle_list())
        birth_ref = person.get_birth_ref()
        if birth_ref:
            birth = self.database.get_event_from_handle(birth_ref.ref)
        else:
            birth = None
        death_ref = person.get_death_ref()
        if death_ref:
            death = self.database.get_event_from_handle(death_ref.ref)
        else:
            death = None
        
        spouse_count = 0; 
        if self.incChiMar:   
            for family_handle in person.get_family_handle_list():
                family = self.database.get_family_from_handle(family_handle)
                spouse_id = None
                if person_handle == family.get_father_handle():
                    spouse_id = family.get_mother_handle()
                else:
                    spouse_id = family.get_father_handle()
                if spouse_id:
                    spouse_count += 1

        self.doc.start_row()
        if spouse_count != 0 or self.missingInfo or death is not None or birth is not None:
            self.doc.start_cell('FGR-TextChild1')
        else:
            self.doc.start_cell('FGR-TextChild2')
        self.doc.start_paragraph('FGR-ChildText')
        index_str = ("%d" % index)
        if person.get_gender() == Person.MALE:
            self.doc.write_text(index_str + self._("acronym for male|M"))
        elif person.get_gender() == Person.FEMALE:
            self.doc.write_text(index_str + self._("acronym for female|F"))
        else:
            self.doc.write_text(self._("acronym for unknown|%dU") % index)
        self.doc.end_paragraph()
        self.doc.end_cell()
        
        name = self._name_display.display(person)
        mark = ReportUtils.get_person_mark(self.database,person)
        self.doc.start_cell('FGR-ChildName',3)
        self.doc.start_paragraph('FGR-ChildText')
        self.doc.write_text(name,mark)
        self.doc.end_paragraph()
        self.doc.end_cell()
        self.doc.end_row()

        if self.missingInfo or birth is not None:
            if spouse_count != 0 or self.missingInfo or death is not None:
                self.dump_child_event('FGR-TextChild1',self._('Birth'),birth)
            else:
                self.dump_child_event('FGR-TextChild2',self._('Birth'),birth)
                
        if self.missingInfo or death is not None:
            if spouse_count == 0 or not self.incChiMar:
                self.dump_child_event('FGR-TextChild2',self._('Death'),death)
            else:
                self.dump_child_event('FGR-TextChild1',self._('Death'),death)

        if self.incChiMar:
            index = 0
            for family_handle in person.get_family_handle_list():
                m = None
                index += 1
                family = self.database.get_family_from_handle(family_handle)

                for event_ref in family.get_event_ref_list():
                    if event_ref:
                        event = self.database.get_event_from_handle(event_ref.ref)
                        if event.type == EventType.MARRIAGE:
                            m = event
                            break  
                
                spouse_id = None

                if person_handle == family.get_father_handle():
                    spouse_id = family.get_mother_handle()
                else:
                    spouse_id = family.get_father_handle()
    
                if spouse_id:
                    self.doc.start_row()
                    if m or index != families:
                        self.doc.start_cell('FGR-TextChild1')
                    else:
                        self.doc.start_cell('FGR-TextChild2')
                    self.doc.start_paragraph('FGR-Normal')
                    self.doc.end_paragraph()
                    self.doc.end_cell()
                    self.doc.start_cell('FGR-TextContents')
                    self.doc.start_paragraph('FGR-Normal')
                    self.doc.write_text(self._("Spouse"))
                    self.doc.end_paragraph()
                    self.doc.end_cell()
                    self.doc.start_cell('FGR-TextContentsEnd',2)
                    self.doc.start_paragraph('FGR-Normal')

                    spouse = self.database.get_person_from_handle(spouse_id)
                    spouse_name = self._name_display.display(spouse)
                    if self.incRelDates:
                        birth = "  "
                        birth_ref = spouse.get_birth_ref()
                        if birth_ref:
                            event = self.database.get_event_from_handle(birth_ref.ref)
                            birth = self._get_date(event.get_date_object())
                        death = "  "
                        death_ref = spouse.get_death_ref()
                        if death_ref:
                            event = self.database.get_event_from_handle(death_ref.ref)
                            death = self._get_date(event.get_date_object())
                        if birth_ref or death_ref:
                            spouse_name = "%s (%s - %s)" % (spouse_name,birth,death)
                    mark = ReportUtils.get_person_mark(self.database,spouse)
                    self.doc.write_text(spouse_name,mark)
                    self.doc.end_paragraph()
                    self.doc.end_cell()
                    self.doc.end_row()
                  
                if m:
                    evtName = self._("Marriage")
                    if index == families:
                        self.dump_child_event('FGR-TextChild2',evtName,m)
                    else:
                        self.dump_child_event('FGR-TextChild1',evtName,m)
            
    def dump_family(self,family_handle,generation):
        self.doc.start_paragraph('FGR-Title')
        if self.recursive and self.generations:
            title = self._("Family Group Report - Generation %d") % generation
        else:
            title = self._("Family Group Report")
        mark = IndexMark(title, INDEX_TYPE_TOC,1)
        self.doc.write_text( title, mark )
        self.doc.end_paragraph()

        family = self.database.get_family_from_handle(family_handle)

        self.dump_parent(self._("Husband"),family.get_father_handle())
        self.doc.start_paragraph("FGR-blank")
        self.doc.end_paragraph()
        
        if self.incParMar:
            self.dump_marriage(family)
            self.doc.start_paragraph("FGR-blank")
            self.doc.end_paragraph()

        self.dump_parent(self._("Wife"),family.get_mother_handle())

        length = len(family.get_child_ref_list())
        if length > 0:
            self.doc.start_paragraph("FGR-blank")
            self.doc.end_paragraph()
            self.doc.start_table('FGR-Children','FGR-ChildTable')
            self.doc.start_row()
            self.doc.start_cell('FGR-ParentHead',4)
            self.doc.start_paragraph('FGR-ParentName')
            self.doc.write_text(self._("Children"))
            self.doc.end_paragraph()
            self.doc.end_cell()
            self.doc.end_row()
            index = 1
            for child_ref in family.get_child_ref_list():
                self.dump_child(index,child_ref.ref)
                index += 1
            self.doc.end_table()

        if self.recursive:
            for child_ref in family.get_child_ref_list():
                child = self.database.get_person_from_handle(child_ref.ref)
                for child_family_handle in child.get_family_handle_list():
                    if child_family_handle != family_handle:
                        self.doc.page_break()
                        self.dump_family(child_family_handle,(generation+1))

    def write_report(self):
        if self.family_handle:
            self.dump_family(self.family_handle,1)
        else:
            self.doc.start_paragraph('FGR-Title')
            self.doc.write_text(self._("Family Group Report"))
            self.doc.end_paragraph()

#------------------------------------------------------------------------
#
# MenuReportOptions
#
#------------------------------------------------------------------------
class FamilyGroupOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)
        
    def add_menu_options(self, menu):
        
        ##########################
        category_name = _("Report Options")
        add_option = partial(menu.add_option, category_name)
        ##########################
        
        family_id = FamilyOption(_("Center Family"))
        family_id.set_help(_("The center family for the report"))
        add_option("family_id", family_id)

        stdoptions.add_name_format_option(menu, category_name)
        
        recursive = BooleanOption(_('Recursive'),False)
        recursive.set_help(_("Create reports for all descendants "
                             "of this family."))
        add_option("recursive", recursive)
        
        stdoptions.add_localization_option(menu, category_name)

        ##########################
        add_option = partial(menu.add_option, _("Include"))
        ##########################
        
        generations = BooleanOption(_("Generation numbers "
                                      "(recursive only)"),True)
        generations.set_help(_("Whether to include the generation on each "
                               "report (recursive only)."))
        add_option("generations", generations)
        
        incParEvents = BooleanOption(_("Parent Events"),False)
        incParEvents.set_help(_("Whether to include events for parents."))
        add_option("incParEvents", incParEvents)
        
        incParAddr = BooleanOption(_("Parent Addresses"),False)
        incParAddr.set_help(_("Whether to include addresses for parents."))
        add_option("incParAddr", incParAddr)
        
        incParNotes = BooleanOption(_("Parent Notes"),False)
        incParNotes.set_help(_("Whether to include notes for parents."))
        add_option("incParNotes", incParNotes)
        
        incattrs = BooleanOption(_("Parent Attributes"),False)
        incattrs.set_help(_("Whether to include attributes."))
        add_option("incattrs", incattrs)
        
        incParNames = BooleanOption(_("Alternate Parent Names"),False)
        incParNames.set_help(_("Whether to include alternate "
                               "names for parents."))
        add_option("incParNames", incParNames)
        
        incParMar = BooleanOption(_("Parent Marriage"),False)
        incParMar.set_help(_("Whether to include marriage information "
                             "for parents."))
        add_option("incParMar", incParMar)
        
        incRelDates = BooleanOption(_("Dates of Relatives"),False)
        incRelDates.set_help(_("Whether to include dates for relatives "
                               "(father, mother, spouse)."))
        add_option("incRelDates", incRelDates)
        
        incChiMar = BooleanOption(_("Children Marriages"),True)
        incChiMar.set_help(_("Whether to include marriage information "
                             "for children."))
        add_option("incChiMar", incChiMar)
        
        ##########################
        add_option = partial(menu.add_option, _("Missing Information"))
        ##########################
                
        missinginfo = BooleanOption(_("Print fields for missing "
                                      "information"),True)
        missinginfo.set_help(_("Whether to include fields for missing "
                               "information."))
        add_option("missinginfo", missinginfo)

    def make_default_style(self,default_style):
        """Make default output style for the Family Group Report."""
        para = ParagraphStyle()
        #Paragraph Styles
        font = FontStyle()
        font.set_size(4)
        para.set_font(font)
        default_style.add_paragraph_style('FGR-blank',para)

        font = FontStyle()
        font.set_type_face(FONT_SANS_SERIF)
        font.set_size(16)
        font.set_bold(1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_header_level(1)
        para.set_description(_("The style used for the title of the page."))
        default_style.add_paragraph_style('FGR-Title',para)

        font = FontStyle()
        font.set_type_face(FONT_SERIF)
        font.set_size(10)
        font.set_bold(0)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style('FGR-Normal',para)

        para = ParagraphStyle()
        font = FontStyle()
        font.set_type_face(FONT_SERIF)
        font.set_size(10)
        font.set_bold(0)
        para.set_font(font)
        para.set(lmargin=0.0)
        para.set_top_margin(0.0)
        para.set_bottom_margin(0.0)
        para.set_description(_('The basic style used for the note display.'))
        default_style.add_paragraph_style("FGR-Note",para)

        font = FontStyle()
        font.set_type_face(FONT_SANS_SERIF)
        font.set_size(10)
        font.set_bold(1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_description(_('The style used for the text related to the children.'))
        default_style.add_paragraph_style('FGR-ChildText',para)

        font = FontStyle()
        font.set_type_face(FONT_SANS_SERIF)
        font.set_size(12)
        font.set_bold(1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(3)
        para.set_description(_("The style used for the parent's name"))
        default_style.add_paragraph_style('FGR-ParentName',para)
        
        #Table Styles
        cell = TableCellStyle()
        cell.set_padding(0.2)
        cell.set_top_border(1)
        cell.set_bottom_border(1)
        cell.set_right_border(1)
        cell.set_left_border(1)
        default_style.add_cell_style('FGR-ParentHead',cell)

        cell = TableCellStyle()
        cell.set_padding(0.1)
        cell.set_bottom_border(1)
        cell.set_left_border(1)
        default_style.add_cell_style('FGR-TextContents',cell)

        cell = TableCellStyle()
        cell.set_padding(0.1)
        cell.set_bottom_border(0)
        cell.set_left_border(1)
        cell.set_padding(0.1)
        default_style.add_cell_style('FGR-TextChild1',cell)

        cell = TableCellStyle()
        cell.set_padding(0.1)
        cell.set_bottom_border(1)
        cell.set_left_border(1)
        cell.set_padding(0.1)
        default_style.add_cell_style('FGR-TextChild2',cell)

        cell = TableCellStyle()
        cell.set_padding(0.1)
        cell.set_bottom_border(1)
        cell.set_right_border(1)
        cell.set_left_border(1)
        default_style.add_cell_style('FGR-TextContentsEnd',cell)

        cell = TableCellStyle()
        cell.set_padding(0.2)
        cell.set_bottom_border(1)
        cell.set_right_border(1)
        cell.set_left_border(1)
        default_style.add_cell_style('FGR-ChildName',cell)

        table = TableStyle()
        table.set_width(100)
        table.set_columns(3)
        table.set_column_width(0,20)
        table.set_column_width(1,40)
        table.set_column_width(2,40)
        default_style.add_table_style('FGR-ParentTable',table)

        table = TableStyle()
        table.set_width(100)
        table.set_columns(4)
        table.set_column_width(0,7)
        table.set_column_width(1,18)
        table.set_column_width(2,35)
        table.set_column_width(3,40)
        default_style.add_table_style('FGR-ChildTable',table)

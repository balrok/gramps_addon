#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2009       Gary Burton
# Copyright (C) 2009-2010  Nick Hall
# Copyright (C) 2009       Benny Malengier
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
TreeModel for the GRAMPS Person tree.
"""

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
import cgi

#-------------------------------------------------------------------------
#
# GTK modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger(".")

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.lib import (Name, EventRef, EventType, EventRoleType,
                            FamilyRelType, ChildRefType, NoteType)
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.datehandler import format_time, get_date, get_date_valid
from .lru import LRU
from .flatbasemodel import FlatBaseModel
from .treebasemodel import TreeBaseModel
from gramps.gen.config import config
from gramps.gen.constfunc import cuni, UNITYPE
from gramps.gen.const import GRAMPS_LOCALE as glocale

#-------------------------------------------------------------------------
#
# COLUMN constants
#
#-------------------------------------------------------------------------
COLUMN_ID     = 1
COLUMN_GENDER = 2
COLUMN_NAME   = 3
COLUMN_DEATH  = 5
COLUMN_BIRTH  = 6
COLUMN_EVENT  = 7
COLUMN_FAMILY = 8
COLUMN_PARENT = 9
COLUMN_NOTES  = 16
COLUMN_CHANGE = 17
COLUMN_TAGS   = 18
COLUMN_PRIV   = 19

invalid_date_format = config.get('preferences.invalid-date-format')

#-------------------------------------------------------------------------
#
# PeopleBaseModel
#
#-------------------------------------------------------------------------
class PeopleBaseModel(object):
    """
    Basic Model interface to handle the PersonViews
    """
    _GENDER = [ _('female'), _('male'), _('unknown') ]

    # LRU cache size
    _CACHE_SIZE = 250

    def __init__(self, db):
        """
        Initialize the model building the initial data
        """
        self.db = db
        self.gen_cursor = db.get_person_cursor
        self.map = db.get_raw_person_data

        self.fmap = [
            self.column_name,
            self.column_id,
            self.column_gender,
            self.column_birth_day,
            self.column_birth_place,
            self.column_death_day,
            self.column_death_place,
            self.column_spouse,
            self.column_parents,
            self.column_marriages,
            self.column_children,
            self.column_todo,
            self.column_private,
            self.column_tags,
            self.column_change,
            self.column_tag_color,
            ]
        self.smap = [
            self.sort_name,
            self.column_id,
            self.column_gender,
            self.sort_birth_day,
            self.column_birth_place,
            self.sort_death_day,
            self.column_death_place,
            self.column_spouse,
            self.sort_parents,
            self.sort_marriages,
            self.sort_children,
            self.sort_todo,
            self.column_private,
            self.column_tags,
            self.sort_change,
            self.column_tag_color,
            ]

        #columns are accessed on every mouse over, so it is worthwhile to
        #cache columns visible in one screen to avoid expensive database 
        #lookup of derived values
        self.lru_name  = LRU(PeopleBaseModel._CACHE_SIZE)
        self.lru_spouse = LRU(PeopleBaseModel._CACHE_SIZE)
        self.lru_bdate = LRU(PeopleBaseModel._CACHE_SIZE)
        self.lru_ddate = LRU(PeopleBaseModel._CACHE_SIZE)

    def destroy(self):
        """
        Unset all elements that can prevent garbage collection
        """
        self.db = None
        self.gen_cursor = None
        self.map = None
        self.fmap = None
        self.smap = None
        self.clear_local_cache()

    def color_column(self):
        """
        Return the color column.
        """
        return 15

    def clear_local_cache(self, handle=None):
        """ Clear the LRU cache """
        if handle:
            try:
                del self.lru_name[handle]
            except KeyError:
                pass
            try:
                del self.lru_spouse[handle]
            except KeyError:
                pass
            try:
                del self.lru_bdate[handle]
            except KeyError:
                pass
            try:
                del self.lru_ddate[handle]
            except KeyError:
                pass
        else:
            self.lru_name.clear()
            self.lru_spouse.clear()
            self.lru_bdate.clear()
            self.lru_ddate.clear()

    def on_get_n_columns(self):
        """ Return the number of columns in the model """
        return len(self.fmap)+1

    def sort_name(self, data):
        name = name_displayer.raw_sorted_name(data[COLUMN_NAME])
        # internally we work with utf-8
        if not isinstance(name, UNITYPE):
            name = name.decode('utf-8')
        return name

    def column_name(self, data):
        handle = data[0]
        if handle in self.lru_name:
            name = self.lru_name[handle]
        else:
            name = name_displayer.raw_display_name(data[COLUMN_NAME])
            # internally we work with utf-8 for python 2.7
            if not isinstance(name, str):
                name = name.encode('utf-8')
            if not self._in_build:
                self.lru_name[handle] = name
        return name

    def column_spouse(self, data):
        handle = data[0]
        if handle in self.lru_spouse:
            value = self.lru_spouse[handle]
        else:
            value = self._get_spouse_data(data)
            if not self._in_build:
                self.lru_spouse[handle] = value
        return value

    def column_private(self, data):
        if data[COLUMN_PRIV]:
            return 'gramps-lock'
        else:
            # There is a problem returning None here.
            return ''
    
    def _get_spouse_data(self, data):
        spouses_names = ""
        for family_handle in data[COLUMN_FAMILY]:
            family = self.db.get_family_from_handle(family_handle)
            for spouse_id in [family.get_father_handle(),
                              family.get_mother_handle()]:
                if not spouse_id:
                    continue
                if spouse_id == data[0]:
                    continue
                spouse = self.db.get_person_from_handle(spouse_id)
                if spouses_names:
                    spouses_names += ", "
                spouses_names += name_displayer.display(spouse)
        return spouses_names

    def column_id(self, data):
        return data[COLUMN_ID]

    def sort_change(self,data):
        return "%012x" % data[COLUMN_CHANGE]

    def column_change(self, data):
        return format_time(data[COLUMN_CHANGE])

    def column_gender(self, data):
        return PeopleBaseModel._GENDER[data[COLUMN_GENDER]]

    def column_birth_day(self, data):
        handle = data[0]
        if handle in self.lru_bdate:
            value = self.lru_bdate[handle]
        else:
            value = self._get_birth_data(data, False)
            if not self._in_build:
                self.lru_bdate[handle] = value
        return value
        
    def sort_birth_day(self, data):
        handle = data[0]
        return self._get_birth_data(data, True)

    def _get_birth_data(self, data, sort_mode):
        index = data[COLUMN_BIRTH]
        if index != -1:
            try:
                local = data[COLUMN_EVENT][index]
                b = EventRef()
                b.unserialize(local)
                birth = self.db.get_event_from_handle(b.ref)
                if sort_mode:
                    retval = "%09d" % birth.get_date_object().get_sort_value()
                else:
                    date_str = get_date(birth)
                    if date_str != "":
                        retval = cgi.escape(date_str)
                if not get_date_valid(birth):
                    return invalid_date_format % retval
                else:
                    return retval
            except:
                return ''
        
        for event_ref in data[COLUMN_EVENT]:
            er = EventRef()
            er.unserialize(event_ref)
            event = self.db.get_event_from_handle(er.ref)
            etype = event.get_type()
            date_str = get_date(event)
            if (etype in [EventType.BAPTISM, EventType.CHRISTEN]
                and er.get_role() == EventRoleType.PRIMARY
                and date_str != ""):
                if sort_mode:
                    retval = "%09d" % event.get_date_object().get_sort_value()
                else:
                    retval = "<i>%s</i>" % cgi.escape(date_str)
                if not get_date_valid(event):
                    return invalid_date_format % retval
                else:
                    return retval
        
        return ""

    def column_death_day(self, data):
        handle = data[0]
        if handle in self.lru_ddate:
            value = self.lru_ddate[handle]
        else:
            value = self._get_death_data(data, False)
            if not self._in_build:
                self.lru_ddate[handle] = value
        return value
        
    def sort_death_day(self, data):
        handle = data[0]
        return self._get_death_data(data, True)

    def _get_death_data(self, data, sort_mode):
        index = data[COLUMN_DEATH]
        if index != -1:
            try:
                local = data[COLUMN_EVENT][index]
                ref = EventRef()
                ref.unserialize(local)
                event = self.db.get_event_from_handle(ref.ref)
                if sort_mode:
                    retval = "%09d" % event.get_date_object().get_sort_value()
                else:
                    date_str = get_date(event)
                    if date_str != "":
                        retval = cgi.escape(date_str)
                if not get_date_valid(event):
                    return invalid_date_format % retval
                else:
                    return retval
            except:
                return ''
        
        for event_ref in data[COLUMN_EVENT]:
            er = EventRef()
            er.unserialize(event_ref)
            event = self.db.get_event_from_handle(er.ref)
            etype = event.get_type()
            date_str = get_date(event)
            if (etype in [EventType.BURIAL,
                          EventType.CREMATION,
                          EventType.CAUSE_DEATH]
                and er.get_role() == EventRoleType.PRIMARY
                and date_str):
                if sort_mode:
                    retval = "%09d" % event.get_date_object().get_sort_value()
                else:
                    retval = "<i>%s</i>" % cgi.escape(date_str)
                if not get_date_valid(event):
                    return invalid_date_format % retval
                else:
                    return retval
        return ""

    def column_birth_place(self, data):
        index = data[COLUMN_BIRTH]
        if index != -1:
            try:
                local = data[COLUMN_EVENT][index]
                br = EventRef()
                br.unserialize(local)
                event = self.db.get_event_from_handle(br.ref)
                if event:
                    place_handle = event.get_place_handle()
                    if place_handle:
                        place = self.db.get_place_from_handle(place_handle)
                        place_title = place.get_title()
                        if place_title:
                            return cgi.escape(place_title)
            except:
                return ''
        
        for event_ref in data[COLUMN_EVENT]:
            er = EventRef()
            er.unserialize(event_ref)
            event = self.db.get_event_from_handle(er.ref)
            etype = event.get_type()
            if (etype in [EventType.BAPTISM, EventType.CHRISTEN] and
                er.get_role() == EventRoleType.PRIMARY):

                place_handle = event.get_place_handle()
                if place_handle:
                    place = self.db.get_place_from_handle(place_handle)
                    place_title = place.get_title()
                    if place_title:
                        return "<i>%s</i>" % cgi.escape(place_title)
        
        return ""

    def column_death_place(self, data):
        index = data[COLUMN_DEATH]
        if index != -1:
            try:
                local = data[COLUMN_EVENT][index]
                dr = EventRef()
                dr.unserialize(local)
                event = self.db.get_event_from_handle(dr.ref)
                if event:
                    place_handle = event.get_place_handle()
                    if place_handle:
                        place = self.db.get_place_from_handle(place_handle)
                        place_title = place.get_title()
                        if place_title:
                            return cgi.escape(place_title)
            except:
                return ''
        
        for event_ref in data[COLUMN_EVENT]:
            er = EventRef()
            er.unserialize(event_ref)
            event = self.db.get_event_from_handle(er.ref)
            etype = event.get_type()
            if (etype in [EventType.BURIAL, EventType.CREMATION,
                          EventType.CAUSE_DEATH]
                and er.get_role() == EventRoleType.PRIMARY):

                place_handle = event.get_place_handle()
                if place_handle:
                    place = self.db.get_place_from_handle(place_handle)
                    place_title = place.get_title()
                    if place_title != "":
                        return "<i>" + cgi.escape(place_title) + "</i>"
        return ""

    def _get_parents_data(self, data):
        parents = 0
        if data[COLUMN_PARENT]:
            family = self.db.get_family_from_handle(data[COLUMN_PARENT][0])
            if family.get_father_handle():
                parents += 1
            if family.get_mother_handle():
                parents += 1
        return parents

    def _get_marriages_data(self, data):
        marriages = 0
        for family_handle in data[COLUMN_FAMILY]:
            family = self.db.get_family_from_handle(family_handle)
            if int(family.get_relationship()) == FamilyRelType.MARRIED:
                marriages += 1
        return marriages

    def _get_children_data(self, data):
        children = 0
        for family_handle in data[COLUMN_FAMILY]:
            family = self.db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                if (child_ref.get_father_relation() == ChildRefType.BIRTH and 
                    child_ref.get_mother_relation() == ChildRefType.BIRTH):
                    children += 1
        return children

    def _get_todo_data(self, data):
        todo = 0
        for note_handle in data[COLUMN_NOTES]:
            note = self.db.get_note_from_handle(note_handle)
            if int(note.get_type()) == NoteType.TODO:
                todo += 1
        return todo

    def column_parents(self, data):
        return cuni(self._get_parents_data(data))

    def sort_parents(self, data):
        return '%06d' % self._get_parents_data(data)

    def column_marriages(self, data):
        return cuni(self._get_marriages_data(data))

    def sort_marriages(self, data):
        return '%06d' % self._get_marriages_data(data)

    def column_children(self, data):
        return cuni(self._get_children_data(data))

    def sort_children(self, data):
        return '%06d' % self._get_children_data(data)

    def column_todo(self, data):
        return cuni(self._get_todo_data(data))

    def sort_todo(self, data):
        return '%06d' % self._get_todo_data(data)

    def get_tag_name(self, tag_handle):
        """
        Return the tag name from the given tag handle.
        """
        return self.db.get_tag_from_handle(tag_handle).get_name()
        
    def column_tag_color(self, data):
        """
        Return the tag color.
        """
        tag_color = "#000000000000"
        tag_priority = None
        for handle in data[COLUMN_TAGS]:
            tag = self.db.get_tag_from_handle(handle)
            if tag:
                this_priority = tag.get_priority()
                if tag_priority is None or this_priority < tag_priority:
                    tag_color = tag.get_color()
                    tag_priority = this_priority
        return tag_color

    def column_tags(self, data):
        """
        Return the sorted list of tags.
        """
        tag_list = list(map(self.get_tag_name, data[COLUMN_TAGS]))
        return ', '.join(sorted(tag_list, key=glocale.sort_key))

class PersonListModel(PeopleBaseModel, FlatBaseModel):
    """
    Listed people model.
    """
    def __init__(self, db, scol=0, order=Gtk.SortType.ASCENDING, search=None,
                 skip=set(), sort_map=None):
        PeopleBaseModel.__init__(self, db)
        FlatBaseModel.__init__(self, db, search=search, skip=skip, scol=scol,
                               order=order, sort_map=sort_map)

    def clear_cache(self, handle=None):
        """ Clear the LRU cache """
        PeopleBaseModel.clear_local_cache(self, handle)

    def destroy(self):
        """
        Unset all elements that can prevent garbage collection
        """
        PeopleBaseModel.destroy(self)
        FlatBaseModel.destroy(self)

class PersonTreeModel(PeopleBaseModel, TreeBaseModel):
    """
    Hierarchical people model.
    """
    def __init__(self, db, scol=0, order=Gtk.SortType.ASCENDING, search=None,
                 skip=set(), sort_map=None):

        PeopleBaseModel.__init__(self, db)
        TreeBaseModel.__init__(self, db, search=search, skip=skip, scol=scol,
                               order=order, sort_map=sort_map)

    def destroy(self):
        """
        Unset all elements that can prevent garbage collection
        """
        PeopleBaseModel.destroy(self)
        self.number_items = None
        TreeBaseModel.destroy(self)

    def _set_base_data(self):
        """See TreeBaseModel, we also set some extra lru caches
        """
        self.number_items = self.db.get_number_of_people

    def clear_cache(self, handle=None):
        """ Clear the LRU cache 
        overwrite of base methods
        """
        TreeBaseModel.clear_cache(self, handle)
        PeopleBaseModel.clear_local_cache(self, handle)

    def get_tree_levels(self):
        """
        Return the headings of the levels in the hierarchy.
        """
        return [_('Group As'), _('Name')]

    def column_header(self, node):
        return node.name
    
    def add_row(self, handle, data):
        """
        Add nodes to the node map for a single person.

        handle      The handle of the gramps object.
        data        The object data.
        """
        ngn = name_displayer.name_grouping_data
        
        name_data = data[COLUMN_NAME]
        group_name = ngn(self.db, name_data)
        #if isinstance(group_name, UNITYPE):
        #    group_name = group_name.encode('utf-8')
        sort_key = self.sort_func(data)

        #if group_name not in self.group_list:
            #self.group_list.append(group_name)
            #self.add_node(None, group_name, group_name, None)
            
        # add as node: parent, child, sortkey, handle; parent and child are 
        # nodes in the treebasemodel, and will be used as iters
        self.add_node(group_name, handle, sort_key, handle)

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2011       Paul Franklin
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
A plugin to verify the data against user-adjusted tests.
This is the research tool, not the low-level data ingerity check.
"""

from __future__ import division, print_function
#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------

import os
import sys
if sys.version_info[0] < 3:
    import cPickle as pickle
else:
    import pickle
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
from gramps.gen.errors import WindowActiveError

#------------------------------------------------------------------------
#
# GNOME/GTK modules
#
#------------------------------------------------------------------------
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import URL_MANUAL_PAGE, VERSION_DIR
from gramps.gen.constfunc import UNITYPE
from gramps.gen.lib import (ChildRefType, EventRoleType, EventType,
                            FamilyRelType, NameType, Person)
from gramps.gen.lib.date import Today
from gramps.gui.editors import EditPerson, EditFamily
from gramps.gen.utils.db import family_name
from gramps.gui.display import display_help
from gramps.gui.managedwindow import ManagedWindow
from gramps.gen.updatecallback import UpdateCallback
from gramps.gui.plug import tool
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from gramps.gui.glade import Glade

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
WIKI_HELP_PAGE = '%s_-_Tools' % URL_MANUAL_PAGE
WIKI_HELP_SEC = _('manual|Verify_the_Data...')

#-------------------------------------------------------------------------
#
# temp storage and related functions
#
#-------------------------------------------------------------------------
_person_cache = {}
_family_cache = {}
_event_cache = {}
_today = Today().get_sort_value()

def find_event(db, handle):
    if handle in _event_cache:
        obj = _event_cache[handle]
    else:
        obj = db.get_event_from_handle(handle)
        _event_cache[handle] = obj
    return obj

def find_person(db, handle):
    if handle in _person_cache:
        obj = _person_cache[handle]
    else:
        obj = db.get_person_from_handle(handle)
        _person_cache[handle] = obj
    return obj

def find_family(db, handle):
    if handle in _family_cache:
        obj = _family_cache[handle]
    else:
        obj = db.get_family_from_handle(handle)
        _family_cache[handle] = obj
    return obj

def clear_cache():
    _person_cache.clear()
    _family_cache.clear()
    _event_cache.clear()   

#-------------------------------------------------------------------------
#
# helper functions
#
#-------------------------------------------------------------------------
def get_date_from_event_handle(db, event_handle, estimate=False):
    if not event_handle:
        return 0
    event =  find_event(db,event_handle)
    if event:
        date_obj = event.get_date_object()
        if not estimate and \
           (date_obj.get_day() == 0 or date_obj.get_month() == 0):
            return 0
        return date_obj.get_sort_value()
    else:
        return 0

def get_date_from_event_type(db, person, event_type, estimate=False):
    if not person:
        return 0
    for event_ref in person.get_event_ref_list():
        event = find_event(db,event_ref.ref)
        if event:
            if event_ref.get_role() != EventRoleType.PRIMARY and \
                event.get_type() == EventType.BURIAL:
                continue
            if event.get_type() == event_type:
                date_obj = event.get_date_object()
                if not estimate and \
                   (date_obj.get_day() == 0 or date_obj.get_month() == 0):
                    return 0
                return date_obj.get_sort_value()
    return 0

def get_bapt_date(db, person, estimate=False):
    return get_date_from_event_type(db, person, 
                                    EventType.BAPTISM, estimate)

def get_bury_date(db, person, estimate=False):
    # check role on burial event
    for event_ref in person.get_event_ref_list():
        event = find_event(db, event_ref.ref)
        if event and event.get_type() == EventType.BURIAL and \
        event_ref.get_role() == EventRoleType.PRIMARY:
            return get_date_from_event_type(db, person, 
                                            EventType.BURIAL, estimate)

def get_birth_date(db, person, estimate=False):
    if not person:
        return 0
    birth_ref = person.get_birth_ref()
    if not birth_ref:
        ret = 0
    else:
        ret = get_date_from_event_handle(db,birth_ref.ref,estimate)
    if estimate and (ret == 0):
        ret = get_bapt_date(db,person,estimate)
    return ret

def get_death_date(db, person, estimate=False):
    if not person:
        return 0
    death_ref = person.get_death_ref()
    if not death_ref:
        ret = 0
    else:
        ret = get_date_from_event_handle(db,death_ref.ref,estimate)
    if estimate and (ret == 0):
        ret = get_bury_date(db,person,estimate)
    return ret

def get_age_at_death(db, person, estimate):
    birth_date = get_birth_date(db,person,estimate)
    death_date = get_death_date(db,person,estimate)
    if (birth_date > 0) and (death_date > 0):
        return death_date - birth_date
    return 0

def get_father(db, family):
    if not family:
        return None
    father_handle = family.get_father_handle()
    if father_handle:
        return find_person(db,father_handle)
    return None

def get_mother(db, family):
    if not family:
        return None
    mother_handle = family.get_mother_handle()
    if mother_handle:
        return find_person(db, mother_handle)
    return None

def get_child_birth_dates(db, family, estimate):
    dates = []
    for child_ref in family.get_child_ref_list():
        child = find_person(db,child_ref.ref)
        child_birth_date = get_birth_date(db, child, estimate)
        if child_birth_date > 0:
            dates.append(child_birth_date)
    return dates

def get_n_children(db, person):
    n = 0
    for family_handle in person.get_family_handle_list():
        family = find_family(db,family_handle)
        if family:
            n += len(family.get_child_ref_list())
    return n

def get_marriage_date(db, family):
    if not family:
        return 0
    for event_ref in family.get_event_ref_list():
        event = find_event(db,event_ref.ref)
        if event.get_type() == EventType.MARRIAGE and \
        (event_ref.get_role() == EventRoleType.FAMILY or 
        event_ref.get_role() == EventRoleType.PRIMARY ):
            date_obj = event.get_date_object()
            return date_obj.get_sort_value()
    return 0

#-------------------------------------------------------------------------
#
# Actual tool
#
#-------------------------------------------------------------------------
class Verify(tool.Tool, ManagedWindow, UpdateCallback):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate
        self.label = _('Data Verify tool')
        self.vr = None
        tool.Tool.__init__(self, dbstate, options_class, name)
        ManagedWindow.__init__(self, uistate,[], self.__class__)
        if uistate:
            UpdateCallback.__init__(self, self.uistate.pulse_progressbar)

        self.dbstate = dbstate
        if uistate:
            self.init_gui()
        else:
            self.add_results = self.add_results_cli
            self.run_tool(cli=True)

    def add_results_cli(self, results):
        # print data for the user, no GUI
        (msg,gramps_id, name, the_type, rule_id, severity, handle) = results
        if severity == Rule.WARNING:
            # translators: needed for Arabic, ignore otherwise
            print(_("%(severity)s: %(msg)s, %(type)s: %(gid)s, %(name)s") %
                       {'severity':'W', 'msg':msg, 'type':the_type,
                        'gid':gramps_id, 'name':name})
        elif severity == Rule.ERROR:
            # translators: needed for Arabic, ignore otherwise
            print(_("%(severity)s: %(msg)s, %(type)s: %(gid)s, %(name)s") %
                       {'severity':'E', 'msg':msg, 'type':the_type,
                        'gid':gramps_id, 'name':name})
        else:
            # translators: needed for Arabic, ignore otherwise
            print(_("%(severity)s: %(msg)s, %(type)s: %(gid)s, %(name)s") %
                       {'severity':'S', 'msg':msg, 'type':the_type,
                        'gid':gramps_id, 'name':name})

    def init_gui(self):
        # Draw dialog and make it handle everything
        self.vr = None 
        self.top = Glade()
        self.top.connect_signals({
            "destroy_passed_object" : self.close,
            "on_help_clicked"       : self.on_help_clicked,
            "on_verify_ok_clicked"  : self.on_apply_clicked,
            "on_delete_event"       : self.close,
        })

        window = self.top.toplevel
        self.set_window(window,self.top.get_object('title'),self.label)

        for option in self.options.handler.options_dict:
            if option in ['estimate_age', 'invdate']:
                self.top.get_object(option).set_active(
                    self.options.handler.options_dict[option]
                    )
            else:
                self.top.get_object(option).set_value(
                    self.options.handler.options_dict[option]
                    )
        self.window.show()

    def build_menu_names(self, obj):
        return (_("Tool settings"),self.label)

    def on_help_clicked(self, obj):
        """Display the relevant portion of GRAMPS manual"""
        display_help(webpage=WIKI_HELP_PAGE, section=WIKI_HELP_SEC)

    def on_apply_clicked(self, obj):
        run_button = self.top.get_object('button4')
        close_button = self.top.get_object('button5')
        run_button.set_sensitive(False)
        close_button.set_sensitive(False)
        for option in self.options.handler.options_dict:
            if option in ['estimate_age', 'invdate']:
                self.options.handler.options_dict[option] = \
                self.top.get_object(option).get_active()
            else:
                self.options.handler.options_dict[option] = \
                    self.top.get_object(option).get_value_as_int()

        try:
            self.vr = VerifyResults(self.dbstate, self.uistate, self.track)
            self.add_results = self.vr.add_results
            self.vr.load_ignored(self.db.full_name)
        except WindowActiveError:
            pass

        self.uistate.set_busy_cursor(True)
        self.uistate.progress.show()
        self.window.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        try:
            self.vr.window.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        except AttributeError:
            pass

        self.run_tool(cli=False)

        self.uistate.progress.hide()
        self.uistate.set_busy_cursor(False)
        try:
            self.window.get_window().set_cursor(None)
            self.vr.window.get_window().set_cursor(None)
        except AttributeError:
            pass
        run_button.set_sensitive(True)
        close_button.set_sensitive(True)
        self.reset()
        
        # Save options
        self.options.handler.save_options()

    def run_tool(self,cli=False):

        person_handles = self.db.iter_person_handles()
        
        for option, value in \
          self.options.handler.options_dict.items():
            exec('%s = %s' % (option, value), globals())

        if self.vr:
            self.vr.real_model.clear()

        self.set_total(self.db.get_number_of_people() +
                       self.db.get_number_of_families())

        for person_handle in person_handles:
            person = find_person(self.db, person_handle)

            rule_list = [
                BirthAfterBapt(self.db, person),
                DeathBeforeBapt(self.db, person),
                BirthAfterBury(self.db, person),
                DeathAfterBury(self.db, person),
                BirthAfterDeath(self.db, person),
                BaptAfterBury(self.db, person),
                OldAge(self.db, person, oldage, estimate_age),
                OldAgeButNoDeath(self.db, person, oldage, estimate_age),
                UnknownGender(self.db, person),
                MultipleParents(self.db, person),
                MarriedOften(self.db, person, wedder),
                OldUnmarried(self.db, person, oldunm, estimate_age),
                TooManyChildren(self.db, person, mxchilddad, mxchildmom),
                Disconnected(self.db, person),
                InvalidBirthDate(self.db, person, invdate),
                InvalidDeathDate(self.db, person, invdate),
                ]

            for rule in rule_list:
                if rule.broken():
                    self.add_results(rule.report_itself())

            clear_cache()
            if not cli:
                self.update()

        # Family-based rules
        for family_handle in self.db.iter_family_handles():
            family = find_family(self.db,family_handle)

            rule_list = [
                SameSexFamily(self.db,family),
                FemaleHusband(self.db,family),
                MaleWife(self.db,family),
                SameSurnameFamily(self.db,family),
                LargeAgeGapFamily(self.db,family, hwdif,estimate_age),
                MarriageBeforeBirth(self.db,family,estimate_age),
                MarriageAfterDeath(self.db,family,estimate_age),
                EarlyMarriage(self.db,family,yngmar,estimate_age),
                LateMarriage(self.db,family, oldmar,estimate_age),
                OldParent(self.db,family, oldmom, olddad,estimate_age),
                YoungParent(self.db,family,yngmom,yngdad,estimate_age),
                UnbornParent(self.db,family,estimate_age),
                DeadParent(self.db,family,estimate_age),
                LargeChildrenSpan(self.db,family,cbspan,estimate_age),
                LargeChildrenAgeDiff(self.db,family,cspace,estimate_age),
                MarriedRelation(self.db,family),
                ]

            for rule in rule_list:
                if rule.broken():
                    self.add_results(rule.report_itself())
                
            clear_cache()
            if not cli:
                self.update()

#-------------------------------------------------------------------------
#
# Display the results
#
#-------------------------------------------------------------------------
class VerifyResults(ManagedWindow):
    IGNORE_COL     = 0
    WARNING_COL    = 1
    OBJ_ID_COL     = 2
    OBJ_NAME_COL   = 3
    OBJ_TYPE_COL   = 4
    RULE_ID_COL    = 5
    OBJ_HANDLE_COL = 6
    FG_COLOR_COL   = 7
    TRUE_COL       = 8
    SHOW_COL       = 9

    def __init__(self,dbstate,uistate,track):
        self.title = _('Data Verification Results')

        ManagedWindow.__init__(self,uistate,track,self.__class__)

        self.dbstate = dbstate
        self.top = Glade(toplevel="verify_result")
        window = self.top.toplevel
        self.set_window(window,self.top.get_object('title2'),self.title)
    
        self.top.connect_signals({
            "destroy_passed_object"  : self.close,
            "on_verify_ok_clicked"   : self.__dummy,
            "on_help_clicked"        : self.__dummy,
            })

        self.warn_tree = self.top.get_object('warn_tree')
        self.warn_tree.connect('button_press_event', self.double_click)

        self.selection = self.warn_tree.get_selection()
        
        self.hide_button = self.top.get_object('hide_button')
        self.hide_button.connect('toggled',self.hide_toggled)

        self.mark_button = self.top.get_object('mark_all')
        self.mark_button.connect('clicked',self.mark_clicked)

        self.unmark_button = self.top.get_object('unmark_all')
        self.unmark_button.connect('clicked',self.unmark_clicked)

        self.invert_button = self.top.get_object('invert_all')
        self.invert_button.connect('clicked',self.invert_clicked)

        self.real_model = Gtk.ListStore(GObject.TYPE_BOOLEAN, 
                                        GObject.TYPE_STRING, 
                                        GObject.TYPE_STRING, 
                                        GObject.TYPE_STRING, 
                                        GObject.TYPE_STRING, object, 
                                        GObject.TYPE_STRING, 
                                        GObject.TYPE_STRING,
                                        GObject.TYPE_BOOLEAN, 
                                        GObject.TYPE_BOOLEAN)
        self.filt_model = self.real_model.filter_new()
        self.filt_model.set_visible_column(VerifyResults.TRUE_COL)
        self.sort_model = self.filt_model.sort_new_with_model()
        self.warn_tree.set_model(self.sort_model)

        self.renderer = Gtk.CellRendererText()
        self.img_renderer = Gtk.CellRendererPixbuf()
        self.bool_renderer = Gtk.CellRendererToggle()
        self.bool_renderer.connect('toggled', self.selection_toggled)

        # Add ignore column
        ignore_column = Gtk.TreeViewColumn(_('Mark'), self.bool_renderer,
                                           active=VerifyResults.IGNORE_COL)
        ignore_column.set_sort_column_id(VerifyResults.IGNORE_COL)
        self.warn_tree.append_column(ignore_column)
        
        # Add image column
        img_column = Gtk.TreeViewColumn(None, self.img_renderer )
        img_column.set_cell_data_func(self.img_renderer,self.get_image)
        self.warn_tree.append_column(img_column)        

        # Add column with the warning text
        warn_column = Gtk.TreeViewColumn(_('Warning'), self.renderer,
                                         text=VerifyResults.WARNING_COL,
                                         foreground=VerifyResults.FG_COLOR_COL)
        warn_column.set_sort_column_id(VerifyResults.WARNING_COL)
        self.warn_tree.append_column(warn_column)

        # Add column with object gramps_id
        id_column = Gtk.TreeViewColumn(_('ID'), self.renderer,
                                       text=VerifyResults.OBJ_ID_COL,
                                       foreground=VerifyResults.FG_COLOR_COL)
        id_column.set_sort_column_id(VerifyResults.OBJ_ID_COL)
        self.warn_tree.append_column(id_column)

        # Add column with object name
        name_column = Gtk.TreeViewColumn(_('Name'), self.renderer,
                                         text=VerifyResults.OBJ_NAME_COL,
                                         foreground=VerifyResults.FG_COLOR_COL)
        name_column.set_sort_column_id(VerifyResults.OBJ_NAME_COL)
        self.warn_tree.append_column(name_column)
       
        self.window.show()
        self.window_shown = False

    def __dummy(self, obj):
        """dummy callback, needed because VerifyResults is in same glade file
        as Verify, so callbacks of Verify must be defined.
        """
        pass

    def load_ignored(self, db_filename):
        if sys.version_info[0] >= 3 and isinstance(db_filename, UNITYPE):
            db_filename = db_filename.encode('utf-8')
        md5sum = md5(db_filename)
        ## a new Gramps major version means recreating the .vfm file. 
        ## User can copy over old one, with name of new one, but no guarantee
        ## that will work.
        self.ignores_filename = os.path.join(
            VERSION_DIR, md5sum.hexdigest() + os.path.extsep + 'vfm')
        if not self._load_ignored(self.ignores_filename):
            self.ignores = {}

    def _load_ignored(self, filename):
        try:
            try:
                f = open(filename, 'rb')
            except IOError:
                return False
            self.ignores = pickle.load(f)
            f.close()
            return True
        except (IOError, EOFError):
            f.close()
            return False

    def save_ignored(self, new_ignores):
        self.ignores = new_ignores
        self._save_ignored(self.ignores_filename)

    def _save_ignored(self,filename):
        try:
            f = open(filename,'wb')
            pickle.dump(self.ignores, f, 1)
            f.close()
            return True
        except IOError:
            return False

    def get_marking(self, handle,rule_id):
        if handle in self.ignores:
            return (rule_id in self.ignores[handle])
        else:
            return False

    def get_new_marking(self):
        new_ignores = {}
        for row_num in range(len(self.real_model)):
            path = (row_num,)
            row = self.real_model[path]
            ignore = row[VerifyResults.IGNORE_COL]
            if ignore:
                handle = row[VerifyResults.OBJ_HANDLE_COL]
                rule_id = row[VerifyResults.RULE_ID_COL]
                if handle not in new_ignores:
                    new_ignores[handle] = set()
                new_ignores[handle].add(rule_id)
        return new_ignores

    def close(self, *obj):
        new_ignores = self.get_new_marking()
        self.save_ignored(new_ignores)

        ManagedWindow.close(self,*obj)

    def hide_toggled(self, button):
        if button.get_active():
            button.set_label(_("_Show all"))
            self.filt_model = self.real_model.filter_new()
            self.filt_model.set_visible_column(VerifyResults.SHOW_COL)
            self.sort_model = self.filt_model.sort_new_with_model()
            self.warn_tree.set_model(self.sort_model)
        else:
            self.filt_model = self.real_model.filter_new()
            self.filt_model.set_visible_column(VerifyResults.TRUE_COL)
            self.sort_model = self.filt_model.sort_new_with_model()
            self.warn_tree.set_model(self.sort_model)
            button.set_label(_("_Hide marked"))
        
    def selection_toggled(self, cell, path_string):
        sort_path = tuple(map(int, path_string.split(':')))
        filt_path = self.sort_model.convert_path_to_child_path(Gtk.TreePath(sort_path))
        real_path = self.filt_model.convert_path_to_child_path(filt_path)
        row = self.real_model[real_path]
        row[VerifyResults.IGNORE_COL] = not row[VerifyResults.IGNORE_COL]
        row[VerifyResults.SHOW_COL] = not row[VerifyResults.IGNORE_COL]
        self.real_model.row_changed(real_path,row.iter)

    def mark_clicked(self, mark_button):
        for row_num in range(len(self.real_model)):
            path = (row_num,)
            row = self.real_model[path]
            row[VerifyResults.IGNORE_COL] = True
            row[VerifyResults.SHOW_COL] = False
        self.filt_model.refilter()

    def unmark_clicked(self, unmark_button):
        for row_num in range(len(self.real_model)):
            path = (row_num,)
            row = self.real_model[path]
            row[VerifyResults.IGNORE_COL] = False
            row[VerifyResults.SHOW_COL] = True
        self.filt_model.refilter()

    def invert_clicked(self, invert_button):
        for row_num in range(len(self.real_model)):
            path = (row_num,)
            row = self.real_model[path]
            row[VerifyResults.IGNORE_COL] = not row[VerifyResults.IGNORE_COL]
            row[VerifyResults.SHOW_COL] = not row[VerifyResults.SHOW_COL]
        self.filt_model.refilter()

    def double_click(self, obj, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            (model, node) = self.selection.get_selected()
            if not node:
                return
            sort_path = self.sort_model.get_path(node)
            filt_path = self.sort_model.convert_path_to_child_path(sort_path)
            real_path = self.filt_model.convert_path_to_child_path(filt_path)
            row = self.real_model[real_path]
            the_type = row[VerifyResults.OBJ_TYPE_COL]
            handle = row[VerifyResults.OBJ_HANDLE_COL]
            if the_type == 'Person':
                try:
                    person = self.dbstate.db.get_person_from_handle(handle)
                    EditPerson(self.dbstate, self.uistate, [], person)
                except WindowActiveError:
                    pass
            elif the_type == 'Family':
                try:
                    family = self.dbstate.db.get_family_from_handle(handle)
                    EditFamily(self.dbstate, self.uistate, [], family)
                except WindowActiveError:
                    pass

    def get_image(self, column, cell, model, iter, user_data=None):
        the_type = model.get_value(iter, VerifyResults.OBJ_TYPE_COL)
        if the_type == 'Person':
            cell.set_property('stock-id', 'gramps-person' )
        elif  the_type == 'Family':
            cell.set_property('stock-id', 'gramps-family' )

    def add_results(self,results):
        (msg,gramps_id, name,the_type,rule_id,severity, handle) = results
        ignore = self.get_marking(handle,rule_id)
        if severity == Rule.ERROR:
            fg = 'red'
            #     fg = '#8b008b' # purple
            # elif severity == Rule.WARNING:
            #     fg = '#008b00' # green
        else:
            fg = None
        self.real_model.append(row=[ignore,msg,gramps_id, name,
                                    the_type,rule_id, handle,fg,
                                    True, not ignore])
        
        if not self.window_shown:
            self.window.show()
            self.window_shown = True

    def build_menu_names(self, obj):
        return (self.title,None)

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
class VerifyOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

        # Options specific for this report
        self.options_dict = {
            'oldage'       : 90,
            'hwdif'       : 30,
            'cspace'       : 8,
            'cbspan'       : 25,
            'yngmar'       : 17,
            'oldmar'       : 50,
            'oldmom'       : 48,
            'yngmom'       : 17,
            'yngdad'       : 18,
            'olddad'       : 65,
            'wedder'       : 3,
            'mxchildmom'   : 12,
            'mxchilddad'   : 15,
            'lngwdw'       : 30,
            'oldunm'       : 99,
            'estimate_age' : 0,
            'invdate'      : 1,
        }
        self.options_help = {
            'oldage'       : ("=num","Maximum age","Age in years"),
            'hwdif'       : ("=num","Maximum husband-wife age difference",
                              "Age difference in years"),
            'cspace'       : ("=num",
                              "Maximum number of years between children",
                              "Number of years"),
            'cbspan'       : ("=num",
                              "Maximum span of years for all children",
                              "Span in years"),
            'yngmar'       : ("=num","Minimum age to marry","Age in years"),
            'oldmar'       : ("=num","Maximum age to marry","Age in years"),
            'oldmom'       : ("=num","Maximum age to bear a child",
                              "Age in years"),
            'yngmom'       : ("=num","Minimum age to bear a child",
                              "Age in years"),
            'yngdad'       : ("=num","Minimum age to father a child",
                              "Age in years"),
            'olddad'       : ("=num","Maximum age to father a child",
                              "Age in years"),
            'wedder'       : ("=num","Maximum number of spouses for a person",
                              "Number of spouses"),
            'mxchildmom'   : ("=num","Maximum number of children for a woman",
                              "Number of children"),
            'mxchilddad'   : ("=num","Maximum  number of children for a man",
                              "Number of chidlren"),
            'lngwdw'       : ("=num","Maximum number of consecutive years "
                              "of widowhood before next marriage",
                              "Number of years"),
            'oldunm'       : ("=num","Maximum age for an unmarried person"
                              "Number of years"),
            'estimate_age' : ("=0/1","Whether to estimate missing or inexact dates",
                              ["Do not estimate","Estimate dates"],
                              True),
            'invdate'      : ("=0/1","Whether to check for invalid dates"
                              "Do not identify invalid dates", 
                              "Identify invalid dates", True),
        }

#-------------------------------------------------------------------------
#
# Base classes for different tests -- the rules
#
#-------------------------------------------------------------------------
class Rule(object):
    """
    Basic class for use in this tool.

    Other rules must inherit from this.
    """
    ID = 0
    TYPE = ''
    
    ERROR   = 1
    WARNING = 2

    SEVERITY = WARNING

    def __init__(self,db, obj):
        self.db = db
        self.obj = obj

    def broken(self):
        """
        Return boolean indicating whether this rule is violated.
        """
        return False

    def get_message(self):
        assert False, "Need to be overriden in the derived class"

    def get_name(self):
        assert False, "Need to be overriden in the derived class"

    def get_handle(self):
        return self.obj.handle

    def get_id(self):
        return self.obj.gramps_id

    def get_level(self):
        return Rule.WARNING

    def get_rule_id(self):
        params = self._get_params()
        return (self.ID,params)

    def _get_params(self):
        return tuple()

    def report_itself(self):
        handle = self.get_handle()
        the_type = self.TYPE
        rule_id = self.get_rule_id()
        severity = self.SEVERITY
        name = self.get_name()
        gramps_id = self.get_id()
        msg = self.get_message()
        return (msg,gramps_id, name,the_type,rule_id,severity, handle)

class PersonRule(Rule):
    """
    Person-based class.
    """
    TYPE = 'Person'
    def get_name(self):
        return self.obj.get_primary_name().get_name()

class FamilyRule(Rule):
    """
    Family-based class.
    """
    TYPE = 'Family'
    def get_name(self):
        return family_name(self.obj,self.db)

#-------------------------------------------------------------------------
#
# Actual rules for testing
#
#-------------------------------------------------------------------------
class BirthAfterBapt(PersonRule):
    ID = 1
    SEVERITY = Rule.ERROR
    def broken(self):
        birth_date = get_birth_date(self.db,self.obj)
        bapt_date = get_bapt_date(self.db,self.obj)
        birth_ok = birth_date > 0 if birth_date is not None else False
        bapt_ok = bapt_date > 0 if bapt_date is not None else False
        return (birth_ok and bapt_ok and birth_date > bapt_date)

    def get_message(self):
        return _("Baptism before birth")

class DeathBeforeBapt(PersonRule):
    ID = 2
    SEVERITY = Rule.ERROR
    def broken(self):
        death_date = get_death_date(self.db,self.obj)
        bapt_date = get_bapt_date(self.db,self.obj)
        bapt_ok = bapt_date > 0 if bapt_date is not None else False
        death_ok = death_date > 0 if death_date is not None else False
        return (death_ok and bapt_ok and bapt_date > death_date)

    def get_message(self):
        return _("Death before baptism")

class BirthAfterBury(PersonRule):
    ID = 3
    SEVERITY = Rule.ERROR
    def broken(self):
        birth_date = get_birth_date(self.db, self.obj)
        bury_date = get_bury_date(self.db, self.obj)
        birth_ok = birth_date > 0 if birth_date is not None else False
        bury_ok = bury_date > 0 if bury_date is not None else False
        return (birth_ok and bury_ok and birth_date > bury_date)

    def get_message(self):
        return _("Burial before birth")

class DeathAfterBury(PersonRule):
    ID = 4
    SEVERITY = Rule.ERROR
    def broken(self):
        death_date = get_death_date(self.db,self.obj)
        bury_date = get_bury_date(self.db,self.obj)
        death_ok = death_date > 0 if death_date is not None else False
        bury_ok = bury_date > 0 if bury_date is not None else False
        return (death_ok and bury_ok and death_date > bury_date)

    def get_message(self):
        return _("Burial before death")

class BirthAfterDeath(PersonRule):
    ID = 5
    SEVERITY = Rule.ERROR
    def broken(self):
        birth_date = get_birth_date(self.db,self.obj)
        death_date = get_death_date(self.db,self.obj)
        birth_ok = birth_date > 0 if birth_date is not None else False
        death_ok = death_date > 0 if death_date is not None else False
        return (birth_ok and death_ok and birth_date > death_date)

    def get_message(self):
        return _("Death before birth")

class BaptAfterBury(PersonRule):
    ID = 6
    SEVERITY = Rule.ERROR
    def broken(self):
        bapt_date = get_bapt_date(self.db,self.obj)
        bury_date = get_bury_date(self.db,self.obj)
        bapt_ok = bapt_date > 0 if bapt_date is not None else False
        bury_ok = bury_date > 0 if bury_date is not None else False
        return (bapt_ok and bury_ok and bapt_date > bury_date)

    def get_message(self):
        return _("Burial before baptism")

class OldAge(PersonRule):
    ID = 7
    SEVERITY = Rule.WARNING
    def __init__(self,db,person, old_age,est):
        PersonRule.__init__(self,db,person)
        self.old_age = old_age
        self.est = est

    def _get_params(self):
        return (self.old_age,self.est)

    def broken(self):
        age_at_death = get_age_at_death(self.db, self.obj, self.est)
        return (age_at_death/365 > self.old_age)

    def get_message(self):
        return _("Old age at death")

class UnknownGender(PersonRule):
    ID = 8
    SEVERITY = Rule.WARNING
    def broken(self):
        female = self.obj.get_gender() == Person.FEMALE
        male = self.obj.get_gender() == Person.MALE
        return not (male or female)

    def get_message(self):
        return _("Unknown gender")

class MultipleParents(PersonRule):
    ID = 9
    SEVERITY = Rule.WARNING
    def broken(self):
        n_parent_sets = len(self.obj.get_parent_family_handle_list())
        return (n_parent_sets>1)

    def get_message(self):
        return _("Multiple parents")

class MarriedOften(PersonRule):
    ID = 10
    SEVERITY = Rule.WARNING
    def __init__(self,db,person,wedder):
        PersonRule.__init__(self,db,person)
        self.wedder = wedder

    def _get_params(self):
        return (self.wedder,)

    def broken(self):
        n_spouses = len(self.obj.get_family_handle_list())
        return (n_spouses>self.wedder)

    def get_message(self):
        return _("Married often")

class OldUnmarried(PersonRule):
    ID = 11
    SEVERITY = Rule.WARNING
    def __init__(self,db,person, old_unm,est):
        PersonRule.__init__(self,db,person)
        self.old_unm = old_unm
        self.est = est

    def _get_params(self):
        return (self.old_unm,self.est)

    def broken(self):
        age_at_death = get_age_at_death(self.db,self.obj,self.est)
        n_spouses = len(self.obj.get_family_handle_list())
        return (age_at_death/365 > self.old_unm and n_spouses==0)

    def get_message(self):
        return _("Old and unmarried")

class TooManyChildren(PersonRule):
    ID = 12
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj,mx_child_dad,mx_child_mom):
        PersonRule.__init__(self,db, obj)
        self.mx_child_dad = mx_child_dad
        self.mx_child_mom = mx_child_mom

    def _get_params(self):
        return (self.mx_child_dad,self.mx_child_mom)

    def broken(self):
        n_child = get_n_children(self.db,self.obj)

        if (self.obj.get_gender == Person.MALE
               and n_child > self.mx_child_dad):
            return True

        if (self.obj.get_gender == Person.FEMALE
               and n_child > self.mx_child_mom):
            return True

        return False

    def get_message(self):
        return _("Too many children")

class SameSexFamily(FamilyRule):
    ID = 13
    SEVERITY = Rule.WARNING
    def broken(self):
        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        same_sex = (mother and father and
                    (mother.get_gender() == father.get_gender()))
        unknown_sex = (mother and
                       (mother.get_gender() == Person.UNKNOWN))
        return (same_sex and not unknown_sex)

    def get_message(self):
        return _("Same sex marriage")

class FemaleHusband(FamilyRule):
    ID = 14
    SEVERITY = Rule.WARNING
    def broken(self):
        father = get_father(self.db,self.obj)
        return (father and (father.get_gender() == Person.FEMALE))

    def get_message(self):
        return _("Female husband")

class MaleWife(FamilyRule):
    ID = 15
    SEVERITY = Rule.WARNING
    def broken(self):
        mother = get_mother(self.db,self.obj)
        return (mother and (mother.get_gender() == Person.MALE))

    def get_message(self):
        return _("Male wife")

class SameSurnameFamily(FamilyRule):
    ID = 16
    SEVERITY = Rule.WARNING
    def broken(self):
        mother = get_mother(self.db, self.obj)
        father = get_father(self.db, self.obj)
        _broken = False
        
        # Make sure both mother and father exist.
        if mother and father:
            mname = mother.get_primary_name()
            fname = father.get_primary_name()
            # Only compare birth names (not married names).
            if mname.get_type() == NameType.BIRTH and \
               fname.get_type() == NameType.BIRTH:
                # Empty names don't count.
                if len(mname.get_surname()) != 0 and \
                   len(fname.get_surname()) != 0:
                    # Finally, check if the names are the same.
                    if mname.get_surname() == fname.get_surname():
                        _broken = True

        return _broken

    def get_message(self):
        return _("Husband and wife with the same surname")

class LargeAgeGapFamily(FamilyRule):
    ID = 17
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj, hw_diff,est):
        FamilyRule.__init__(self,db, obj)
        self.hw_diff = hw_diff
        self.est = est

    def _get_params(self):
        return (self.hw_diff,self.est)

    def broken(self):
        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0
        large_diff = \
                   abs(father_birth_date-mother_birth_date)/365 > self.hw_diff
        return (mother_birth_date_ok and father_birth_date_ok and large_diff)

    def get_message(self):
        return _("Large age difference between spouses")

class MarriageBeforeBirth(FamilyRule):
    ID = 18
    SEVERITY = Rule.ERROR
    def __init__(self,db, obj,est):
        FamilyRule.__init__(self,db, obj)
        self.est = est

    def _get_params(self):
        return (self.est,)

    def broken(self):
        marr_date = get_marriage_date(self.db,self.obj)
        marr_date_ok = marr_date > 0

        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0

        father_broken = (father_birth_date_ok and marr_date_ok
                         and (father_birth_date > marr_date))
        mother_broken = (mother_birth_date_ok and marr_date_ok
                         and (mother_birth_date > marr_date))

        return (father_broken or mother_broken)

    def get_message(self):
        return _("Marriage before birth")

class MarriageAfterDeath(FamilyRule):
    ID = 19
    SEVERITY = Rule.ERROR
    def __init__(self,db, obj,est):
        FamilyRule.__init__(self,db, obj)
        self.est = est

    def _get_params(self):
        return (self.est,)

    def broken(self):
        marr_date = get_marriage_date(self.db,self.obj)
        marr_date_ok = marr_date > 0

        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_death_date = get_death_date(self.db,mother,self.est)
        father_death_date = get_death_date(self.db,father,self.est)
        mother_death_date_ok = mother_death_date > 0
        father_death_date_ok = father_death_date > 0

        father_broken = (father_death_date_ok and marr_date_ok
                         and (father_death_date < marr_date))
        mother_broken = (mother_death_date_ok and marr_date_ok
                         and (mother_death_date < marr_date))

        return (father_broken or mother_broken)

    def get_message(self):
        return _("Marriage after death")

class EarlyMarriage(FamilyRule):
    ID = 20
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj,yng_mar,est):
        FamilyRule.__init__(self,db, obj)
        self.yng_mar = yng_mar
        self.est = est

    def _get_params(self):
        return (self.yng_mar,self.est,)

    def broken(self):
        marr_date = get_marriage_date(self.db,self.obj)
        marr_date_ok = marr_date > 0

        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0

        father_broken = (father_birth_date_ok and marr_date_ok and
                         father_birth_date < marr_date and
                         ((marr_date - father_birth_date)/365 < self.yng_mar))
        mother_broken = (mother_birth_date_ok and marr_date_ok and
                         mother_birth_date < marr_date and
                         ((marr_date - mother_birth_date)/365 < self.yng_mar))

        return (father_broken or mother_broken)

    def get_message(self):
        return _("Early marriage")

class LateMarriage(FamilyRule):
    ID = 21
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj, old_mar,est):
        FamilyRule.__init__(self,db, obj)
        self.old_mar = old_mar
        self.est = est

    def _get_params(self):
        return (self.old_mar,self.est)

    def broken(self):
        marr_date = get_marriage_date(self.db,self.obj)
        marr_date_ok = marr_date > 0

        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0

        father_broken = (father_birth_date_ok and marr_date_ok and
                         ((marr_date - father_birth_date)/365 > self.old_mar))
        mother_broken = (mother_birth_date_ok and marr_date_ok and
                         ((marr_date - mother_birth_date)/365 > self.old_mar))

        return (father_broken or mother_broken)

    def get_message(self):
        return _("Late marriage")

## class MarriageBeforePrefiousMarrChild(PersonRule):
##     def broken(self):
##         marr_date = get_marriage_date(self.obj)
##         prev_marr_child_date = get_prev_marr_child_date(self.obj)
##         return (prev_marr_child_date>marr_date)

##     def get_message(self):
##         return _("Marriage before having a child from previous marriage")

## class LongWidowhood(FamilyRule):
##     def broken(self):
##         marr_date = get_marriage_date(self.obj)
##         prev_marr_spouse_death_date = get_prev_marr_spouse_death_date(self.obj)
##         birth_date = get_birth_date(self.obj)
##         return (marr_date-prev_marr_spouse_death_date>lngwdw)

##     def get_message(self):
##         return _("Long Windowhood")

class OldParent(FamilyRule):
    ID = 22
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj, old_mom, old_dad,est):
        FamilyRule.__init__(self,db, obj)
        self.old_mom = old_mom
        self.old_dad = old_dad
        self.est = est

    def _get_params(self):
        return (self.old_mom,self.old_dad,self.est)

    def broken(self):
        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0

        for child_ref in self.obj.get_child_ref_list():
            child = find_person(self.db,child_ref.ref)
            child_birth_date = get_birth_date(self.db,child,self.est)
            child_birth_date_ok = child_birth_date > 0
            if not child_birth_date_ok:
                continue
            father_broken = (father_birth_date_ok and
                ((child_birth_date - father_birth_date)/365 > self.old_dad))
            if father_broken:
                self.get_message = self.father_message
                return True

            mother_broken = (mother_birth_date_ok and
                ((child_birth_date - mother_birth_date)/365 > self.old_mom))
            if mother_broken:
                self.get_message = self.mother_message
                return True
        return False

    def father_message(self):
        return _("Old father")

    def mother_message(self):
        return _("Old mother")

class YoungParent(FamilyRule):
    ID = 23
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj,yng_mom,yng_dad,est):
        FamilyRule.__init__(self,db, obj)
        self.yng_dad = yng_dad
        self.yng_mom = yng_mom
        self.est = est

    def _get_params(self):
        return (self.yng_mom,self.yng_dad,self.est)

    def broken(self):
        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0

        for child_ref in self.obj.get_child_ref_list():
            child = find_person(self.db,child_ref.ref)
            child_birth_date = get_birth_date(self.db,child,self.est)
            child_birth_date_ok = child_birth_date > 0
            if not child_birth_date_ok:
                continue
            father_broken = (father_birth_date_ok and
                ((child_birth_date - father_birth_date)/365 < self.yng_dad))
            if father_broken:
                self.get_message = self.father_message
                return True

            mother_broken = (mother_birth_date_ok and
                ((child_birth_date - mother_birth_date)/365 < self.yng_mom))
            if mother_broken:
                self.get_message = self.mother_message
                return True
        return False

    def father_message(self):
        return _("Young father")

    def mother_message(self):
        return _("Young mother")

class UnbornParent(FamilyRule):
    ID = 24
    SEVERITY = Rule.ERROR
    def __init__(self,db, obj,est):
        FamilyRule.__init__(self,db, obj)
        self.est = est

    def _get_params(self):
        return (self.est,)

    def broken(self):
        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_birth_date = get_birth_date(self.db,mother,self.est)
        father_birth_date = get_birth_date(self.db,father,self.est)
        mother_birth_date_ok = mother_birth_date > 0
        father_birth_date_ok = father_birth_date > 0

        for child_ref in self.obj.get_child_ref_list():
            child = find_person(self.db,child_ref.ref)
            child_birth_date = get_birth_date(self.db,child,self.est)
            child_birth_date_ok = child_birth_date > 0
            if not child_birth_date_ok:
                continue
            father_broken = (father_birth_date_ok
                             and (father_birth_date > child_birth_date))
            if father_broken:
                self.get_message = self.father_message
                return True

            mother_broken = (mother_birth_date_ok
                             and (mother_birth_date > child_birth_date))
            if mother_broken:
                self.get_message = self.mother_message
                return True

    def father_message(self):
        return _("Unborn father")

    def mother_message(self):
        return _("Unborn mother")

class DeadParent(FamilyRule):
    ID = 25
    SEVERITY = Rule.ERROR
    def __init__(self,db, obj,est):
        FamilyRule.__init__(self,db, obj)
        self.est = est

    def _get_params(self):
        return (self.est,)

    def broken(self):
        mother = get_mother(self.db,self.obj)
        father = get_father(self.db,self.obj)
        mother_death_date = get_death_date(self.db,mother,self.est)
        father_death_date = get_death_date(self.db,father,self.est)
        mother_death_date_ok = mother_death_date > 0
        father_death_date_ok = father_death_date > 0

        for child_ref in self.obj.get_child_ref_list():
            child = find_person(self.db,child_ref.ref)
            child_birth_date = get_birth_date(self.db,child,self.est)
            child_birth_date_ok = child_birth_date > 0
            if not child_birth_date_ok:
                continue

            hasBirthRelToMother = child_ref.mrel == ChildRefType.BIRTH    
            hasBirthRelToFather = child_ref.frel == ChildRefType.BIRTH
            
            father_broken = (hasBirthRelToFather
                             and father_death_date_ok
                             and ((father_death_date + 294) < child_birth_date))
            if father_broken:
                self.get_message = self.father_message
                return True

            mother_broken = (hasBirthRelToMother
                             and mother_death_date_ok
                             and (mother_death_date < child_birth_date))
            if mother_broken:
                self.get_message = self.mother_message
                return True

    def father_message(self):
        return _("Dead father")

    def mother_message(self):
        return _("Dead mother")

class LargeChildrenSpan(FamilyRule):
    ID = 26
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj,cb_span,est):
        FamilyRule.__init__(self,db, obj)
        self.cb_span = cb_span
        self.est = est

    def _get_params(self):
        return (self.cb_span,self.est)

    def broken(self):
        child_birh_dates = get_child_birth_dates(self.db,self.obj,self.est)
        child_birh_dates.sort()
        
        return (child_birh_dates and ((child_birh_dates[-1]
                                       - child_birh_dates[0])/365
                                      > self.cb_span))

    def get_message(self):
        return _("Large year span for all children")

class LargeChildrenAgeDiff(FamilyRule):
    ID = 27
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj,c_space,est):
        FamilyRule.__init__(self,db, obj)
        self.c_space = c_space
        self.est = est

    def _get_params(self):
        return (self.c_space,self.est)

    def broken(self):
        child_birh_dates = get_child_birth_dates(self.db,self.obj,self.est)
        child_birh_dates_diff = [child_birh_dates[i+1] - child_birh_dates[i]
                                 for i in range(len(child_birh_dates)-1) ]
        
        return (child_birh_dates_diff and
                max(child_birh_dates_diff)/365 > self.c_space)

    def get_message(self):
        return _("Large age differences between children")

class Disconnected(PersonRule):
    ID = 28
    SEVERITY = Rule.WARNING
    def broken(self):
        return (len(self.obj.get_parent_family_handle_list())
                + len(self.obj.get_family_handle_list()) == 0)

    def get_message(self):
        return _("Disconnected individual")

class InvalidBirthDate(PersonRule):
    ID = 29
    SEVERITY = Rule.ERROR
    def __init__(self, db, person, invdate):
        PersonRule.__init__(self, db, person)
        self._invdate = invdate

    def broken(self):
        if not self._invdate: return False # should we check?
        # if so, let's get the birth date
        person = self.obj
        birth_ref = person.get_birth_ref()
        if birth_ref:
            birth_event = self.db.get_event_from_handle(birth_ref.ref)
            birth_date = birth_event.get_date_object()
            if birth_date and not birth_date.get_valid():
                return True
        return False

    def get_message(self):
        return _("Invalid birth date")

class InvalidDeathDate(PersonRule):
    ID = 30
    SEVERITY = Rule.ERROR
    def __init__(self, db, person, invdate):
        PersonRule.__init__(self, db, person)
        self._invdate = invdate

    def broken(self):
        if not self._invdate: return False # should we check?
        # if so, let's get the death date
        person = self.obj
        death_ref = person.get_death_ref()
        if death_ref:
            death_event = self.db.get_event_from_handle(death_ref.ref)
            death_date = death_event.get_date_object()
            if death_date and not death_date.get_valid():
                return True
        return False

    def get_message(self):
        return _("Invalid death date")
        
class MarriedRelation(FamilyRule):
    ID = 31
    SEVERITY = Rule.WARNING
    def __init__(self,db, obj):
        FamilyRule.__init__(self,db, obj)

    def broken(self):          
        marr_date = get_marriage_date(self.db,self.obj)
        marr_date_ok = marr_date > 0
        married = self.obj.get_relationship() == FamilyRelType.MARRIED
        if not married and marr_date_ok:
            return self.get_message

    def get_message(self):
        return _("Marriage date but not married")

class OldAgeButNoDeath(PersonRule):
    ID = 32
    SEVERITY = Rule.WARNING
    def __init__(self,db,person, old_age,est):
        PersonRule.__init__(self,db,person)
        self.old_age = old_age
        self.est = est

    def _get_params(self):
        return (self.old_age,self.est)

    def broken(self):
        birth_date = get_birth_date(self.db,self.obj,self.est)
        dead = get_death_date(self.db,self.obj,True) # if no death use burial
        if dead or not birth_date:
            return 0
        age = ( _today - birth_date ) / 365
        return ( age > self.old_age )

    def get_message(self):
        return _("Old age but no death")


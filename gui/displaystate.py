#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Nick Hall
# Copyright (C) 2011       Tim G L Lyons
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
# Standard python modules
#
#-------------------------------------------------------------------------
import os
import sys
if sys.version_info[0] < 3:
    from StringIO import StringIO
else:
    from io import StringIO
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger(".DisplayState")

#-------------------------------------------------------------------------
#
# GNOME python modules
#
#-------------------------------------------------------------------------
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GLib

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from gramps.gen.utils.callback import Callback
from .utils import process_pending_events
from .views.navigationview import NavigationView
from gramps.gen.config import config
from gramps.gen.display.name import displayer as name_displayer
from .managedwindow import GrampsWindowManager
from gramps.gen.relationship import get_relationship_calculator
from .glade import Glade
from gramps.gen.utils.db import navigation_label
from gramps.gen.constfunc import UNITYPE, cuni
from .widgets.progressdialog import ProgressMonitor, GtkProgressDialog

DISABLED = -1

#-------------------------------------------------------------------------
#
# History manager
#
#-------------------------------------------------------------------------
class History(Callback):
    """ History manages the objects of a certain type that have been viewed, 
        with ability to go back, or forward. 
        When accessing an object, it should be pushed on the History.
    """

    __signals__ = {
        'active-changed' : (UNITYPE, ), 
        'mru-changed' : (list, )
        }

    def __init__(self, dbstate, nav_type):
        Callback.__init__(self)
        self.dbstate = dbstate
        self.nav_type = nav_type
        self.clear()

        dbstate.connect('database-changed', self.connect_signals)
        self.signal_map = {}
        self.signal_map[nav_type.lower() + '-delete'] = self.handles_removed
        self.signal_map[nav_type.lower() + '-rebuild'] = self.history_changed

    def connect_signals(self, dbstate):
        """
        Connects database signals when the database has changed.
        """
        for sig in self.signal_map:
            dbstate.connect(sig, self.signal_map[sig])
            
    def clear(self):
        """
        Clears the history, resetting the values back to their defaults
        """
        self.history = []
        self.mru = []
        self.index = -1
        self.lock = False

        if self.dbstate.open and self.nav_type == 'Person':
            initial_person = self.dbstate.db.find_initial_person()
            if initial_person:
                self.push(initial_person.get_handle())

    def remove(self, handle, old_id=None):
        """
        Remove a handle from the history list
        """
        if old_id:
            del_id = old_id
        else:
            del_id = handle

        history_count = self.history.count(del_id)
        for c in range(history_count):
            self.history.remove(del_id)
            self.index -= 1
        
        mhc = self.mru.count(del_id)
        for c in range(mhc):
            self.mru.remove(del_id)
        self.emit('mru-changed', (self.mru, ))
        if self.history:
            newact = self.history[self.index]
            if not isinstance(newact, UNITYPE):
                newact = cuni(newact)
            self.emit('active-changed', (newact,))

    def push(self, handle):
        """
        Pushes the handle on the history stack
        """
        self.prune()
        if len(self.history) == 0 or handle != self.history[-1]:
            self.history.append(handle)
            if handle in self.mru:
                self.mru.remove(handle)
            self.mru.append(handle)
            self.emit('mru-changed', (self.mru, ))
            self.index += 1
        if self.history:
            newact = self.history[self.index]
            if not isinstance(newact, UNITYPE):
                newact = cuni(newact)
            self.emit('active-changed', (newact,))
 
    def forward(self, step=1):
        """
        Moves forward in the history list
        """
        self.index += step
        handle = self.history[self.index]
        if handle in self.mru:
            self.mru.remove(handle)
        self.mru.append(handle)
        self.emit('mru-changed', (self.mru, ))
        newact = self.history[self.index]
        if not isinstance(newact, UNITYPE):
            newact = cuni(newact)
        self.emit('active-changed', (newact,))
        return newact

    def back(self, step=1):
        """
        Moves backward in the history list
        """
        self.index -= step
        try:
            handle = self.history[self.index]
            if handle in self.mru:
                self.mru.remove(handle)
            self.mru.append(handle)
            self.emit('mru-changed', (self.mru, ))
            newact = self.history[self.index]
            if not isinstance(newact, UNITYPE):
                newact = cuni(newact)
            self.emit('active-changed', (newact,))
            return newact
        except IndexError:
            return ""
        
    def present(self):
        """
        return the person handle that is now active in the history
        """
        try :
            if self.history :
                return self.history[self.index]
            else:
                return ""
        except IndexError:
            return ""
        
    def at_end(self):
        """
        returns True if we are at the end of the history list
        """
        return self.index+1 == len(self.history)

    def at_front(self):
        """
        returns True if we are at the front of the history list
        """
        return self.index <= 0

    def prune(self):
        """
        Truncates the history list at the current object.
        """
        if not self.at_end():
            self.history = self.history[0:self.index+1]

    def handles_removed(self, handle_list):
        """
        Called in response to an object-delete signal.
        Removes a list of handles from the history.
        """
        for handle in handle_list:
            self.remove(handle)
            
    def history_changed(self):
        """
        Called in response to an object-rebuild signal.
        Objects in the history list may have been deleted.
        """
        self.clear()
        self.emit('mru-changed', (self.mru, ))
        
#-------------------------------------------------------------------------
#
# Recent Docs Menu
#
#-------------------------------------------------------------------------

_RCT_TOP = '<ui><menubar name="MenuBar"><menu action="FileMenu"><menu action="OpenRecent">'
_RCT_BTM = '</menu></menu></menubar></ui>'

from gramps.gen.recentfiles import RecentFiles
import os

class RecentDocsMenu(object):
    def __init__(self, uistate, state, fileopen):
        self.action_group = Gtk.ActionGroup(name='RecentFiles')
        self.active = DISABLED
        self.uistate = uistate
        self.uimanager = uistate.uimanager
        self.fileopen = fileopen
        self.state = state

    def load(self, item):
        filename = item.get_path()
        self.fileopen(filename)

    def build(self):
        buf = StringIO()
        buf.write(_RCT_TOP)
        gramps_rf = RecentFiles()

        count = 0
        
        if self.active != DISABLED:
            self.uimanager.remove_ui(self.active)
            self.uimanager.remove_action_group(self.action_group)
            self.action_group = Gtk.ActionGroup(name='RecentFiles')
            self.active = DISABLED
            
        actions = []
        rfiles = gramps_rf.gramps_recent_files
        rfiles.sort(key=lambda x: x.get_time(), reverse=True)

        new_menu = Gtk.Menu()

        for item in rfiles:
            try:
                title = item.get_name()
                filename = os.path.basename(item.get_path())
                action_id = "RecentMenu%d" % count
                buf.write('<menuitem action="%s"/>' % action_id)
                actions.append((action_id, None, title, None, None, 
                                make_callback(item, self.load)))
                mitem = Gtk.MenuItem(label=title, use_underline=False)
                mitem.connect('activate', make_callback(item, self.load))
                mitem.show()
                new_menu.append(mitem)
            except RuntimeError:
                _LOG.info("Ignoring the RecentItem %s (%s)" % (title, filename))
                pass    # ignore no longer existing files
            
            count += 1
        buf.write(_RCT_BTM)
        self.action_group.add_actions(actions)
        self.uimanager.insert_action_group(self.action_group, 1)
        self.active = self.uimanager.add_ui_from_string(buf.getvalue())
        self.uimanager.ensure_update()
        buf.close()

        if len(rfiles) > 0:
            new_menu.show()
            self.uistate.set_open_recent_menu(new_menu)

def make_callback(val, func):
    return lambda x: func(val)

from .logger import RotateHandler

class WarnHandler(RotateHandler):

    def __init__(self, capacity, button):
        RotateHandler.__init__(self, capacity)
        self.setLevel(logging.WARN)
        self.button = button
        button.on_clicked(self.display)
        self.timer = None
        self.last_line = '-1'

    def emit(self, record):
        if self.timer is None:
            #check every 3 minutes if warn button can disappear
            self.timer = GLib.timeout_add(3*60*1000, self._check_clear)
        RotateHandler.emit(self, record)
        self.button.show()

    def _check_clear(self):
        buffer = self.get_buffer()
        if len(buffer) > 0:
            new_last_line = self.get_buffer()[-1]
            if self.last_line == new_last_line:
                #buffer has not changed for 3 minutes, let's clear it:
                self._clear()
                return False
            else:
                self.last_line = new_last_line
                return True
        else:
            return False

    def _clear(self):
        self.button.hide()
        self.set_capacity(self._capacity)
        self.last_line = '-1'
        self.timer = None

    def display(self, obj):
        obj.hide()
        self.glade = Glade()
        top = self.glade.toplevel
        msg = self.glade.get_object('msg')
        buf = msg.get_buffer()
        for i in self.get_formatted_log():
            buf.insert_at_cursor(i + '\n')
        top.run()
        top.destroy()

class DisplayState(Callback):

    __signals__ = {
        'filters-changed' : (str, ), 
        'filter-name-changed' : (str, UNITYPE, UNITYPE), 
        'nameformat-changed' : None, 
        'grampletbar-close-changed' : None, 
        'update-available' : (list, ), 
        }
    
    #nav_type to message
    NAV2MES = {
        'Person': _("No active person"),
        'Family': _("No active family"),
        'Event': _("No active event"),
        'Place': _("No active place"),
        'Source': _("No active source"),
        'Citation': _("No active citation"),
        'Repository': _("No active repository"),
        'Media': _("No active media"),
        'Note': _("No active note"),
        }

    BUSY_CURSOR = Gdk.Cursor.new(Gdk.CursorType.WATCH)

    def __init__(self, window, status, uimanager, viewmanager=None):

        self.busy = False
        self.cursor = None
        self.viewmanager = viewmanager
        self.uimanager = uimanager
        self.progress_monitor = ProgressMonitor(GtkProgressDialog, ("", window))
        self.window = window
        Callback.__init__(self)
        self.status = status
        self.status_id = status.get_context_id('GRAMPS')
        self.progress = status.get_progress_bar()
        self.history_lookup = {}
        self.gwm = GrampsWindowManager(uimanager)
        self.widget = None
        self.disprel_old = ''
        self.disprel_defpers = None
        self.disprel_active = None
        self.set_relationship_class()

        formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
        warnbtn = status.get_warning_button()
        self.rhandler = WarnHandler(capacity=400, button=warnbtn)
        self.rhandler.setFormatter(formatter)
        self.rhandler.setLevel(logging.WARNING)
        self.log = logging.getLogger()
        self.log.addHandler(self.rhandler)
        # This call has been moved one level up, 
        # but this connection is still made!
        # self.dbstate.connect('database-changed', self.db_changed)

    def screen_width(self):
        """
        Return the width of the current screen.
        """
        return self.window.get_screen().get_width()

    def screen_height(self):
        """
        Return the height of the current screen.
        """
        return self.window.get_screen().get_height()

    def clear_history(self):
        """
        Clear all history objects.
        """
        for history in list(self.history_lookup.values()):
            history.clear()

    def get_history(self, nav_type, nav_group=0):
        """
        Return the history object for the given navigation type and group.
        """
        return self.history_lookup.get((nav_type, nav_group))

    def register(self, dbstate, nav_type, nav_group):
        """
        Create a history and navigation object for the specified
        navigation type and group, if they don't exist.
        """
        if (nav_type, nav_group) not in self.history_lookup:
            history = History(dbstate, nav_type)
            self.history_lookup[(nav_type, nav_group)] = history

    def get_active(self, nav_type, nav_group=0):
        """
        Return the handle for the active obejct specified by the given
        navigation type and group.
        """
        history = self.get_history(nav_type, nav_group)
        return history.present() if history else None

    def set_active(self, handle, nav_type, nav_group=0):
        """
        Set the active object for the specified navigation type and group to
        the given handle.
        """
        history = self.get_history(nav_type, nav_group)
        if history:
            history.push(handle)

    def set_sensitive(self, state):
        self.window.set_sensitive(state)
        
    def db_changed(self, db):
        db.connect('long-op-start', self.progress_monitor.add_op)
        self.clear_history()

    def set_relationship_class(self):
        """method that rebinds the relationship to the current rel calc
           Should be called after load or reload of plugins
        """
        self.relationship = get_relationship_calculator(reinit=True)

    def set_gendepth(self, value):
        """ Set the generations we search back for showing relationships
            on GRAMPS interface. Value must be integer > 0
            This method will be used by the preference editor when user changes
            the generations. 
        """
        self.relationship.set_depth(value)
        
    def display_relationship(self, dbstate, active_handle):
        """ Construct the relationship in order to show it in the statusbar
            This can be a time intensive calculation, so we only want to do
            it if persons are different than before.
            Eg: select a person, then double click, will result in calling
                three times to construct build the statusbar. We only want
                to obtain relationship once!
            This means the relationship part of statusbar only changes on
            change of row.
        """
        self.relationship.connect_db_signals(dbstate)
        default_person = dbstate.db.get_default_person()
        if default_person is None or active_handle is None:
            return ''
        if default_person.handle == self.disprel_defpers and \
                active_handle == self.disprel_active :
            return self.disprel_old

        active = dbstate.db.get_person_from_handle(active_handle)
        if active is None:
            # During merger this method can be called at a time when treemodel
            # and database are not in sync, resulting in active_handle != None,
            # but active == None; see bug 5290 for the details.
            return ''
        name = self.relationship.get_one_relationship(
                                            dbstate.db, default_person, active)
        #store present call data
        self.disprel_old = name
        self.disprel_defpers = default_person.handle
        self.disprel_active = active_handle
        if name:
            return name
        else:
            return ""

    def set_busy_cursor(self, value):
        if value == self.busy:
            return
        else:
            self.busy = value
        if value:
            self.cursor = self.window.get_window().get_cursor()
            self.window.get_window().set_cursor(self.BUSY_CURSOR)
        else:
            self.window.get_window().set_cursor(self.cursor)
        if self.window.get_window().is_visible():
            #avoid critical gdk error: 
            #Gdk-CRITICAL **: gdk_error_trap_pop_internal: assertion `trap != NULL' failed
            #only process events if window is actually visible
            process_pending_events()

    def set_open_widget(self, widget):
        self.widget = widget

    def set_open_recent_menu(self, menu):
        self.widget.set_menu(menu)

    def push_message(self, dbstate, text):
        self.status_text(text)
        GLib.timeout_add(5000, self.modify_statusbar, dbstate)

    def show_filter_results(self, dbstate, matched, total):
        #nav_type = self.viewmanager.active_page.navigation_type()
        #text = ((_("%(nav_type)s View") % {"nav_type": _(nav_type)}) + 
        text = (self.viewmanager.active_page.get_title() +
                (": %d/%d" % (matched, total)))
        self.status.set_filter(text)

    def clear_filter_results(self):
        self.status.clear_filter()

    def modify_statusbar(self, dbstate, active=None):
        view = self.viewmanager.active_page
        if not isinstance(view, NavigationView):
            return

        nav_type = view.navigation_type()
        active_handle = self.get_active(nav_type, view.navigation_group())
        
        self.status.pop(self.status_id)

        name, obj = navigation_label(dbstate.db, nav_type, active_handle)

        # Append relationship to default person if funtionality is enabled.
        if nav_type == 'Person' and active_handle \
                                and config.get('interface.statusbar') > 1:
            if active_handle != dbstate.db.get_default_handle():
                msg = self.display_relationship(dbstate, active_handle)
                if msg:
                    name = '%s (%s)' % (name, msg.strip())

        if not name:
            name = self.NAV2MES[nav_type]

        self.status.push(self.status_id, name)
        process_pending_events()

    def pulse_progressbar(self, value, text=None):
        self.progress.set_fraction(min(value/100.0, 1.0))
        if text:
            self.progress.set_text("%s: %d%%" % (text, value))
        else:
            self.progress.set_text("%d%%" % value)
        process_pending_events()

    def status_text(self, text):
        self.status.pop(self.status_id)
        self.status.push(self.status_id, text)
        process_pending_events()

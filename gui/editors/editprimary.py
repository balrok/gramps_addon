#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
#               2009       Gary Burton
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
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GTK modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from ..managedwindow import ManagedWindow
from gramps.gen.datehandler import displayer, parser
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.config import config
from ..utils import is_right_click
from ..display import display_help
from ..dialog import SaveDialog
from gramps.gen.lib import PrimaryObject
from ..dbguielement import DbGUIElement

class EditPrimary(ManagedWindow, DbGUIElement):

    QR_CATEGORY = -1
    
    def __init__(self, state, uistate, track, obj, get_from_handle, 
                 get_from_gramps_id, callback=None):
        """
        Create an edit window.  
        
        Associate a person with the window.
        
        """
        self.dp  = parser
        self.dd  = displayer
        self.name_displayer  = name_displayer
        self.obj = obj
        self.dbstate = state
        self.uistate = uistate
        self.db = state.db
        self.callback = callback
        self.ok_button = None
        self.get_from_handle = get_from_handle
        self.get_from_gramps_id = get_from_gramps_id
        self.contexteventbox = None
        self.__tabs = []

        ManagedWindow.__init__(self, uistate, track, obj)
        DbGUIElement.__init__(self, self.db)

        self._local_init()
        self._set_size()
        self._create_tabbed_pages()
        self._setup_fields()
        self._connect_signals()
        #if the database is changed, all info shown is invalid and the window
        # should close
        self.dbstate_connect_key = self.dbstate.connect('database-changed', 
                                   self._do_close)
        self.show()
        self._post_init()

    def _local_init(self):
        """
        Derived class should do any pre-window initalization in this task.
        """
        pass

    def _post_init(self):
        """
        Derived class should do any post-window initalization in this task.
        """
        pass

    def _setup_fields(self):
        pass

    def _create_tabbed_pages(self):
        pass

    def _connect_signals(self):
        pass

    def build_window_key(self, obj):
        if obj and obj.get_handle():
            return obj.get_handle()
        else:
            return id(self)

    def _setup_notebook_tabs(self, notebook):
        for child in notebook.get_children():
            label = notebook.get_tab_label(child)
            page_no = notebook.page_num(child)
            label.drag_dest_set(0, [], 0)
            label.connect('drag_motion',
                          self._switch_page_on_dnd,
                          notebook,
                          page_no)
            child.set_parent_notebook(notebook)

        notebook.connect('key-press-event', self.key_pressed, notebook)

    def key_pressed(self, obj, event, notebook):
        """
        Handles the key being pressed on the notebook, pass to key press of
        current page.
        """
        pag = notebook.get_current_page()
        if not pag == -1:
            notebook.get_nth_page(pag).key_pressed(obj, event)

    def _switch_page_on_dnd(self, widget, context, x, y, time, notebook, 
                            page_no):
        if notebook.get_current_page() != page_no:
            notebook.set_current_page(page_no)

    def _add_tab(self, notebook, page):
        self.__tabs.append(page)
        notebook.insert_page(page, page.get_tab_widget(), -1)
        page.label.set_use_underline(True)
        return page

    def _cleanup_on_exit(self):
        """Unset all things that can block garbage collection.
        Finalize rest
        """
        for tab in self.__tabs:
            if hasattr(tab, '_cleanup_on_exit'):
                tab._cleanup_on_exit()
        self.__tabs = None

    def object_is_empty(self):
        return self.obj.serialize()[1:] == self.empty_object().serialize()[1:]

    def define_ok_button(self, button, function):
        self.ok_button = button
        button.connect('clicked', function)
        button.set_sensitive(not self.db.readonly)

    def define_cancel_button(self, button):
        button.connect('clicked', self.close)

    def define_help_button(self, button, webpage='', section=''):
        button.connect('clicked', lambda x: display_help(webpage,
                                                               section))

    def _do_close(self, *obj):
        self._cleanup_db_connects()
        self.dbstate.disconnect(self.dbstate_connect_key)
        self._cleanup_connects()
        self._cleanup_on_exit()
        self.get_from_handle = None
        self.get_from_gramps_id = None
        ManagedWindow.close(self)
        self.dbstate = None
        self.uistate = None
        self.db = None

    def _cleanup_db_connects(self):
        """
        All connects that happened to signals of the db must be removed on 
        closed. This implies two things:
        1. The connects on the main view must be disconnected
        2. Connects done in subelements must be disconnected
        """
        #cleanup callbackmanager of this editor
        self._cleanup_callbacks()
        for tab in self.__tabs:
            if hasattr(tab, 'callman'):
                tab._cleanup_callbacks()
    
    def _cleanup_connects(self):
        """
        Connects to interface elements to things outside the element should be
        removed before destroying the interface
        """
        self._cleanup_local_connects()
        for tab in [tab for tab in self.__tabs if hasattr(tab, '_cleanup_local_connects')]:
            tab._cleanup_local_connects()

    def _cleanup_local_connects(self):
        """
        Connects to interface elements to things outside the element should be
        removed before destroying the interface. This methods cleans connects
        of the main interface, not of the displaytabs.
        """
        pass

    def check_for_close(self, handles):
        """
        Callback method for delete signals. 
        If there is a delete signal of the primary object we are editing, the
        editor (and all child windows spawned) should be closed
        """
        if self.obj.get_handle() in handles:
            self._do_close()

    def close(self, *obj):
        """If the data has changed, give the user a chance to cancel
        the close window"""
        if not config.get('interface.dont-ask') and self.data_has_changed():
            SaveDialog(
                _('Save Changes?'),
                _('If you close without saving, the changes you '
                  'have made will be lost'),
                self._do_close,
                self.save)
            return True
        else:
            self._do_close()
            return False

    def empty_object(self):
        #empty_object should be overridden in base class and will throw an 
        #exception if it is not because self.empty_object().serialize() is 
        #called and PrimaryObject does not implement serialize(). See
        #BaseObject.serialize()
        return PrimaryObject

    def data_has_changed(self):
        if self.db.readonly:
            return False
        elif self.obj.handle:
            orig = self.get_from_handle(self.obj.handle)
            if orig:
                cmp_obj = orig
            else:
                cmp_obj = self.empty_object()
            return cmp_obj.serialize()[1:] != self.obj.serialize()[1:]
        else:
            cmp_obj = self.empty_object()
            return cmp_obj.serialize()[1:] != self.obj.serialize()[1:]

    def save(self, *obj):
        """ Save changes and close. Inheriting classes must implement this
        """
        self.close()
        
    def set_contexteventbox(self, eventbox):
        """Set the contextbox that grabs button presses if not grabbed
            by overlying widgets.
        """
        self.contexteventbox = eventbox
        self.contexteventbox.connect('button-press-event',
                                self._contextmenu_button_press)
        
    def _contextmenu_button_press(self, obj, event) :
        """
        Button press event that is caught when a mousebutton has been
        pressed while on contexteventbox
        It opens a context menu with possible actions
        """
        if is_right_click(event):
            if self.obj.get_handle() == 0 :
                return False
            
            #build the possible popup menu
            self._build_popup_ui()
            #set or unset sensitivity in popup
            self._post_build_popup_ui()
                
            menu = self.popupmanager.get_widget('/Popup')
            if menu:
                menu.popup(None, None, None, None, event.button, event.time)
                return True
        return False

    def _build_popup_ui(self):
        """
        Create actions and ui of context menu
        """
        from ..plug.quick import create_quickreport_menu        
        
        self.popupmanager = Gtk.UIManager()
        #add custom actions
        (ui_top, action_groups) = self._top_contextmenu()
        for action in action_groups :
            self.popupmanager.insert_action_group(action, -1)
        #see which quick reports are available now:
        ui_qr = ''
        if self.QR_CATEGORY > -1 :
            (ui_qr, reportactions) = create_quickreport_menu(self.QR_CATEGORY,
                                    self.dbstate, self.uistate, 
                                    self.obj.get_handle())
            self.report_action = Gtk.ActionGroup(name="/PersonReport")
            self.report_action.add_actions(reportactions)
            self.report_action.set_visible(True)
            self.popupmanager.insert_action_group(self.report_action, -1)
        
        popupui = '''
        <ui>
          <popup name="Popup">''' + ui_top + '''
            <separator/>''' + ui_qr + '''
          </popup>
        </ui>'''
        
        self.popupmanager.add_ui_from_string(popupui)
        
    def _top_contextmenu(self):
        """
        Derived class can create a ui with menuitems and corresponding list of 
        actiongroups
        """
        return "", []
        
    def _post_build_popup_ui(self):
        """
        Derived class should do extra actions here on the menu
        """
        pass

    def _uses_duplicate_id(self):
        """
        Check whether a changed or added GRAMPS ID already exists in the DB.
        
        Return True if a duplicate GRAMPS ID has been detected.
        
        """
        original = self.get_from_handle(self.obj.get_handle())
        if original and original.get_gramps_id() == self.obj.get_gramps_id():
            return (False, 0)
        else:
            idval = self.obj.get_gramps_id()
            if self.get_from_gramps_id(idval):
                return (True, idval)
            return (False, 0)
            

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2001-2007  Donald N. Allingham
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
Provide the base class for GRAMPS' DataView classes
"""

#----------------------------------------------------------------
#
# python modules
#
#----------------------------------------------------------------
import sys
import logging
_LOG = logging.getLogger('.pageview')

#----------------------------------------------------------------
#
# gtk
#
#----------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import Gdk
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#----------------------------------------------------------------
#
# GRAMPS 
#
#----------------------------------------------------------------
from gramps.gen.errors import WindowActiveError
from ..dbguielement import DbGUIElement
from ..widgets.grampletbar import GrampletBar
from ..configure import ConfigureDialog
from gramps.gen.config import config

#------------------------------------------------------------------------------
#
# PageView
#
#------------------------------------------------------------------------------
class PageView(DbGUIElement):
    """
    The PageView class is the base class for all Data Views in GRAMPS.  All 
    Views should derive from this class. The ViewManager understands the public
    interface of this class
    
    The following attributes are available
    ..attribute:: active
      is the view active at the moment (visible in Gramps as the main view)
    ..attribute:: dirty
      bool, is the view current with the database or not. A dirty view triggers
      a rebuild when it becomes active
    ..attribute:: _dirty_on_change_inactive
      read/write bool by inheriting classes. 
      Views can behave two ways to signals:
      1. if the view is inactive, set it dirty, and rebuild the view when 
          it becomes active. In this case, this method returns True
      2. if the view is inactive, try to stay in sync with database. Only 
         rebuild or other large changes make view dirty
    ..attribute:: title
      title of the view
    ..attribute:: dbstate
      the dbstate
    ..attribute:: uistate
      the displaystate
    ..attribute:: category
      the category to which the view belongs. Views in the same category are
      placed behind the same button in the sidebar
    """

    CONFIGSETTINGS = []

    def __init__(self, title, pdata, dbstate, uistate):
        self.title = title
        self.pdata = pdata
        self.dbstate = dbstate
        self.uistate = uistate
        self.action_list = []
        self.action_toggle_list = []
        self.action_toolmenu_list = []
        self.action_toolmenu = {} #easy access to toolmenuaction and proxies
        self.action_group = None
        self.additional_action_groups = []
        self.additional_uis = []
        self.ui_def = '''<ui>
          <menubar name="MenuBar">
            <menu action="ViewMenu">
              <placeholder name="Bars">
                <menuitem action="Sidebar"/>
                <menuitem action="Bottombar"/>
              </placeholder>
            </menu>
          </menubar>
        </ui>'''
        self.dirty = True
        self.active = False
        self._dirty_on_change_inactive = True
        self.func_list = {}
        
        if isinstance(self.pdata.category, tuple):
            self.category, self.translated_category = self.pdata.category
        else:
            raise AttributeError("View category must be (name, translated-name)")
        self.ident = self.category + '_' + self.pdata.id

        self.dbstate.connect('no-database', self.disable_action_group)
        self.dbstate.connect('database-changed', self.enable_action_group)
        self.uistate.window.connect("key-press-event", self.key_press_handler)
        
        self.model = None
        self.selection = None
        self.handle_col = 0
        
        self._config = None
        self.init_config()

        self.filter_class = None
        self.top = None
        self.sidebar = None
        self.bottombar = None

        DbGUIElement.__init__(self, dbstate.db)

    def build_interface(self):
        """
        Builds the container widget for the interface.
        Returns a gtk container widget.
        """
        defaults = self.get_default_gramplets()
        self.sidebar = GrampletBar(self.dbstate, self.uistate, self,
                                   self.ident + "_sidebar",
                                   defaults[0])
        self.bottombar = GrampletBar(self.dbstate, self.uistate, self,
                                     self.ident + "_bottombar",
                                     defaults[1])
        hpane = Gtk.HPaned()
        vpane = Gtk.VPaned()
        hpane.pack1(vpane, resize=True, shrink=False)
        hpane.pack2(self.sidebar, resize=False, shrink=True)
        hpane.show()
        vpane.show()

        widget = self.build_widget()
        widget.show_all()
        vpane.pack1(widget, resize=True, shrink=False)
        vpane.pack2(self.bottombar, resize=False, shrink=True)

        self.sidebar_toggled(self.sidebar.get_property('visible'))

        return hpane

    def __sidebar_toggled(self, action):
        """
        Called when the sidebar is toggled.
        """
        active = action.get_active()
        if active:
            self.sidebar.show()
            self.sidebar_toggled(True)
        else:
            self.sidebar.hide()
            self.sidebar_toggled(False)

    def __bottombar_toggled(self, action):
        """
        Called when the bottombar is toggled.
        """
        active = action.get_active()
        if active:
            self.bottombar.show()
        else:
            self.bottombar.hide()

    def sidebar_toggled(self, active):
        """
        Called when the sidebar is toggled.
        """
        pass

    def get_default_gramplets(self):
        """
        Get the default gramplets for the Gramps sidebar and bottombar.
        Returns a 2-tuple.  The first element is a tuple of sidebar gramplets
        and the second element is a tuple of bottombar gramplets.

        Views should override this method to define default gramplets. 
        """
        return ((), ())

    def key_press_handler(self, widget, event):
        """
        A general keypress handler. Override if you want to handle
        special control characters, like control+c (copy) or control+v
        (paste).
        """
        return False

    def copy_to_clipboard(self, objclass, handles):
        """
        This code is called on Control+C in a navigation view. If the
        copy can be handled, it returns true, otherwise false.

        The code brings up the Clipboard (if already exists) or
        creates it. The copy is handled through the drag and drop
        system.
        """
        if sys.version_info[0] < 3:
            import cPickle as pickle
        else:
            import pickle
        from ..clipboard import ClipboardWindow, obj2target
        handled = False
        for handle in handles:
            if handle is None:
                continue
            clipboard = None
            for widget in self.uistate.gwm.window_tree:
                if isinstance(widget, ClipboardWindow):
                    clipboard = widget
            if clipboard is None:
                clipboard = ClipboardWindow(self.dbstate, self.uistate)
            # Construct a drop:
            drag_type = obj2target(objclass)
            if drag_type:
                class Selection(object):
                    def __init__(self, data):
                        self.data = data
                    def get_data(self):
                        return self.data
                class Context(object):
                    targets = [drag_type]
                    action = 1
                    def list_targets(self):
                        return Context.targets
                    def get_actions(self):
                        return Context.action
                # eg: ('person-link', 23767, '27365123671', 0)
                data = (drag_type.name(), id(self), handle, 0)
                clipboard.object_list.object_drag_data_received(
                    clipboard.object_list._widget, # widget
                    Context(),       # drag type and action
                    0, 0,            # x, y
                    Selection(pickle.dumps(data)), # pickled data
                    None,            # info (not used)
                    -1)  # time
                handled = True
        return handled

    def call_paste(self): 
        """
        This code is called on Control+V in a navigation view. If the
        copy can be handled, it returns true, otherwise false.

        The code creates the Clipboard if it does not already exist.
        """
        from ..clipboard import ClipboardWindow
        clipboard = None
        for widget in self.uistate.gwm.window_tree:
            if isinstance(widget, ClipboardWindow):
                clipboard = widget
        if clipboard is None:
            clipboard = ClipboardWindow(self.dbstate, self.uistate)
            return True
        return False

    def call_function(self, key):
        """
        Calls the function associated with the key value
        """
        self.func_list.get(key)()

    def post(self):
        """
        Called after a page is created.
        """
        pass
    
    def set_active(self):
        """
        Called with the PageView is set as active. If the page is "dirty",
        then we rebuild the data.
        """
        self.sidebar.set_active()
        self.bottombar.set_active()
        self.active = True
        if self.dirty:
            self.uistate.set_busy_cursor(True)
            self.build_tree()
            self.uistate.set_busy_cursor(False)
            
    def set_inactive(self):
        """
        Marks page as being inactive (not currently displayed)
        """
        self.sidebar.set_inactive()
        self.bottombar.set_inactive()
        self.active = False

    def build_tree(self):
        """
        Rebuilds the current display. This must be overridden by the derived
        class.
        """
        raise NotImplementedError
    
    def ui_definition(self):
        """
        returns the XML UI definition for the UIManager
        """
        return self.ui_def

    def additional_ui_definitions(self):
        """
        Return any additional interfaces for the UIManager that the view
        needs to define.
        """
        return self.additional_uis

    def disable_action_group(self):
        """
        Turns off the visibility of the View's action group, if defined
        """
        if self.action_group:
            self.action_group.set_visible(False)

    def enable_action_group(self, obj):
        """
        Turns on the visibility of the View's action group, if defined
        """
        if self.action_group:
            self.action_group.set_visible(True)

    def get_stock(self):
        """
        Return image associated with the view category, which is used for the 
        icon for the button.
        """
        return Gtk.STOCK_MISSING_IMAGE

    def get_viewtype_stock(self):
        """
        Return immage associated with the viewtype inside a view category, it
        will be used for the icon on the button to select view in the category
        """
        return Gtk.STOCK_MISSING_IMAGE

    def get_title(self):
        """
        Return the title of the view. This is used to define the text for the
        button, and for the tab label.
        """
        return self.title

    def get_category(self):
        """
        Return the category name of the view. This is used to define
        the text for the button, and for the tab label.
        """
        return self.category

    def get_translated_category(self):
        """
        Return the translated category name of the view. This is used
        to define the text for the button, and for the tab label.
        """
        return self.translated_category

    def get_display(self):
        """
        Builds the graphical display, returning the top level widget.
        """
        if not self.top:
            self.top = self.build_interface()
        return self.top

    def build_widget(self):
        """
        Builds the container widget for the main view pane. Must be overridden
        by the base class. Returns a gtk container widget.
        """
        raise NotImplementedError

    def define_actions(self):
        """
        Defines the UIManager actions. Called by the ViewManager to set up the
        View. The user typically defines self.action_list and 
        self.action_toggle_list in this function. 
        """
        self._add_toggle_action('Sidebar', None, _('_Sidebar'), 
             "<shift><PRIMARY>R", None, self.__sidebar_toggled,
             self.sidebar.get_property('visible'))
        self._add_toggle_action('Bottombar', None, _('_Bottombar'), 
             "<shift><PRIMARY>B", None, self.__bottombar_toggled,
             self.bottombar.get_property('visible'))

    def __build_action_group(self):
        """
        Create an UIManager ActionGroup from the values in self.action_list
        and self.action_toggle_list. The user should define these in 
        self.define_actions
        """
        self.action_group = Gtk.ActionGroup(name=self.title)
        if len(self.action_list) > 0:
            self.action_group.add_actions(self.action_list)
        if len(self.action_toggle_list) > 0:
            self.action_group.add_toggle_actions(self.action_toggle_list)

    def _add_action(self, name, stock_icon, label, accel=None, tip=None, 
                   callback=None):
        """
        Add an action to the action list for the current view. 
        """
        self.action_list.append((name, stock_icon, label, accel, tip, 
                                 callback))

    def _add_toggle_action(self, name, stock_icon, label, accel=None, 
                           tip=None, callback=None, value=False):
        """
        Add a toggle action to the action list for the current view. 
        """
        self.action_toggle_list.append((name, stock_icon, label, accel, 
                                        tip, callback, value))
    
    def _add_toolmenu_action(self, name, label, tooltip, callback, 
                             arrowtooltip):
        """
        Add a menu action to the action list for the current view. 
        """
        self.action_toolmenu_list.append((name, label, tooltip, callback,
                                          arrowtooltip))

    def get_actions(self):
        """
        Return the actions that should be used for the view. This includes the
        standard action group (which handles the main toolbar), along with 
        additional action groups.

        If the action group is not defined, we build it the first time. This 
        allows us to delay the intialization until it is really needed.

        The ViewManager uses this function to extract the actions to install 
        into the UIManager.
        """
        if not self.action_group:
            self.__build_action_group()
        return [self.action_group] + self.additional_action_groups

    def _add_action_group(self, group):
        """
        Allows additional action groups to be added to the view. 
        """
        self.additional_action_groups.append(group)

    def change_page(self):
        """
        Called when the page changes.
        """
        self.uistate.clear_filter_results()

    def edit(self, obj):
        """
        Template function to allow the editing of the selected object
        """
        raise NotImplementedError

    def remove(self, handle):
        """
        Template function to allow the removal of an object by its handle
        """
        raise NotImplementedError

    def remove_object_from_handle(self, handle):
        """
        Template function to allow the removal of an object by its handle
        """
        raise NotImplementedError

    def add(self, obj):
        """
        Template function to allow the adding of a new object
        """
        raise NotImplementedError
    
    def _key_press(self, obj, event):
        """
        Define the action for a key press event
        """
        # TODO: This is never used? (replaced in ListView)
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.edit(obj)
            return True
        return False

    def on_delete(self):
        """
        Method called on shutdown. Data views should put code here
        that should be called when quiting the main application.
        """
        self.sidebar.on_delete()
        self.bottombar.on_delete()
        self._config.save()

    def init_config(self):
        """
        If you need a view with a config, then call this method in the 
        build_widget or __init__ method. It will set up a config file for the 
        view, and use CONFIGSETTINGS to set the config defaults. 
        The config is later accessbile via self._config
        So you can do 
        self._config.get("section.variable1")
        self._config.set("section.variable1", value)
        self._config.save()
        
        CONFIGSETTINGS should be a list with tuples like 
        ("section.variable1", value)
        """
        if self._config:
            return
        self._config = config.register_manager(self.ident, 
                                               use_config_path=True)
        for section, value in self.CONFIGSETTINGS:
            self._config.register(section, value)
        self._config.init()
        self.config_connect()

    def config_connect(self):
        """
        Overwrite this method to set connects to the config file to monitor
        changes. This method will be called after the ini file is initialized
        Eg:
            self.config.connect("section.option", self.callback)
        """
        pass

    def config_callback(self, callback):
        """
        Convenience wrappen to create a callback for a config setting
        :param callback: a callback function to call.
        """
        return lambda arg1, arg2, arg3, arg4: callback()

    def can_configure(self):
        """
        Inheriting classes should set if the view has a configure window or not
        :return: bool
        """
        return False

    def _get_configure_page_funcs(self):
        """
        Return a list of functions that create gtk elements to use in the 
        notebook pages of the Configure view
        
        :return: list of functions
        """
        raise NotImplementedError

    def configure(self):
        """
        Open the configure dialog for the view.
        """
        title = _("Configure %(cat)s - %(view)s") % \
                        {'cat': self.get_translated_category(), 
                         'view': self.get_title()}

        if self.can_configure():
            config_funcs = self._get_configure_page_funcs()
        else:
            config_funcs = []
        if self.sidebar:
            config_funcs += self.sidebar.get_config_funcs()
        if self.bottombar:
            config_funcs += self.bottombar.get_config_funcs()

        try:
            ViewConfigureDialog(self.uistate, self.dbstate, 
                            config_funcs,
                            self, self._config, dialogtitle=title,
                            ident=_("%(cat)s - %(view)s") % 
                                    {'cat': self.get_translated_category(),
                                     'view': self.get_title()})
        except WindowActiveError:
            return

class ViewConfigureDialog(ConfigureDialog):
    """
    All views can have their own configuration dialog
    """
    def __init__(self, uistate, dbstate, configure_page_funcs, configobj,
                 configmanager,
                 dialogtitle=_("Preferences"), on_close=None, ident=''):
        self.ident = ident
        ConfigureDialog.__init__(self, uistate, dbstate, configure_page_funcs,
                                 configobj, configmanager,
                                 dialogtitle=dialogtitle, on_close=on_close)
        
    def build_menu_names(self, obj):
        return (_('Configure %s View') % self.ident, None)

class DummyPage(PageView):
    """
    A Dummy page for testing or errors
    """
    def __init__(self, title, pdata, dbstate, uistate, msg1="", msg2=""):
        self.msg = msg1
        self.msg2 = msg2
        PageView.__init__(self, title, pdata, dbstate, uistate)
    
    def build_widget(self):
        box = Gtk.VBox(homogeneous=False, spacing=1)
        #top widget at the top
        box.pack_start(Gtk.Label(label=_('View %(name)s: %(msg)s') % {
                'name': self.title,
                'msg': self.msg}), False, False, 0)
        tv = Gtk.TextView()
        tb = tv.get_buffer()
        tb.insert_at_cursor(self.msg2)
        box.pack_start(tv, False, False, 0)
        return box

    def build_tree(self):
        pass

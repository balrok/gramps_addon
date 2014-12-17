#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2010 Nick Hall
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
# $Id: navigator.py 20492 2012-10-02 21:08:19Z nick-h $

"""
A module that provides pluggable sidebars.  These provide an interface to
manage pages in the main Gramps window.
"""
#-------------------------------------------------------------------------
#
# GNOME modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import Gdk

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.plug import (START, END)
from .pluginmanager import GuiPluginManager

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
UICATEGORY = '''<ui>
<menubar name="MenuBar">
  <menu action="ViewMenu">
    <placeholder name="ViewsInCategory">%s
    </placeholder>
  </menu>
</menubar>
</ui>
'''

CATEGORY_ICON = {
    'Dashboard': 'gramps-gramplet',
    'People': 'gramps-person',
    'Relationships': 'gramps-relation',
    'Families': 'gramps-family',
    'Events': 'gramps-event',
    'Ancestry': 'gramps-pedigree',
    'Places': 'gramps-place',
    'Geography': 'gramps-geo',
    'Sources': 'gramps-source',
    'Repositories': 'gramps-repository',
    'Media': 'gramps-media',
    'Notes': 'gramps-notes',
    'Citations': 'gramps-citation',
}

#-------------------------------------------------------------------------
#
# Navigator class
#
#-------------------------------------------------------------------------
class Navigator(object):
    """
    A class which defines the graphical representation of the Gramps navigator.
    """
    def __init__(self, viewmanager):

        self.viewmanager = viewmanager
        self.pages = []
        self.active_cat = None
        self.active_view = None

        self.ui_category = {}
        self.view_toggle_actions = {}
        self.cat_view_group = None
        self.merge_ids = []

        self.top = Gtk.VBox()
        
        frame = Gtk.Frame()
        hbox = Gtk.HBox()
        hbox.show()
        frame.add(hbox)
        frame.show()
        
        self.select_button = Gtk.ToggleButton()
        self.select_button.set_relief(Gtk.ReliefStyle.NONE)
        select_hbox = Gtk.HBox()
        self.title_label = Gtk.Label(label='')
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.DOWN, 
                                    shadow_type=Gtk.ShadowType.NONE)
        select_hbox.pack_start(self.title_label, False, True, 0)
        select_hbox.pack_end(arrow, False, True, 0)
        self.select_button.add(select_hbox)

        self.select_button.connect('button_press_event',
                                   self.__menu_button_pressed)

        #close_button = Gtk.Button()
        #img = Gtk.Image.new_from_stock(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU)
        #close_button.set_image(img)
        #close_button.set_relief(Gtk.ReliefStyle.NONE)
        #close_button.connect('clicked', self.cb_close_clicked)
        hbox.pack_start(self.select_button, False, True, 0)
        #hbox.pack_end(close_button, False, True, 0)

        self.top.pack_end(frame, False, True, 0)        

        self.menu = Gtk.Menu()
        self.menu.show()
        self.menu.connect('deactivate', cb_menu_deactivate, self.select_button)

        self.notebook = Gtk.Notebook()
        self.notebook.show()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(False)
        self.notebook.connect('switch_page', self.cb_switch_page)
        self.top.show()
        self.top.pack_start(self.notebook, True, True, 0)
        
    def load_plugins(self, dbstate, uistate):
        """
        Load the sidebar plugins.
        """
        plugman = GuiPluginManager.get_instance()

        categories = []
        views = {}
        for cat_num, cat_views in enumerate(self.viewmanager.get_views()):
            uimenuitems = ''
            self.view_toggle_actions[cat_num] = []
            for view_num, page in enumerate(cat_views):

                if view_num == 0:
                    views[cat_num] = []
                    cat_name = page[0].category[1]
                    cat_icon = CATEGORY_ICON.get(page[0].category[0])
                    if cat_icon is None:
                        cat_icon = 'gramps-view'
                    categories.append([cat_num, cat_name, cat_icon])

                pageid = 'page_%i_%i' % (cat_num, view_num)
                uimenuitems += '\n<menuitem action="%s"/>' % pageid
                # id, stock, button text, UI, tooltip, page
                if view_num < 9:
                    modifier = "<PRIMARY><ALT>%d" % ((view_num % 9) + 1)
                else:
                    modifier = ""

                stock_icon = page[0].stock_icon
                if stock_icon is None:
                    stock_icon = cat_icon
                self.view_toggle_actions[cat_num].append((pageid, 
                            stock_icon,
                            page[0].name, modifier, page[0].name, view_num))

                views[cat_num].append((view_num, page[0].name, stock_icon))

            if len(cat_views) > 1:
                #allow for switching views in a category
                self.ui_category[cat_num] = UICATEGORY % uimenuitems

        for pdata in plugman.get_reg_sidebars():
            module = plugman.load_plugin(pdata)
            if not module:
                print("Error loading sidebar '%s': skipping content"
                      % pdata.name)
                continue

            sidebar_class = getattr(module, pdata.sidebarclass)
            sidebar_page = sidebar_class(dbstate, uistate, categories, views)
            self.add(pdata.menu_label, sidebar_page, pdata.order)

    def get_top(self):
        """
        Return the top container widget for the GUI.
        """
        return self.top
        
    def add(self, title, sidebar, order):
        """
        Add a page to the sidebar for a plugin.
        """
        self.pages.append((title, sidebar))
        index = self.notebook.append_page(sidebar.get_top(), Gtk.Label(label=title))

        menu_item = Gtk.MenuItem(label=title)
        if order == START:
            self.menu.prepend(menu_item)
            self.notebook.set_current_page(index)
        else:
            self.menu.append(menu_item)
        menu_item.connect('activate', self.cb_menu_activate, index)
        menu_item.show()

        if self.notebook.get_n_pages() == 2:
            self.select_button.show_all()

    def view_changed(self, cat_num, view_num):
        """
        Called when a Gramps view is changed.
        """
        self.active_cat = cat_num
        self.active_view = view_num

        # Add buttons to the menu for the different view in the category
        uimanager = self.viewmanager.uimanager
        if self.cat_view_group:
            if self.cat_view_group in uimanager.get_action_groups(): 
                uimanager.remove_action_group(self.cat_view_group)
                
            list(map(uimanager.remove_ui, self.merge_ids))

        if cat_num in self.ui_category:
            self.cat_view_group = Gtk.ActionGroup(name='viewmenu')
            self.cat_view_group.add_radio_actions(
                    self.view_toggle_actions[cat_num], value=view_num,
                    on_change=self.cb_view_clicked, user_data=cat_num)
            self.cat_view_group.set_sensitive(True)
            uimanager.insert_action_group(self.cat_view_group, 1)
            mergeid = uimanager.add_ui_from_string(self.ui_category[cat_num])
            self.merge_ids.append(mergeid)

        # Call the view_changed method for the active sidebar
        try:
            sidebar = self.pages[self.notebook.get_current_page()][1]
        except IndexError:
            return
        sidebar.view_changed(cat_num, view_num)

    def cb_view_clicked(self, radioaction, current, cat_num):
        """
        Called when a view is selected from the menu.
        """
        view_num = radioaction.get_current_value()
        self.viewmanager.goto_page(cat_num, view_num)

    def __menu_button_pressed(self, button, event):
        """
        Called when the button to select a sidebar page is pressed.
        """
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            button.grab_focus()
            button.set_active(True)

            self.menu.popup(None, None, cb_menu_position, button, event.button,
                            event.time)

    def cb_menu_activate(self, menu, index):
        """
        Called when an item in the popup menu is selected.
        """        
        self.notebook.set_current_page(index)

    def cb_switch_page(self, notebook, unused, index):
        """
        Called when the user has switched to a new sidebar plugin page.
        """
        old_page = notebook.get_current_page()
        if old_page != -1:
            self.pages[old_page][1].inactive()
        self.pages[index][1].active(self.active_cat, self.active_view)
        if self.active_view is not None:
            self.pages[index][1].view_changed(self.active_cat, self.active_view)
        self.title_label.set_text(self.pages[index][0])

    def cb_close_clicked(self, button):
        """
        Called when the sidebar is closed.
        """
        uimanager = self.viewmanager.uimanager
        uimanager.get_action('/MenuBar/ViewMenu/Navigator').activate()

#-------------------------------------------------------------------------
#
# Functions
#
#-------------------------------------------------------------------------
def cb_menu_position(menu, button):
    """
    Determine the position of the popup menu.
    """
    ret_val, x_pos, y_pos = button.get_window().get_origin()
    x_pos += button.get_allocation().x
    y_pos += button.get_allocation().y + button.get_allocation().height
    
    return (x_pos, y_pos, False)

def cb_menu_deactivate(menu, button):
    """
    Called when the popup menu disappears.
    """
    button.set_active(False)

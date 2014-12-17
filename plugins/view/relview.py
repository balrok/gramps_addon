# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2001-2007  Donald N. Allingham
# Copyright (C) 2009-2010  Gary Burton
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
Relationship View
"""
from __future__ import unicode_literals

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored
import cgi

#-------------------------------------------------------------------------
#
# Set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger("plugin.relview")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango

#-------------------------------------------------------------------------
#
# Gramps Modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import (ChildRef, EventRoleType, EventType, Family, 
                            FamilyRelType, Name, Person, Surname)
from gramps.gen.lib.date import Today
from gramps.gen.db import DbTxn
from gramps.gui.views.navigationview import NavigationView
from gramps.gui.editors import EditPerson, EditFamily
from gramps.gui.editors import FilterEditor
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.utils.file import media_path_full
from gramps.gen.utils.alive import probably_alive
from gramps.gui.utils import open_file_with_default_application
from gramps.gen.datehandler import displayer, get_date
from gramps.gui.thumbnails import get_thumbnail_image
from gramps.gen.config import config
from gramps.gui import widgets
from gramps.gui.widgets.reorderfam import Reorder
from gramps.gui.selectors import SelectorFactory
from gramps.gen.errors import WindowActiveError
from gramps.gui.views.bookmarks import PersonBookmarks
from gramps.gen.const import CUSTOM_FILTERS
from gramps.gen.utils.db import (get_birth_or_fallback, get_death_or_fallback, 
                          preset_name)

_GenderCode = {
    Person.MALE    : '\u2642', 
    Person.FEMALE  : '\u2640', 
    Person.UNKNOWN : '\u2650', 
    }

_NAME_START   = 0
_LABEL_START  = 0
_LABEL_STOP   = 1
_DATA_START   = _LABEL_STOP
_DATA_STOP    = _DATA_START+1
_BTN_START    = _DATA_STOP
_BTN_STOP     = _BTN_START+2
_PLABEL_START = 1 
_PLABEL_STOP  = _PLABEL_START+1
_PDATA_START  = _PLABEL_STOP
_PDATA_STOP   = _PDATA_START+2
_PDTLS_START  = _PLABEL_STOP
_PDTLS_STOP   = _PDTLS_START+2
_CLABEL_START = _PLABEL_START+1
_CLABEL_STOP  = _CLABEL_START+1
_CDATA_START  = _CLABEL_STOP
_CDATA_STOP   = _CDATA_START+1
_CDTLS_START  = _CDATA_START
_CDTLS_STOP   = _CDTLS_START+1
_ALABEL_START = 0
_ALABEL_STOP  = _ALABEL_START+1
_ADATA_START  = _ALABEL_STOP
_ADATA_STOP   = _ADATA_START+3
_SDATA_START  = 2
_SDATA_STOP   = 4
_RETURN = Gdk.keyval_from_name("Return")
_KP_ENTER = Gdk.keyval_from_name("KP_Enter")
_SPACE = Gdk.keyval_from_name("space")
_LEFT_BUTTON = 1
_RIGHT_BUTTON = 3

class AttachList(object):

    def __init__(self):
        self.list = []
        self.max_x = 0
        self.max_y = 0

    def attach(self, widget, x0, x1, y0, y1, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, 
               yoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL):
        assert(widget)
        assert(x1>x0)
        self.list.append((widget, x0, x1, y0, y1, xoptions, yoptions))
        self.max_x = max(self.max_x, x1)
        self.max_y = max(self.max_y, y1)

class RelationshipView(NavigationView):
    """
    View showing a textual representation of the relationships of the 
    active person
    """
    #settings in the config file
    CONFIGSETTINGS = (
        ('preferences.family-siblings', True),
        ('preferences.family-details', True),
        ('preferences.relation-display-theme', "CLASSIC"),
        ('preferences.relation-shade', True),
        ('preferences.releditbtn', True),
        )

    def __init__(self, pdata, dbstate, uistate, nav_group=0):
        NavigationView.__init__(self, _('Relationships'),
                                      pdata, dbstate, uistate, 
                                      PersonBookmarks,
                                      nav_group)        

        self.func_list.update({
            '<PRIMARY>J' : self.jump,
            })

        dbstate.connect('database-changed', self.change_db)
        uistate.connect('nameformat-changed', self.build_tree)
        self.redrawing = False

        self.child = None
        self.old_handle = None

        self.reorder_sensitive = False
        self.collapsed_items = {}

        self.additional_uis.append(self.additional_ui())

        self.show_siblings = self._config.get('preferences.family-siblings')
        self.show_details = self._config.get('preferences.family-details')
        self.use_shade = self._config.get('preferences.relation-shade')
        self.theme = self._config.get('preferences.relation-display-theme')
        self.toolbar_visible = config.get('interface.toolbar-on')

    def _connect_db_signals(self):
        """
        implement from base class DbGUIElement
        Register the callbacks we need.
        """
        # Add a signal to pick up event changes, bug #1416
        self.callman.add_db_signal('event-update', self.family_update)

        self.callman.add_db_signal('person-update', self.person_update)
        self.callman.add_db_signal('person-rebuild', self.person_rebuild)
        self.callman.add_db_signal('family-update', self.family_update)
        self.callman.add_db_signal('family-add',    self.family_add)
        self.callman.add_db_signal('family-delete', self.family_delete)
        self.callman.add_db_signal('family-rebuild', self.family_rebuild)

        self.callman.add_db_signal('person-delete', self.redraw)

    def navigation_type(self):
        return 'Person'

    def can_configure(self):
        """
        See :class:`~gui.views.pageview.PageView 
        :return: bool
        """
        return True

    def goto_handle(self, handle):
        self.change_person(handle)

    def shade_update(self, client, cnxn_id, entry, data):
        self.use_shade = self._config.get('preferences.relation-shade')
        self.toolbar_visible = config.get('interface.toolbar-on')
        self.uistate.modify_statusbar(self.dbstate)
        self.redraw()

    def config_update(self, client, cnxn_id, entry, data):
        self.show_siblings = self._config.get('preferences.family-siblings')
        self.show_details = self._config.get('preferences.family-details')
        self.redraw()

    def build_tree(self):
        self.redraw()

    def person_update(self, handle_list):
        if self.active:
            person  = self.get_active()
            if person:
                while not self.change_person(person):
                    pass
            else:
                self.change_person(None)
        else:
            self.dirty = True

    def person_rebuild(self):
        """Large change to person database"""
        if self.active:
            self.bookmarks.redraw()
            person  = self.get_active()
            if person:
                while not self.change_person(person):
                    pass
            else:
                self.change_person(None)
        else:
            self.dirty = True

    def family_update(self, handle_list):
        if self.active:
            person  = self.get_active()
            if person:
                while not self.change_person(person):
                    pass
            else:
                self.change_person(None)
        else:
            self.dirty = True

    def family_add(self, handle_list):
        if self.active:
            person  = self.get_active()
            if person:
                while not self.change_person(person):
                    pass
            else:
                self.change_person(None)
        else:
            self.dirty = True

    def family_delete(self, handle_list):
        if self.active:
            person  = self.get_active()
            if person:
                while not self.change_person(person):
                    pass
            else:
                self.change_person(None)
        else:
            self.dirty = True

    def family_rebuild(self):
        if self.active:
            person  = self.get_active()
            if person:
                while not self.change_person(person):
                    pass
            else:
                self.change_person(None)
        else:
            self.dirty = True

    def change_page(self):
        NavigationView.change_page(self)
        self.uistate.clear_filter_results()
            
    def get_stock(self):
        """
        Return the name of the stock icon to use for the display.
        This assumes that this icon has already been registered with
        GNOME as a stock icon.
        """
        return 'gramps-relation'
    
    def get_viewtype_stock(self):
        """Type of view in category
        """
        return 'gramps-relation'

    def build_widget(self):
        """
        Build the widget that contains the view, see 
        :class:`~gui.views.pageview.PageView 
        """
        container = Gtk.VBox()
        container.set_border_width(12)

        self.vbox = Gtk.VBox()
        self.vbox.show()

        self.header = Gtk.VBox()
        self.header.show()

        self.child = None

        self.scroll = Gtk.ScrolledWindow()

        st_cont = self.scroll.get_style_context()
        col = st_cont.lookup_color('base_color')
        if col[0]:
            self.color = col[1]
        else:
            self.color = Gdk.RGBA()
            self.color.parse("White")

        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll.show()
        
        vp = Gtk.Viewport()
        vp.set_shadow_type(Gtk.ShadowType.NONE)
        vp.add(self.vbox)

        self.scroll.add(vp)
        self.scroll.show_all()

        container.set_spacing(6)
        container.pack_start(self.header, False, False, 0)
        container.pack_start(Gtk.HSeparator(), False, False, 0)
        container.add(self.scroll)
        container.show_all()
        return container

    def additional_ui(self):
        """
        Specifies the UIManager XML code that defines the menus and buttons
        associated with the interface.
        """
        return '''<ui>
          <menubar name="MenuBar">
            <menu action="GoMenu">
              <placeholder name="CommonGo">
                <menuitem action="Back"/>
                <menuitem action="Forward"/>
                <separator/>
                <menuitem action="HomePerson"/>
                <separator/>
              </placeholder>
            </menu>
            <menu action="EditMenu">
              <menuitem action="Edit"/>
              <menuitem action="AddParentsMenu"/>
              <menuitem action="ShareFamilyMenu"/>
              <menuitem action="AddSpouseMenu"/>
              <menuitem action="ChangeOrder"/>
              <menuitem action="FilterEdit"/>
            </menu>
            <menu action="BookMenu">
              <placeholder name="AddEditBook">
                <menuitem action="AddBook"/>
                <menuitem action="EditBook"/>
              </placeholder>
            </menu>
            <menu action="ViewMenu">
            </menu>
          </menubar>
          <toolbar name="ToolBar">
            <placeholder name="CommonNavigation">
              <toolitem action="Back"/>  
              <toolitem action="Forward"/>  
              <toolitem action="HomePerson"/>
            </placeholder>
            <placeholder name="CommonEdit">
              <toolitem action="Edit"/>
              <toolitem action="AddParents"/>
              <toolitem action="ShareFamily"/>
              <toolitem action="AddSpouse"/>
              <toolitem action="ChangeOrder"/>
            </placeholder>
          </toolbar>
          <popup name="Popup">
            <menuitem action="Back"/>
            <menuitem action="Forward"/>
            <menuitem action="HomePerson"/>
            <separator/>
          </popup>
        </ui>'''

    def define_actions(self):
        NavigationView.define_actions(self)

        self.order_action = Gtk.ActionGroup(name=self.title + '/ChangeOrder')
        self.order_action.add_actions([
            ('ChangeOrder', Gtk.STOCK_SORT_ASCENDING, _('_Reorder'), None ,
            _("Change order of parents and families"), self.reorder),
            ])

        self.family_action = Gtk.ActionGroup(name=self.title + '/Family')
        self.family_action.add_actions([
            ('Edit', Gtk.STOCK_EDIT, _('Edit...'), "<PRIMARY>Return",
                _("Edit the active person"), self.edit_active),
            ('AddSpouse', 'gramps-spouse', _('Partner'), None ,
                _("Add a new family with person as parent"), self.add_spouse),
            ('AddSpouseMenu', 'gramps-spouse', _('Add Partner...'), None ,
                _("Add a new family with person as parent"), self.add_spouse),
            ('AddParents', 'gramps-parents-add', _('Add'), None ,
                _("Add a new set of parents"), self.add_parents),
            ('AddParentsMenu', 'gramps-parents-add', _('Add New Parents...'), 
                None, _("Add a new set of parents"), self.add_parents),
            ('ShareFamily', 'gramps-parents-open', _('Share'), 
                None , _("Add person as child to an existing family"), 
                self.select_parents),
            ('ShareFamilyMenu', 'gramps-parents-open', 
                _('Add Existing Parents...'), None , 
                _("Add person as child to an existing family"), 
                self.select_parents),
            ])
            
        self._add_action('FilterEdit',  None, _('Person Filter Editor'), 
                        callback=self.filter_editor)
                        
        self._add_action_group(self.order_action)
        self._add_action_group(self.family_action)

        self.order_action.set_sensitive(self.reorder_sensitive)
        self.family_action.set_sensitive(False)

    def filter_editor(self, obj):
        try:
            FilterEditor('Person', CUSTOM_FILTERS, 
                         self.dbstate, self.uistate)
        except WindowActiveError:
            return

    def change_db(self, db):
        #reset the connects
        self._change_db(db)
        if self.child:
            list(map(self.vbox.remove, self.vbox.get_children()))
            list(map(self.header.remove, self.header.get_children()))
            self.child = None
        if self.active:
                self.bookmarks.redraw()
        self.redraw()

    def get_name(self, handle, use_gender=False):
        if handle:
            person = self.dbstate.db.get_person_from_handle(handle)
            name = name_displayer.display(person)
            if use_gender:
                gender = _GenderCode[person.gender]
            else:
                gender = ""
            return (name, gender)
        else:
            return (_("Unknown"), "")

    def redraw(self, *obj):
        active_person = self.get_active()
        if active_person:
            self.change_person(active_person)
        else:
            self.change_person(None)
        
    def change_person(self, obj):
        self.change_active(obj)
        try:
            return self._change_person(obj)
        except AttributeError as msg:
            import traceback
            exc = traceback.format_exc()
            _LOG.error(str(msg) +"\n" + exc)
            from gramps.gui.dialog import RunDatabaseRepair
            RunDatabaseRepair(str(msg))
            self.redrawing = False
            return True

    def _change_person(self, obj):
        if obj == self.old_handle:
            #same object, keep present scroll position
            old_vadjust = self.scroll.get_vadjustment().get_value()
            self.old_handle = obj
        else:
            #different object, scroll to top
            old_vadjust = self.scroll.get_vadjustment().get_lower()
            self.old_handle = obj
        self.scroll.get_vadjustment().set_value(
                            self.scroll.get_vadjustment().get_lower())
        if self.redrawing:
            return False
        self.redrawing = True

        for old_child in self.vbox.get_children():
            self.vbox.remove(old_child)
        for old_child in self.header.get_children():
            self.header.remove(old_child)

        person = self.dbstate.db.get_person_from_handle(obj)
        if not person:
            self.family_action.set_sensitive(False)
            self.order_action.set_sensitive(False)
            self.redrawing = False
            return
        self.family_action.set_sensitive(True)

        self.write_title(person)

        self.attach = AttachList()
        self.row = 0

        family_handle_list = person.get_parent_family_handle_list()

        self.reorder_sensitive = len(family_handle_list)> 1

        if family_handle_list:
            for family_handle in family_handle_list:
                if family_handle:
                    self.write_parents(family_handle, person)
        else:
            self.write_label("%s:" % _('Parents'), None, True, person)
            self.row += 1
                
        family_handle_list = person.get_family_handle_list()
        
        if not self.reorder_sensitive:
            self.reorder_sensitive = len(family_handle_list)> 1

        if family_handle_list:
            for family_handle in family_handle_list:
                if family_handle:
                    self.write_family(family_handle, person)

        self.row = 0

        # Here it is necessary to beat GTK into submission. For some
        # bizzare reason, if you have an empty column that is spanned, 
        # you lose the appropriate FILL handling. So, we need to see if
        # column 3 is unused (usually if there is no siblings or children.
        # If so, we need to subtract one index of each x coord > 3.
                
        found = False
        for d in self.attach.list:
            if d[1] == 4 or d[2] == 4:
                found = True

        if found:
            cols = self.attach.max_x
        else:
            cols = self.attach.max_x-1

        self.child = Gtk.Table(n_rows=self.attach.max_y, n_columns=cols)
        self.child.set_border_width(12)
        self.child.set_col_spacings(12)
        self.child.set_row_spacings(0)

        for d in self.attach.list:
            x0 = d[1]
            x1 = d[2]
            if not found:
                if x0 > 4:
                    x0 -= 1
                if x1 > 4:
                    x1 -= 1
            self.child.attach(d[0], x0, x1, d[3], d[4], d[5], d[6])

        self.child.show_all()

        self.vbox.pack_start(self.child, False, True, 0)
        #reset scroll position as it was before
        self.scroll.get_vadjustment().set_value(old_vadjust)
        self.redrawing = False
        self.uistate.modify_statusbar(self.dbstate)

        self.order_action.set_sensitive(self.reorder_sensitive)
        self.dirty = False

        return True

    def write_title(self, person):

        list(map(self.header.remove, self.header.get_children()))
        table = Gtk.Table(n_rows=2, n_columns=3)
        table.set_col_spacings(12)
        table.set_row_spacings(0)

        # name and edit button
        name = name_displayer.display(person)
        fmt = '<span size="larger" weight="bold">%s</span>'
        text = fmt % cgi.escape(name)
        label = widgets.DualMarkupLabel(text, _GenderCode[person.gender],
                                        x_align=1)
        if self._config.get('preferences.releditbtn'):
            button = widgets.IconButton(self.edit_button_press, 
                                        person.handle)
            button.set_tooltip_text(_('Edit %s') % name)
        else:
            button = None
        hbox = widgets.LinkBox(label, button)

        table.attach(hbox, 0, 2, 0, 1)

        eventbox = Gtk.EventBox()
        if self.use_shade:
            eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
        table.attach(eventbox, 1, 2, 1, 2)
        subtbl = Gtk.Table(n_rows=3, n_columns=3)
        subtbl.set_col_spacings(12)
        subtbl.set_row_spacings(0)
        eventbox.add(subtbl)
                
        # GRAMPS ID

        subtbl.attach(widgets.BasicLabel("%s:" % _('ID')),
                      1, 2, 0, 1, xoptions=Gtk.AttachOptions.FILL, yoptions=0)
        subtbl.attach(widgets.BasicLabel(person.gramps_id),
                      2, 3, 0, 1, yoptions=0)

        # Birth event.
        birth = get_birth_or_fallback(self.dbstate.db, person)
        if birth:
            birth_title = birth.get_type()
        else:
            birth_title = _("Birth")

        subtbl.attach(widgets.BasicLabel("%s:" % birth_title),
                      1, 2, 1, 2, xoptions=Gtk.AttachOptions.FILL, yoptions=0)
        subtbl.attach(widgets.BasicLabel(self.format_event(birth)),
                      2, 3, 1, 2, yoptions=0)

        death = get_death_or_fallback(self.dbstate.db, person)
        if death:
            death_title = death.get_type()
        else:
            death_title = _("Death")

        showed_death = False
        if birth:
            birth_date = birth.get_date_object()
            if (birth_date and birth_date.get_valid()):
                if death:
                    death_date = death.get_date_object()
                    if (death_date and death_date.get_valid()):
                        age = death_date - birth_date
                        subtbl.attach(widgets.BasicLabel("%s:" % death_title),
                                      1, 2, 2, 3, xoptions=Gtk.AttachOptions.FILL, yoptions=0)
                        subtbl.attach(widgets.BasicLabel("%s (%s)" % 
                                                         (self.format_event(death), age),
                                                         Pango.EllipsizeMode.END),
                                      2, 3, 2, 3, yoptions=0)
                        showed_death = True
                if not showed_death:
                    age = Today() - birth_date
                    if probably_alive(person, self.dbstate.db):
                        subtbl.attach(widgets.BasicLabel("%s:" % _("Alive")),
                                      1, 2, 2, 3, xoptions=Gtk.AttachOptions.FILL, yoptions=0)
                        subtbl.attach(widgets.BasicLabel("(%s)" % age, Pango.EllipsizeMode.END),
                                      2, 3, 2, 3, yoptions=0)
                    else:
                        subtbl.attach(widgets.BasicLabel("%s:" % _("Death")),
                                      1, 2, 2, 3, xoptions=Gtk.AttachOptions.FILL, yoptions=0)
                        subtbl.attach(widgets.BasicLabel("%s (%s)" % (_("unknown"), age), 
                                                         Pango.EllipsizeMode.END),
                                      2, 3, 2, 3, yoptions=0)
                    showed_death = True

        if not showed_death:
            subtbl.attach(widgets.BasicLabel("%s:" % death_title),
                          1, 2, 2, 3, xoptions=Gtk.AttachOptions.FILL, yoptions=0)
            subtbl.attach(widgets.BasicLabel(self.format_event(death)),
                          2, 3, 2, 3, yoptions=0)

        mbox = Gtk.HBox()
        mbox.add(table)

        # image
        image_list = person.get_media_list()
        if image_list:
            mobj = self.dbstate.db.get_object_from_handle(image_list[0].ref)
            if mobj and mobj.get_mime_type()[0:5] == "image":
                pixbuf = get_thumbnail_image(
                                media_path_full(self.dbstate.db, 
                                                mobj.get_path()),
                                rectangle=image_list[0].get_rectangle())
                image = Gtk.Image()
                image.set_from_pixbuf(pixbuf)
                button = Gtk.Button()
                button.add(image)
                button.connect("clicked", lambda obj: self.view_photo(mobj))
                mbox.pack_end(button, False, True, 0)

        mbox.show_all()
        self.header.pack_start(mbox, False, True, 0)

    def view_photo(self, photo):
        """
        Open this picture in the default picture viewer.
        """
        photo_path = media_path_full(self.dbstate.db, photo.get_path())
        open_file_with_default_application(photo_path)

    def write_person_event(self, ename, event):
        if event:
            dobj = event.get_date_object()
            phandle = event.get_place_handle()
            if phandle:
                pname = self.place_name(phandle)
            else:
                pname = None

            value = {
                'date' : displayer.display(dobj), 
                'place' : pname, 
                }
        else:
            pname = None
            dobj = None

        if dobj:
            if pname:
                self.write_person_data(ename, 
                                       _('%(date)s in %(place)s') % value)
            else:
                self.write_person_data(ename, '%(date)s' % value)
        elif pname:
            self.write_person_data(ename, pname)
        else:
            self.write_person_data(ename, '')

    def format_event(self, event):
        if event:
            dobj = event.get_date_object()
            phandle = event.get_place_handle()
            if phandle:
                pname = self.place_name(phandle)
            else:
                pname = None

            value = {
                'date' : displayer.display(dobj), 
                'place' : pname, 
                }
        else:
            pname = None
            dobj = None

        if dobj:
            if pname:
                return _('%(date)s in %(place)s') % value
            else:
                return '%(date)s' % value
        elif pname:
            return pname
        else:
            return ''

    def write_person_data(self, title, data):
        self.attach.attach(widgets.BasicLabel(title), _ALABEL_START, 
                           _ALABEL_STOP, self.row, self.row+1, 
                           xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK)
        self.attach.attach(widgets.BasicLabel(data), 
                           _ADATA_START, _ADATA_STOP, 
                           self.row, self.row+1)
        self.row += 1

    def write_label(self, title, family, is_parent, person = None):
        msg = '<span style="italic" weight="heavy">%s</span>' % cgi.escape(title)
        hbox = Gtk.HBox()
        label = widgets.MarkupLabel(msg, x_align=1)
        # Draw the collapse/expand button:
        if family is not None:
            if self.check_collapsed(person.handle, family.handle):
                arrow = widgets.ExpandCollapseArrow(True,
                                                    self.expand_collapse_press,
                                                    (person, family.handle))
            else:
                arrow = widgets.ExpandCollapseArrow(False,
                                                    self.expand_collapse_press,
                                                    (person, family.handle))
        else :
            arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.RIGHT, 
                                        shadow_type=Gtk.ShadowType.OUT)
        hbox.pack_start(arrow, False, True, 0)
        hbox.pack_start(label, True, True, 0)
        self.attach.attach(hbox,
                           _LABEL_START, _LABEL_STOP, 
                           self.row, self.row+1, Gtk.AttachOptions.SHRINK|Gtk.AttachOptions.FILL)

        if family:
            value = family.gramps_id
        else:
            value = ""
        self.attach.attach(widgets.BasicLabel(value), 
                           _DATA_START, _DATA_STOP, 
                           self.row, self.row+1, Gtk.AttachOptions.SHRINK|Gtk.AttachOptions.FILL)

        if family and self.check_collapsed(person.handle, family.handle):
            # show family names later
            pass
        else:
            hbox = Gtk.HBox()
            hbox.set_spacing(12)
            if is_parent:
                call_fcn = self.add_parent_family
                del_fcn = self.delete_parent_family
                add_msg = _('Add a new set of parents')
                sel_msg = _('Add person as child to an existing family')
                edit_msg = _('Edit parents')
                ord_msg = _('Reorder parents')
                del_msg = _('Remove person as child of these parents')
            else:
                add_msg = _('Add a new family with person as parent')
                sel_msg = None
                edit_msg = _('Edit family')
                ord_msg = _('Reorder families')
                del_msg = _('Remove person as parent in this family')
                call_fcn = self.add_family
                del_fcn = self.delete_family

            if not self.toolbar_visible and not self.dbstate.db.readonly:
                # Show edit-Buttons if toolbar is not visible
                if self.reorder_sensitive:
                    add = widgets.IconButton(self.reorder_button_press, None, 
                                             Gtk.STOCK_SORT_ASCENDING)
                    add.set_tooltip_text(ord_msg)
                    hbox.pack_start(add, False, True, 0)

                add = widgets.IconButton(call_fcn, None, Gtk.STOCK_ADD)
                add.set_tooltip_text(add_msg)
                hbox.pack_start(add, False, True, 0)

                if is_parent:
                    add = widgets.IconButton(self.select_family, None,
                                             Gtk.STOCK_INDEX)
                    add.set_tooltip_text(sel_msg)
                    hbox.pack_start(add, False, True, 0)

            if family:
                edit = widgets.IconButton(self.edit_family, family.handle, 
                                          Gtk.STOCK_EDIT)
                edit.set_tooltip_text(edit_msg)
                hbox.pack_start(edit, False, True, 0)
                if not self.dbstate.db.readonly:
                    delete = widgets.IconButton(del_fcn, family.handle, 
                                                Gtk.STOCK_REMOVE)
                    delete.set_tooltip_text(del_msg)
                    hbox.pack_start(delete, False, True, 0)
            self.attach.attach(hbox, _BTN_START, _BTN_STOP, self.row, self.row+1)
        self.row += 1
        
######################################################################

    def write_parents(self, family_handle, person = None):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        if not family:
            return
        if person and self.check_collapsed(person.handle, family_handle):
            # don't show rest
            self.write_label("%s:" % _('Parents'), family, True, person)
            self.row -= 1 # back up one row for summary names
            active = self.get_active()
            child_list = [ref.ref for ref in family.get_child_ref_list()
                          if ref.ref != active]
            if child_list:
                count = len(child_list)
            else:
                count = 0
            if count > 1 :
                # translators: leave all/any {...} untranslated
                childmsg = ngettext(" ({number_of} sibling)",
                                    " ({number_of} siblings)", count
                                   ).format(number_of=count)
            elif count == 1 :
                gender = self.dbstate.db.get_person_from_handle(
                                        child_list[0]).gender
                if gender == Person.MALE :
                    childmsg = _(" (1 brother)")
                elif gender == Person.FEMALE :
                    childmsg = _(" (1 sister)")
                else :
                    childmsg = _(" (1 sibling)")
            else :
                childmsg = _(" (only child)")
            box = self.get_people_box(family.get_father_handle(),
                                      family.get_mother_handle(),
                                      post_msg=childmsg)
            eventbox = Gtk.EventBox()
            if self.use_shade:
                eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
            eventbox.add(box)
            self.attach.attach(
                eventbox, _PDATA_START, _PDATA_STOP,
                self.row, self.row+1)
            self.row += 1 # now advance it
        else:
            self.write_label("%s:" % _('Parents'), family, True, person)
            self.write_person(_('Father'), family.get_father_handle())
            self.write_person(_('Mother'), family.get_mother_handle())

            if self.show_siblings:
                active = self.get_active()
                hbox = Gtk.HBox()
                if self.check_collapsed(person.handle, "SIBLINGS"):
                    arrow = widgets.ExpandCollapseArrow(True,
                                                        self.expand_collapse_press,
                                                        (person, "SIBLINGS"))
                else:
                    arrow = widgets.ExpandCollapseArrow(False,
                                                        self.expand_collapse_press,
                                                        (person, "SIBLINGS"))
                hbox.pack_start(arrow, False, True, 0)
                label_cell = self.build_label_cell(_('Siblings'))
                hbox.pack_start(label_cell, True, True, 0)
                self.attach.attach(
                    hbox, _CLABEL_START-1, _CLABEL_STOP-1, self.row, 
                    self.row+1, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK,
                    yoptions=Gtk.AttachOptions.FILL)

                if self.check_collapsed(person.handle, "SIBLINGS"):
                    hbox = Gtk.HBox()
                    child_list = [ref.ref for ref in family.get_child_ref_list()
                                  if ref.ref != active]
                    if child_list:
                        count = len(child_list)
                    else:
                        count = 0
                    if count > 1 :
                        # translators: leave all/any {...} untranslated
                        childmsg = ngettext(" ({number_of} sibling)",
                                            " ({number_of} siblings)", count
                                           ).format(number_of=count)
                    elif count == 1 :
                        gender = self.dbstate.db.get_person_from_handle(
                                                child_list[0]).gender
                        if gender == Person.MALE :
                            childmsg = _(" (1 brother)")
                        elif gender == Person.FEMALE :
                            childmsg = _(" (1 sister)")
                        else :
                            childmsg = _(" (1 sibling)")
                    else :
                        childmsg = _(" (only child)")
                    box = self.get_people_box(post_msg=childmsg)
                    eventbox = Gtk.EventBox()
                    if self.use_shade:
                        eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
                    eventbox.add(box)
                    self.attach.attach(
                        eventbox, _PDATA_START, _PDATA_STOP,
                        self.row, self.row+1)
                    self.row += 1 # now advance it
                else:
                    hbox = Gtk.HBox()
                    addchild = widgets.IconButton(self.add_child_to_fam, 
                                                  family.handle, 
                                                  Gtk.STOCK_ADD)
                    addchild.set_tooltip_text(_('Add new child to family'))
                    selchild = widgets.IconButton(self.sel_child_to_fam, 
                                                  family.handle, 
                                                  Gtk.STOCK_INDEX)
                    selchild.set_tooltip_text(_('Add existing child to family'))
                    hbox.pack_start(addchild, False, True, 0)
                    hbox.pack_start(selchild, False, True, 0)

                    self.attach.attach(
                        hbox, _CLABEL_START, _CLABEL_STOP, self.row, 
                        self.row+1, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK,
                        yoptions=Gtk.AttachOptions.FILL)

                    self.row += 1
                    vbox = Gtk.VBox()
                    i = 1
                    child_list = [ref.ref for ref in family.get_child_ref_list()]
                    for child_handle in child_list:
                        child_should_be_linked = (child_handle != active)
                        self.write_child(vbox, child_handle, i, child_should_be_linked)
                        i += 1
                    eventbox = Gtk.EventBox()
                    if self.use_shade:
                        eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
                    eventbox.add(vbox)
                    self.attach.attach(
                        eventbox, _CDATA_START-1, _CDATA_STOP, self.row,
                        self.row+1)

            self.row += 1

    def get_people_box(self, *handles, **kwargs):
        vbox = Gtk.HBox()
        initial_name = True
        for handle in handles:
            if not initial_name:
                link_label = Gtk.Label(label=" %s " % _('and'))
                link_label.show()
                vbox.pack_start(link_label, False, True, 0)
            initial_name = False
            if handle:
                name = self.get_name(handle, True)
                link_label = widgets.LinkLabel(name, self._button_press, 
                                               handle, theme=self.theme)
                if self.use_shade:
                    link_label.override_background_color(Gtk.StateType.NORMAL, self.color)
                if self._config.get('preferences.releditbtn'):
                    button = widgets.IconButton(self.edit_button_press, 
                                                handle)
                    button.set_tooltip_text(_('Edit %s') % name[0])
                else:
                    button = None
                vbox.pack_start(widgets.LinkBox(link_label, button),
                                False, True, 0)
            else:
                link_label = Gtk.Label(label=_('Unknown'))
                link_label.show()
                vbox.pack_start(link_label, False, True, 0)
        if "post_msg" in kwargs and kwargs["post_msg"]:
            link_label = Gtk.Label(label=kwargs["post_msg"])
            link_label.show()
            vbox.pack_start(link_label, False, True, 0)
        return vbox

    def write_person(self, title, handle):
        if title:
            format = '<span weight="bold">%s: </span>'
        else:
            format = "%s"

        label = widgets.MarkupLabel(format % cgi.escape(title),
                                    x_align=1, y_align=0)
        if self._config.get('preferences.releditbtn'):
            label.set_padding(0, 5)
        self.attach.attach(label, _PLABEL_START, _PLABEL_STOP, self.row, 
                           self.row+1, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK,
                           yoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK)

        vbox = Gtk.VBox()
        
        if handle:
            name = self.get_name(handle, True)
            person = self.dbstate.db.get_person_from_handle(handle)
            parent = len(person.get_parent_family_handle_list()) > 0
            format = ''
            relation_display_theme = self._config.get(
                                    'preferences.relation-display-theme')
            if parent:
                emph = True
            else:
                emph = False
            link_label = widgets.LinkLabel(name, self._button_press, 
                                           handle, emph, theme=self.theme)
            if self.use_shade:
                link_label.override_background_color(Gtk.StateType.NORMAL, self.color)
            if self._config.get('preferences.releditbtn'):
                button = widgets.IconButton(self.edit_button_press, handle)
                button.set_tooltip_text(_('Edit %s') % name[0])
            else:
                button = None
            vbox.pack_start(widgets.LinkBox(link_label, button), True, True, 0)
        else:
            link_label = Gtk.Label(label=_('Unknown'))
            link_label.set_alignment(0, 1)
            link_label.show()
            vbox.pack_start(link_label, True, True, 0)
            
        if self.show_details:
            value = self.info_string(handle)
            if value:
                vbox.pack_start(widgets.MarkupLabel(value), True, True, 0)

        eventbox = Gtk.EventBox()
        if self.use_shade:
            eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
        eventbox.add(vbox)
        
        self.attach.attach(eventbox, _PDATA_START, _PDATA_STOP,
                           self.row, self.row+1)
        self.row += 1
        return vbox

    def build_label_cell(self, title):
        if title:
            format = '<span weight="bold">%s: </span>'
        else:
            format = "%s"

        lbl = widgets.MarkupLabel(format % cgi.escape(title),
                                  x_align=1, y_align=.5)
        if self._config.get('preferences.releditbtn'):
            lbl.set_padding(0, 5)
        return lbl

    def write_child(self, vbox, handle, index, child_should_be_linked):
        if not child_should_be_linked:
            original_vbox = vbox
            vbox = Gtk.VBox()
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
            if self.use_shade:
                ev = Gtk.EventBox()
                ev.override_background_color(Gtk.StateType.NORMAL, self.color)
                ev.add(vbox)
                frame.add(ev)
            else:
                frame.add(vbox)
            original_vbox.add(frame)
        
        parent = has_children(self.dbstate.db,
                              self.dbstate.db.get_person_from_handle(handle))

        format = ''
        relation_display_theme = self._config.get(
                                        'preferences.relation-display-theme')
        emph = False
        if child_should_be_linked and parent:
            emph = True
        elif child_should_be_linked and not parent:
            emph = False
        elif parent and not child_should_be_linked:
            emph = None

        if child_should_be_linked:
            link_func = self._button_press
        else:
            link_func = None

        name = self.get_name(handle, True)
        link_label = widgets.LinkLabel(name, link_func, handle, emph,
                                       theme=self.theme)

        if self.use_shade:
            link_label.override_background_color(Gtk.StateType.NORMAL, self.color)
        link_label.set_padding(3, 0)
        if child_should_be_linked and self._config.get(
            'preferences.releditbtn'):
            button = widgets.IconButton(self.edit_button_press, handle)
            button.set_tooltip_text(_('Edit %s') % name[0])
        else:
            button = None

        hbox = Gtk.HBox()
        l = widgets.BasicLabel("%d." % index)
        l.set_width_chars(3)
        l.set_alignment(1.0, 0.5)
        hbox.pack_start(l, False, False, 0)
        hbox.pack_start(widgets.LinkBox(link_label, button),
                        False, False, 4)
        hbox.show()
        vbox.pack_start(hbox, True, True, 0)

        if self.show_details:
            value = self.info_string(handle)
            if value:
                l = widgets.MarkupLabel(value)
                l.set_padding(48, 0)
                vbox.add(l)

    def write_data(self, box, title, start_col=_SDATA_START,
                   stop_col=_SDATA_STOP):
        box.add(widgets.BasicLabel(title))

    def info_string(self, handle):
        person = self.dbstate.db.get_person_from_handle(handle)
        if not person:
            return None

        birth = get_birth_or_fallback(self.dbstate.db, person)
        if birth and birth.get_type() != EventType.BIRTH:
            sdate = get_date(birth)
            if sdate:
                bdate  = "<i>%s</i>" % cgi.escape(sdate)
            else:
                bdate = ""
        elif birth:
            bdate  = cgi.escape(get_date(birth))
        else:
            bdate = ""

        death = get_death_or_fallback(self.dbstate.db, person)
        if death and death.get_type() != EventType.DEATH:
            sdate = get_date(death)
            if sdate:
                ddate  = "<i>%s</i>" % cgi.escape(sdate)
            else:
                ddate = ""
        elif death:
            ddate  = cgi.escape(get_date(death))
        else:
            ddate = ""

        if bdate and ddate:
            value = _("%(birthabbrev)s %(birthdate)s, %(deathabbrev)s %(deathdate)s") % {
                'birthabbrev': birth.type.get_abbreviation(),
                'deathabbrev': death.type.get_abbreviation(),
                'birthdate' : bdate, 
                'deathdate' : ddate
                }
        elif bdate:
            value = _("%(event)s %(date)s") % {'event': birth.type.get_abbreviation(), 'date': bdate}
        elif ddate:
            value = _("%(event)s %(date)s") % {'event': death.type.get_abbreviation(), 'date': ddate}
        else:
            value = ""
        return value

    def check_collapsed(self, person_handle, handle):
        """ Return true if collapsed. """
        return (handle in self.collapsed_items.get(person_handle, []))

    def expand_collapse_press(self, obj, event, pair):
        """ Calback function for ExpandCollapseArrow, user param is
            pair, which is a tuple (object, handle) which handles the
            section of which the collapse state must change, so a
            parent, siblings id, family id, family children id, etc.
            NOTE: object must be a thing that has a handle field.
        """
        if button_activated(event, _LEFT_BUTTON):
            object, handle = pair
            if object.handle in self.collapsed_items:
                if handle in self.collapsed_items[object.handle]:
                    self.collapsed_items[object.handle].remove(handle)
                else:
                    self.collapsed_items[object.handle].append(handle)
            else:
                self.collapsed_items[object.handle] = [handle]
            self.redraw()

    def _button_press(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            self.change_active(handle)
        elif button_activated(event, _RIGHT_BUTTON):
            myMenu = Gtk.Menu()
            myMenu.append(self.build_menu_item(handle))
            myMenu.popup(None, None, None, None, event.button, event.time)

    def build_menu_item(self, handle):
        person = self.dbstate.db.get_person_from_handle(handle)
        name = name_displayer.display(person)

        item = Gtk.ImageMenuItem(None)
        image = Gtk.Image.new_from_stock(Gtk.STOCK_EDIT, Gtk.IconSize.MENU)
        image.show()
        label = Gtk.Label(label=_("Edit %s") % name)
        label.show()
        label.set_alignment(0, 0)

        item.set_image(image)
        item.add(label)

        item.connect('activate', self.edit_menu, handle)
        item.show()
        return item

    def edit_menu(self, obj, handle):
        person = self.dbstate.db.get_person_from_handle(handle)
        try:
            EditPerson(self.dbstate, self.uistate, [], person)
        except WindowActiveError:
            pass

    def write_relationship(self, box, family):
        msg = _('Relationship type: %s') % cgi.escape(str(family.get_relationship()))
        box.add(widgets.MarkupLabel(msg))

    def place_name(self, handle):
        p = self.dbstate.db.get_place_from_handle(handle)
        return p.get_title()

    def write_relationship_events(self, vbox, family):
        value = False
        for event_ref in family.get_event_ref_list():
            handle = event_ref.ref
            event = self.dbstate.db.get_event_from_handle(handle)
            if (event and event.get_type().is_relationship_event() and
                (event_ref.get_role() == EventRoleType.FAMILY or 
                 event_ref.get_role() == EventRoleType.PRIMARY)):
                self.write_event_ref(vbox, event.get_type().string, event)
                value = True
        return value

    def write_event_ref(self, vbox, ename, event, start_col=_SDATA_START, 
                        stop_col=_SDATA_STOP):
        if event:
            dobj = event.get_date_object()
            phandle = event.get_place_handle()
            if phandle:
                pname = self.place_name(phandle)
            else:
                pname = None

            value = {
                'date' : displayer.display(dobj), 
                'place' : pname, 
                'event_type' : ename, 
                }
        else:
            pname = None
            dobj = None
            value = { 'event_type' : ename, }

        if dobj:
            if pname:
                self.write_data(
                    vbox, _('%(event_type)s: %(date)s in %(place)s') %
                    value, start_col, stop_col)
            else:
                self.write_data(
                    vbox, _('%(event_type)s: %(date)s') % value, 
                    start_col, stop_col)
        elif pname:
            self.write_data(
                vbox, _('%(event_type)s: %(place)s') % value,
                start_col, stop_col)
        else:
            self.write_data(
                vbox, '%(event_type)s:' % value, start_col, stop_col)

    def write_family(self, family_handle, person = None):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        if family is None:
            from gramps.gui.dialog import WarningDialog
            WarningDialog(
                _('Broken family detected'),
                _('Please run the Check and Repair Database tool'))
            return
        
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        if self.get_active() == father_handle:
            handle = mother_handle
        else:
            handle = father_handle

        # collapse button
        if self.check_collapsed(person.handle, family_handle):
            # show "> Family: ..." and nothing else
            self.write_label("%s:" % _('Family'), family, False, person)
            self.row -= 1 # back up
            child_list = family.get_child_ref_list()
            if child_list:
                count = len(child_list)
            else:
                count = 0
            if count >= 1 :
                # translators: leave all/any {...} untranslated
                childmsg = ngettext(" ({number_of} child)",
                                    " ({number_of} children)", count
                                   ).format(number_of=count)
            else :
                childmsg = _(" (no children)")
            box = self.get_people_box(handle, post_msg=childmsg)
            eventbox = Gtk.EventBox()
            if self.use_shade:
                eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
            eventbox.add(box)
            self.attach.attach(
                eventbox, _PDATA_START, _PDATA_STOP,
                self.row, self.row+1)
            self.row += 1 # now advance it
        else:
            # show "V Family: ..." and the rest
            self.write_label("%s:" % _('Family'), family, False, person)
            if (handle or
                    family.get_relationship() != FamilyRelType.UNKNOWN):
                box = self.write_person(_('Spouse'), handle)

                if not self.write_relationship_events(box, family):
                    self.write_relationship(box, family)

            hbox = Gtk.HBox()
            if self.check_collapsed(family.handle, "CHILDREN"):
                arrow = widgets.ExpandCollapseArrow(True,
                                                    self.expand_collapse_press,
                                                    (family, "CHILDREN"))
            else:
                arrow = widgets.ExpandCollapseArrow(False,
                                                    self.expand_collapse_press,
                                                    (family, "CHILDREN"))
            hbox.pack_start(arrow, False, True, 0)
            label_cell = self.build_label_cell(_('Children'))
            hbox.pack_start(label_cell, True, True, 0)
            self.attach.attach(
                hbox, _CLABEL_START-1, _CLABEL_STOP-1, self.row, 
                self.row+1, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK,
                yoptions=Gtk.AttachOptions.FILL)

            if self.check_collapsed(family.handle, "CHILDREN"):
                hbox = Gtk.HBox()
                child_list = family.get_child_ref_list()
                if child_list:
                    count = len(child_list)
                else:
                    count = 0
                if count >= 1 :
                    # translators: leave all/any {...} untranslated
                    childmsg = ngettext(" ({number_of} child)",
                                        " ({number_of} children)", count
                                       ).format(number_of=count)
                else :
                    childmsg = _(" (no children)")
                box = self.get_people_box(post_msg=childmsg)
                eventbox = Gtk.EventBox()
                if self.use_shade:
                    eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
                eventbox.add(box)
                self.attach.attach(
                    eventbox, _PDATA_START, _PDATA_STOP,
                    self.row, self.row+1)
                self.row += 1 # now advance it
            else:
                hbox = Gtk.HBox()
                addchild = widgets.IconButton(self.add_child_to_fam, 
                                              family.handle, 
                                              Gtk.STOCK_ADD)
                addchild.set_tooltip_text(_('Add new child to family'))
                selchild = widgets.IconButton(self.sel_child_to_fam, 
                                              family.handle, 
                                              Gtk.STOCK_INDEX)
                selchild.set_tooltip_text(_('Add existing child to family'))                                  
                hbox.pack_start(addchild, False, True, 0)
                hbox.pack_start(selchild, False, True, 0)
                self.attach.attach(
                    hbox, _CLABEL_START, _CLABEL_STOP, self.row, 
                    self.row+1, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.SHRINK,
                    yoptions=Gtk.AttachOptions.FILL)

                vbox = Gtk.VBox()
                i = 1
                child_list = family.get_child_ref_list()
                for child_ref in child_list:
                    self.write_child(vbox, child_ref.ref, i, True)
                    i += 1

                self.row += 1
                eventbox = Gtk.EventBox()
                if self.use_shade:
                    eventbox.override_background_color(Gtk.StateType.NORMAL, self.color)
                eventbox.add(vbox)
                self.attach.attach(
                    eventbox, _CDATA_START-1, _CDATA_STOP, self.row,
                    self.row+1)
                self.row += 1

    def edit_button_press(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            self.edit_person(obj, handle)
        
    def edit_person(self, obj, handle):
        person = self.dbstate.db.get_person_from_handle(handle)
        try:
            EditPerson(self.dbstate, self.uistate, [], person)
        except WindowActiveError:
            pass

    def edit_family(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            family = self.dbstate.db.get_family_from_handle(handle)
            try:
                EditFamily(self.dbstate, self.uistate, [], family)
            except WindowActiveError:
                pass

    def add_family(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            family = Family()
            person = self.dbstate.db.get_person_from_handle(self.get_active())
            if not person:
                return
            
            if person.gender == Person.MALE:
                family.set_father_handle(person.handle)
            else:
                family.set_mother_handle(person.handle)
                
            try:
                EditFamily(self.dbstate, self.uistate, [], family)
            except WindowActiveError:
                pass

    def add_spouse(self, obj):
        family = Family()
        person = self.dbstate.db.get_person_from_handle(self.get_active())

        if not person:
            return
            
        if person.gender == Person.MALE:
            family.set_father_handle(person.handle)
        else:
            family.set_mother_handle(person.handle)
                
        try:
            EditFamily(self.dbstate, self.uistate, [], family)
        except WindowActiveError:
            pass

    def edit_active(self, obj):
        phandle = self.get_active()
        self.edit_person(obj, phandle)

    def add_child_to_fam(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            callback = lambda x: self.callback_add_child(x, handle)
            person = Person()
            name = Name()
            #the editor requires a surname
            name.add_surname(Surname())
            name.set_primary_surname(0)
            family = self.dbstate.db.get_family_from_handle(handle)
            father = self.dbstate.db.get_person_from_handle(
                                        family.get_father_handle())
            if father:
                preset_name(father, name)
            person.set_primary_name(name)
            try:
                EditPerson(self.dbstate, self.uistate, [], person, 
                           callback=callback)
            except WindowActiveError:
                pass

    def callback_add_child(self, person, family_handle):
        ref = ChildRef()
        ref.ref = person.get_handle()
        family = self.dbstate.db.get_family_from_handle(family_handle)
        family.add_child_ref(ref)
        
        with DbTxn(_("Add Child to Family"), self.dbstate.db) as trans:
            #add parentref to child
            person.add_parent_family_handle(family_handle)
            #default relationship is used
            self.dbstate.db.commit_person(person, trans)
            #add child to family
            self.dbstate.db.commit_family(family, trans)

    def sel_child_to_fam(self, obj, event, handle, surname=None):
        if button_activated(event, _LEFT_BUTTON):
            SelectPerson = SelectorFactory('Person')
            family = self.dbstate.db.get_family_from_handle(handle)
            # it only makes sense to skip those who are already in the family
            skip_list = [family.get_father_handle(),
                         family.get_mother_handle()]
            skip_list.extend(x.ref for x in family.get_child_ref_list())

            sel = SelectPerson(self.dbstate, self.uistate, [],
                               _("Select Child"), skip=skip_list)
            person = sel.run()
            
            if person:
                self.callback_add_child(person, handle)

    def select_family(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            SelectFamily = SelectorFactory('Family')

            phandle = self.get_active()
            person = self.dbstate.db.get_person_from_handle(phandle)
            skip = set(person.get_family_handle_list())
            
            dialog = SelectFamily(self.dbstate, self.uistate, skip=skip)
            family = dialog.run()

            if family:
                child = self.dbstate.db.get_person_from_handle(self.get_active())

                self.dbstate.db.add_child_to_family(family, child)

    def select_parents(self, obj):
        SelectFamily = SelectorFactory('Family')

        phandle = self.get_active()
        person = self.dbstate.db.get_person_from_handle(phandle)
        skip = set(person.get_family_handle_list()+
                   person.get_parent_family_handle_list())
            
        dialog = SelectFamily(self.dbstate, self.uistate, skip=skip)
        family = dialog.run()

        if family:
            child = self.dbstate.db.get_person_from_handle(self.get_active())
            
            self.dbstate.db.add_child_to_family(family, child)

    def add_parents(self, obj):
        family = Family()
        person = self.dbstate.db.get_person_from_handle(self.get_active())

        if not person:
            return

        ref = ChildRef()
        ref.ref = person.handle
        family.add_child_ref(ref)
        
        try:
            EditFamily(self.dbstate, self.uistate, [], family)
        except WindowActiveError:
            pass
            
    def add_parent_family(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            family = Family()
            person = self.dbstate.db.get_person_from_handle(self.get_active())

            ref = ChildRef()
            ref.ref = person.handle
            family.add_child_ref(ref)
                
            try:
                EditFamily(self.dbstate, self.uistate, [], family)
            except WindowActiveError:
                pass

    def delete_family(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            self.dbstate.db.remove_parent_from_family(self.get_active(), handle)

    def delete_parent_family(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            self.dbstate.db.remove_child_from_family(self.get_active(), handle)

    def change_to(self, obj, handle):
        self.change_active(handle)

    def reorder_button_press(self, obj, event, handle):
        if button_activated(event, _LEFT_BUTTON):
            self.reorder(obj)
            
    def reorder(self, obj, dumm1=None, dummy2=None):
        if self.get_active():
            try:
                Reorder(self.dbstate, self.uistate, [], self.get_active())
            except WindowActiveError:
                pass

    def config_connect(self):
        """
        Overwriten from  :class:`~gui.views.pageview.PageView method
        This method will be called after the ini file is initialized,
        use it to monitor changes in the ini file
        """
        self._config.connect("preferences.relation-shade",
                          self.shade_update)
        self._config.connect("preferences.releditbtn",
                          self.config_update)
        self._config.connect("preferences.relation-display-theme",
                          self.config_update)
        self._config.connect("preferences.family-siblings",
                          self.config_update)
        self._config.connect("preferences.family-details",
                          self.config_update)
        config.connect("interface.toolbar-on",
                          self.shade_update)

    def config_panel(self, configdialog):
        """
        Function that builds the widget in the configuration dialog
        """
        table = Gtk.Table(n_rows=3, n_columns=2)
        table.set_border_width(12)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        configdialog.add_checkbox(table, 
                _('Use shading'), 
                0, 'preferences.relation-shade')
        configdialog.add_checkbox(table, 
                _('Display edit buttons'), 
                1, 'preferences.releditbtn')
        checkbox = Gtk.CheckButton(label=_('View links as website links'))
        theme = self._config.get('preferences.relation-display-theme')
        checkbox.set_active(theme == 'WEBPAGE')
        checkbox.connect('toggled', self._config_update_theme)
        table.attach(checkbox, 1, 9, 2, 3, yoptions=0)

        return _('Layout'), table

    def content_panel(self, configdialog):
        """
        Function that builds the widget in the configuration dialog
        """
        table = Gtk.Table(n_rows=2, n_columns=2)
        table.set_border_width(12)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        configdialog.add_checkbox(table, 
                _('Show Details'), 
                0, 'preferences.family-details')
        configdialog.add_checkbox(table, 
                _('Show Siblings'), 
                1, 'preferences.family-siblings')

        return _('Content'), table

    def _config_update_theme(self, obj):
        """
        callback from the theme checkbox
        """
        if obj.get_active():
            self.theme = 'WEBPAGE'
            self._config.set('preferences.relation-display-theme', 
                              'WEBPAGE')
        else:
            self.theme = 'CLASSIC'
            self._config.set('preferences.relation-display-theme', 
                              'CLASSIC')

    def _get_configure_page_funcs(self):
        """
        Return a list of functions that create gtk elements to use in the 
        notebook pages of the Configure dialog
        
        :return: list of functions
        """
        return [self.content_panel, self.config_panel]

#-------------------------------------------------------------------------
#
# Function to return if person has children
#
#-------------------------------------------------------------------------
def has_children(db,p):
    """
    Return if a person has children.
    """
    for family_handle in p.get_family_handle_list():
        family = db.get_family_from_handle(family_handle)
        childlist = family.get_child_ref_list()
        if childlist and len(childlist) > 0:
            return True
    return False

def button_activated(event, mouse_button):
    if (event.type == Gdk.EventType.BUTTON_PRESS and
        event.button == mouse_button) or \
       (event.type == Gdk.EventType.KEY_PRESS and
        event.keyval in (_RETURN, _KP_ENTER, _SPACE)):
        return True
    else:
        return False


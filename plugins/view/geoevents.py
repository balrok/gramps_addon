# -*- python -*-
# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2011  Serge Noiraud
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
Geography for events
"""
#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
import os
import sys
import operator
from gi.repository import Gdk
KEY_TAB = Gdk.KEY_Tab
import socket
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger("GeoGraphy.geoevents")

#-------------------------------------------------------------------------
#
# Gramps Modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.lib import EventType
from gramps.gen.config import config
from gramps.gen.datehandler import displayer
from gramps.gen.display.name import displayer as _nd
from gramps.gen.utils.place import conv_lat_lon
from gramps.gui.views.pageview import PageView
from gramps.gui.editors import EditPlace
from gramps.gui.selectors.selectplace import SelectPlace
from gramps.gui.filters.sidebar import EventSidebarFilter
from gramps.gui.views.navigationview import NavigationView
from gramps.gui.views.bookmarks import EventBookmarks
from gramps.plugins.lib.maps.geography import GeoGraphyView

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------

_UI_DEF = '''\
<ui>
<menubar name="MenuBar">
<menu action="GoMenu">
  <placeholder name="CommonGo">
    <menuitem action="Back"/>
    <menuitem action="Forward"/>
    <separator/>
  </placeholder>
</menu>
<menu action="EditMenu">
  <placeholder name="CommonEdit">
    <menuitem action="PrintView"/>
  </placeholder>
</menu>
<menu action="BookMenu">
  <placeholder name="AddEditBook">
    <menuitem action="AddBook"/>
    <menuitem action="EditBook"/>
  </placeholder>
</menu>
</menubar>
<toolbar name="ToolBar">
<placeholder name="CommonNavigation">
  <toolitem action="Back"/>  
  <toolitem action="Forward"/>  
</placeholder>
<placeholder name="CommonEdit">
  <toolitem action="PrintView"/>
</placeholder>
</toolbar>
</ui>
'''

#-------------------------------------------------------------------------
#
# GeoView
#
#-------------------------------------------------------------------------
class GeoEvents(GeoGraphyView):
    """
    The view used to render events map.
    """

    def __init__(self, pdata, dbstate, uistate, nav_group=0):
        GeoGraphyView.__init__(self, _('Events places map'),
                                      pdata, dbstate, uistate, 
                                      EventBookmarks,
                                      nav_group)
        self.dbstate = dbstate
        self.uistate = uistate
        self.place_list = []
        self.place_without_coordinates = []
        self.minlat = self.maxlat = self.minlon = self.maxlon = 0.0
        self.minyear = 9999
        self.maxyear = 0
        self.nbplaces = 0
        self.nbmarkers = 0
        self.sort = []
        self.generic_filter = None
        self.additional_uis.append(self.additional_ui())
        self.no_show_places_in_status_bar = False

    def get_title(self):
        """
        Used to set the titlebar in the configuration window.
        """
        return _('GeoEvents')

    def get_stock(self):
        """
        Returns the name of the stock icon to use for the display.
        This assumes that this icon has already been registered 
        as a stock icon.
        """
        return 'geo-show-events'
    
    def get_viewtype_stock(self):
        """Type of view in category
        """
        return 'geo-show-events'

    def additional_ui(self):
        """
        Specifies the UIManager XML code that defines the menus and buttons
        associated with the interface.
        """
        return _UI_DEF

    def navigation_type(self):
        """
        Indicates the navigation type. Navigation type can be the string
        name of any of the primary objects.
        """
        return 'Event'

    def goto_handle(self, handle=None):
        """
        Rebuild the tree with the given events handle as the root.
        """
        self.places_found = []
        self.build_tree()

    def show_all_events(self, menu, event, lat, lon):
        """
        Ask to show all events.
        """
        self._createmap(None)

    def build_tree(self):
        """
        This is called by the parent class when the view becomes visible. Since
        all handling of visibility is now in rebuild_trees, see that for more
        information.
        """
        active = self.uistate.get_active('Event')
        if active:
            self._createmap(active)
        else:
            self._createmap(None)

    def _createmap_for_one_event(self,event):
        """
        Create all markers for each people's event in the database which has 
        a lat/lon.
        """
        dbstate = self.dbstate
        if self.nbplaces >= self._config.get("geography.max_places"):
            return
        descr = descr2 = ""
        if event:
            place_handle = event.get_place_handle()
            eventyear = event.get_date_object().to_calendar(self.cal).get_year()
        else:
            place_handle = None
        if place_handle:
            place = dbstate.db.get_place_from_handle(place_handle)
            if place:
                descr1 = place.get_title()
                longitude = place.get_longitude()
                latitude = place.get_latitude()
                latitude, longitude = conv_lat_lon(latitude, longitude, "D.D8")
                # place.get_longitude and place.get_latitude return
                # one string. We have coordinates when the two values
                # contains non null string.
                if ( longitude and latitude ):
                    person_list = [
                        dbstate.db.get_person_from_handle(ref_handle)
                        for (ref_type, ref_handle) in
                            dbstate.db.find_backlink_handles(event.handle)
                                if ref_type == 'Person'
                                  ]
                    if person_list:
                        for person in person_list:
                            if descr2 == "":
                                descr2 = ("%s") % _nd.display(person)
                            else:
                                descr2 = ("%s - %s") % ( descr2,
                                                         _nd.display(person))
                    else:
                        # family list ?
                        family_list = [
                            dbstate.db.get_family_from_handle(ref_handle)
                            for (ref_type, ref_handle) in
                                dbstate.db.find_backlink_handles(event.handle)
                                    if ref_type == 'Family'
                                      ]
                        if family_list:
                            for family in family_list:
                                hdle = family.get_father_handle()
                                father = dbstate.db.get_person_from_handle(hdle)
                                hdle = family.get_mother_handle()
                                mother = dbstate.db.get_person_from_handle(hdle)
                                descr2 = ("%(father)s - %(mother)s") % {
                                               'father': _nd.display(father) if father is not None else "?",
                                               'mother': _nd.display(mother) if mother is not None else "?"
                                              }
                        else:
                            descr2 = _("incomplete or unreferenced event ?")
                    self._append_to_places_list(descr1, None,
                                                None,
                                                latitude, longitude,
                                                descr2, 
                                                eventyear,
                                                event.get_type(),
                                                None, # person.gramps_id
                                                place.gramps_id,
                                                event.gramps_id,
                                                None
                                                )
                else:
                    descr = place.get_title()
                    self._append_to_places_without_coord(
                         place.gramps_id, descr)

    def _createmap(self,obj):
        """
        Create all markers for each people's event in the database which has 
        a lat/lon.
        """
        dbstate = self.dbstate
        self.place_list = []
        self.place_without_coordinates = []
        self.minlat = self.maxlat = self.minlon = self.maxlon = 0.0
        self.minyear = 9999
        self.maxyear = 0
        latitude = ""
        longitude = ""
        self.without = 0
        self.cal = config.get('preferences.calendar-format-report')
        self.no_show_places_in_status_bar = False

        if self.generic_filter:
            events_list = self.generic_filter.apply(dbstate.db)
            for event_handle in events_list:
                event = dbstate.db.get_event_from_handle(event_handle)
                self._createmap_for_one_event(event)
        else:
            if obj is None:
                events_handle = dbstate.db.get_event_handles()
                for event_hdl in events_handle:
                    event = dbstate.db.get_event_from_handle(event_hdl)
                    self._createmap_for_one_event(event)
            else:
                event = dbstate.db.get_event_from_handle(obj)
                self._createmap_for_one_event(event)
        self.sort = sorted(self.place_list,
                           key=operator.itemgetter(3, 4, 6)
                          )
        if self.nbmarkers > 500 : # performance issue. Is it the good value ?
            self.no_show_places_in_status_bar = True
        self._create_markers()

    def bubble_message(self, event, lat, lon, marks):
        self.menu = Gtk.Menu()
        menu = self.menu
        menu.set_title("events")
        message = ""
        oldplace = ""
        prevmark = None
        for mark in marks:
            if message != "":
                add_item = Gtk.MenuItem(label=message)
                add_item.show()
                menu.append(add_item)
                self.itemoption = Gtk.Menu()
                itemoption = self.itemoption
                itemoption.set_title(message)
                itemoption.show()
                add_item.set_submenu(itemoption)
                modify = Gtk.MenuItem(label=_("Edit Event"))
                modify.show()
                modify.connect("activate", self.edit_event,
                               event, lat, lon, prevmark)
                itemoption.append(modify)
                center = Gtk.MenuItem(label=_("Center on this place"))
                center.show()
                center.connect("activate", self.center_here,
                               event, lat, lon, prevmark)
                itemoption.append(center)
                evt = self.dbstate.db.get_event_from_gramps_id(mark[10])
                hdle = evt.get_handle()
                bookm = Gtk.MenuItem(label=_("Bookmark this event"))
                bookm.show()
                bookm.connect("activate", self.add_bookmark, hdle)
                itemoption.append(bookm)
            if mark[0] != oldplace:
                message = "%s :" % mark[0]
                self.add_place_bubble_message(event, lat, lon,
                                              marks, menu, message, mark)
                oldplace = mark[0]
            evt = self.dbstate.db.get_event_from_gramps_id(mark[10])
            # format the date as described in preferences.
            date = displayer.display(evt.get_date_object())
            message = "(%s) %s : %s" % (date, EventType( mark[7] ), mark[5] )
            prevmark = mark
        add_item = Gtk.MenuItem(label=message)
        add_item.show()
        menu.append(add_item)
        self.itemoption = Gtk.Menu()
        itemoption = self.itemoption
        itemoption.set_title(message)
        itemoption.show()
        add_item.set_submenu(itemoption)
        modify = Gtk.MenuItem(label=_("Edit Event"))
        modify.show()
        modify.connect("activate", self.edit_event, event, lat, lon, prevmark)
        itemoption.append(modify)
        center = Gtk.MenuItem(label=_("Center on this place"))
        center.show()
        center.connect("activate", self.center_here, event, lat, lon, prevmark)
        itemoption.append(center)
        evt = self.dbstate.db.get_event_from_gramps_id(mark[10])
        hdle = evt.get_handle()
        bookm = Gtk.MenuItem(label=_("Bookmark this event"))
        bookm.show()
        bookm.connect("activate", self.add_bookmark, hdle)
        itemoption.append(bookm)
        menu.popup(None, None,
                   lambda menu, data: (event.get_root_coords()[0],
                                       event.get_root_coords()[1], True),
                   None, event.button, event.time)
        return 1

    def add_specific_menu(self, menu, event, lat, lon): 
        """ 
        Add specific entry to the navigation menu.
        """ 
        add_item = Gtk.MenuItem()
        add_item.show()
        menu.append(add_item)
        add_item = Gtk.MenuItem(label=_("Show all events"))
        add_item.connect("activate", self.show_all_events, event, lat , lon)
        add_item.show()
        menu.append(add_item)
        add_item = Gtk.MenuItem(label=_("Centering on Place"))
        add_item.show()
        menu.append(add_item)
        self.itemoption = Gtk.Menu()
        itemoption = self.itemoption
        itemoption.set_title(_("Centering on Place"))
        itemoption.show()
        add_item.set_submenu(itemoption)
        oldplace = ""
        for mark in self.sort:
            if mark[0] != oldplace:
                oldplace = mark[0]
                modify = Gtk.MenuItem(label=mark[0])
                modify.show()
                modify.connect("activate", self.goto_place, float(mark[3]), float(mark[4]))
                itemoption.append(modify)

    def goto_place(self, obj, lat, lon):
        """
        Center the map on latitude, longitude.
        """
        self.set_center(None, None, lat, lon)

    def get_default_gramplets(self):
        """
        Define the default gramplets for the sidebar and bottombar.
        """
        return (("Event Filter",),
                ())

# -*- python -*-
# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2011-2012       Serge Noiraud
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
import os
from gi.repository import GObject

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import time
import logging
_LOG = logging.getLogger("maps.osmgps")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import Gdk

#-------------------------------------------------------------------------
#
# Gramps Modules
#
#-------------------------------------------------------------------------
from gramps.plugins.lib.maps import constants
from .dummylayer import DummyLayer
from .dummynogps import DummyMapNoGpsPoint
from .selectionlayer import SelectionLayer
from .lifewaylayer import LifeWayLayer
from .markerlayer import MarkerLayer
from .datelayer import DateLayer
from .messagelayer import MessageLayer
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
from gramps.gen.config import config
from gramps.gui.dialog import ErrorDialog
from gramps.gen.constfunc import get_env_var

#-------------------------------------------------------------------------
#
# OsmGps
#
#-------------------------------------------------------------------------

try:
    from gi.repository import OsmGpsMap as osmgpsmap
except:
    raise

class OsmGps():
    def __init__(self):
        """
        Initialize the map
        """
        self.vbox = None
        self.cross_map = None
        self.osm = None
        self.show_tooltips = True
        self.zone_selection = False
        self.selection_layer = None
        self.lifeway_layer = None
        self.marker_layer = None
        self.date_layer = None
        self.message_layer = None
        self.context_id = 0
        self.begin_selection = None
        self.end_selection = None
        self.current_map = None
        self.places_found = None

    def build_widget(self):
        """
        create the vbox 
        """
        self.vbox = Gtk.VBox(homogeneous=False, spacing=0)
        cache_path = config.get('geography.path')
        if not os.path.isdir(cache_path):
            try:
                os.makedirs(cache_path, 0o755) # create dir like mkdir -p
            except:
                ErrorDialog(_("Can't create tiles cache directory %s") %
                             cache_path )
                return self.vbox

        self.change_map(None, config.get("geography.map_service"))
        return self.vbox

    def change_map(self, obj, map_type):
        """
        Change the current map
        """
        if obj is not None:
            self.osm.layer_remove_all()
            self.osm.image_remove_all()
            self.vbox.remove(self.osm)
            self.osm.destroy()
        tiles_path = os.path.join(config.get('geography.path'),
                                  constants.tiles_path[map_type])
        if not os.path.isdir(tiles_path):
            try:
                os.makedirs(tiles_path, 0o755) # create dir like mkdir -p
            except:
                ErrorDialog(_("Can't create tiles cache directory for '%s'.") %
                             constants.map_title[map_type])
        config.set("geography.map_service", map_type)
        self.current_map = map_type
        http_proxy = get_env_var('http_proxy')
        if 0:
            self.osm = DummyMapNoGpsPoint()
        else:
            if http_proxy:
                self.osm = osmgpsmap.Map(tile_cache=tiles_path,
                                         proxy_uri=http_proxy,
                                         map_source=constants.map_type[map_type])
            else:
                self.osm = osmgpsmap.Map(tile_cache=tiles_path,
                                         map_source=constants.map_type[map_type])
        self.osm.props.tile_cache = osmgpsmap.MAP_CACHE_AUTO
        current_map = osmgpsmap.MapOsd( show_dpad=False, show_zoom=True)
        self.end_selection = None
        self.osm.layer_add(current_map)
        self.osm.layer_add(DummyLayer())
        self.selection_layer = self.add_selection_layer()
        self.lifeway_layer = self.add_lifeway_layer()
        self.marker_layer = self.add_marker_layer()
        self.date_layer = self.add_date_layer()
        self.message_layer = self.add_message_layer()
        self.cross_map = osmgpsmap.MapOsd( show_crosshair=False)
        self.set_crosshair(config.get("geography.show_cross"))
        self.osm.set_center_and_zoom(config.get("geography.center-lat"),
                                     config.get("geography.center-lon"),
                                     config.get("geography.zoom") )

        self.osm.connect('button_release_event', self.map_clicked)
        self.osm.connect('button_press_event', self.map_clicked)
        self.osm.connect("motion-notify-event", self.motion_event)
        self.osm.connect('changed', self.zoom_changed)
        self.osm.show()
        self.vbox.pack_start(self.osm, True, True, 0)
        self.goto_handle(handle=None)

    def add_selection_layer(self):
        """
        add the selection layer
        """
        selection_layer = SelectionLayer()
        self.osm.layer_add(selection_layer)
        return selection_layer

    def get_selection_layer(self):
        """
        get the selection layer
        """
        return self.selection_layer

    def add_message_layer(self):
        """
        add the message layer to the map
        """
        message_layer = MessageLayer()
        self.osm.layer_add(message_layer)
        return message_layer

    def get_message_layer(self):
        """
        get the message layer
        """
        return self.message_layer

    def add_date_layer(self):
        """
        add the date layer to the map
        """
        date_layer = DateLayer()
        self.osm.layer_add(date_layer)
        return date_layer

    def get_date_layer(self):
        """
        get the date layer
        """
        return self.date_layer

    def add_marker_layer(self):
        """
        add the marker layer
        """
        marker_layer = MarkerLayer()
        self.osm.layer_add(marker_layer)
        return marker_layer

    def get_marker_layer(self):
        """
        get the marker layer
        """
        return self.marker_layer

    def add_lifeway_layer(self):
        """
        add the track or life ways layer
        """
        lifeway_layer = LifeWayLayer()
        self.osm.layer_add(lifeway_layer)
        return lifeway_layer

    def get_lifeway_layer(self):
        """
        get the track or life ways layer
        """
        return self.lifeway_layer

    def remove_layer(self, layer):
        """
        remove the specified layer
        """
        self.osm.layer_remove(layer)

    def zoom_changed(self, zoom):
        """
        save the zoom and the position
        """
        config.set("geography.zoom", self.osm.props.zoom)
        self.save_center(self.osm.props.latitude, self.osm.props.longitude)

    def motion_event(self, osmmap, event):
        """
        Moving during selection
        """
        current = osmmap.convert_screen_to_geographic(int(event.x), int(event.y))
        lat, lon = current.get_degrees()
        if self.zone_selection:
            # We draw a rectangle to show the selected region.
            layer = self.get_selection_layer()
            if layer:
                self.osm.layer_remove(layer)
            self.selection_layer = self.add_selection_layer()
            if self.end_selection == None:
                self.selection_layer.add_rectangle(self.begin_selection,
                                                   current)
            else:
                self.selection_layer.add_rectangle(self.begin_selection,
                                                   self.end_selection)
        else:
            places = self.is_there_a_place_here(lat, lon)
            mess = ""
            for plc in places:
                if mess != "":
                    mess += " || "
                mess += plc[0]
            self.uistate.status.pop(self.context_id)
            self.context_id = self.uistate.status.push(1, mess)

    def save_center(self, lat, lon):
        """
        Save the longitude and lontitude in case we switch between maps.
        """
        _LOG.debug("save_center : %s,%s" % (lat, lon) )
        if ( -90.0 < lat < +90.0 ) and ( -180.0 < lon < +180.0 ):
            config.set("geography.center-lat", lat)
            config.set("geography.center-lon", lon)
        else:
            _LOG.debug("save_center : new coordinates : %s,%s" % (lat, lon) )
            _LOG.debug("save_center : old coordinates : %s,%s" % (lat, lon) )
            # osmgpsmap bug ? reset to prior values to avoid osmgpsmap problems.
            self.osm.set_center_and_zoom(config.get("geography.center-lat"),
                                         config.get("geography.center-lon"),
                                         config.get("geography.zoom") )

    def activate_selection_zoom(self, osm, event):
        """
        Zoom when in zone selection
        """
        if self.end_selection is not None:
            self._autozoom()
        return True

    def map_clicked(self, osm, event):
        """
        Someone click on the map. Look at if we have a marker.
        mouse button 1 : zone selection or marker selection
        mouse button 2 : begin zone selection
        mouse button 3 : call the menu
        """
        lat, lon = self.osm.get_event_location(event).get_degrees()
        current = osm.convert_screen_to_geographic(int(event.x), int(event.y))
        lat, lon = current.get_degrees()
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            if self.end_selection is not None:
                self.activate_selection_zoom(osm, event)
                self.end_selection = None
            else:
                # do we click on a marker ?
                self.is_there_a_marker_here(event, lat, lon)
        elif event.button == 2 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.begin_selection = current
            self.end_selection = None
            self.zone_selection = True
        elif event.button == 2 and event.type == Gdk.EventType.BUTTON_RELEASE:
            self.end_selection = current
            self.zone_selection = False
        elif event.button == 3 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.build_nav_menu(osm, event, lat, lon)
        else:
            self.save_center(lat, lon)

    def is_there_a_place_here(self, lat, lon):
        """
        Is there a place at this position ?
        If too many places, this function is very time consuming
        """
        mark_selected = []
        if self.no_show_places_in_status_bar:
            return mark_selected
        oldplace = ""
        _LOG.debug("%s" % time.strftime("start is_there_a_place_here : "
                   "%a %d %b %Y %H:%M:%S", time.gmtime()))
        for mark in self.places_found:
            # as we are not precise with our hand, reduce the precision
            # depending on the zoom.
            if mark[0] != oldplace:
                oldplace = mark[0]
                precision = {
                              1 : '%3.0f', 2 : '%3.1f', 3 : '%3.1f',
                              4 : '%3.1f', 5 : '%3.2f', 6 : '%3.2f',
                              7 : '%3.2f', 8 : '%3.3f', 9 : '%3.3f',
                             10 : '%3.3f', 11 : '%3.3f', 12 : '%3.3f',
                             13 : '%3.3f', 14 : '%3.4f', 15 : '%3.4f',
                             16 : '%3.4f', 17 : '%3.4f', 18 : '%3.4f'
                             }.get(config.get("geography.zoom"), '%3.1f')
                shift = {
                          1 : 5.0, 2 : 5.0, 3 : 3.0,
                          4 : 1.0, 5 : 0.5, 6 : 0.3, 7 : 0.15,
                          8 : 0.06, 9 : 0.03, 10 : 0.015,
                         11 : 0.005, 12 : 0.003, 13 : 0.001,
                         14 : 0.0005, 15 : 0.0003, 16 : 0.0001,
                         17 : 0.0001, 18 : 0.0001
                         }.get(config.get("geography.zoom"), 5.0)
                latp  = precision % lat
                lonp  = precision % lon
                mlatp = precision % float(mark[1])
                mlonp = precision % float(mark[2])
                latok = lonok = False
                if (float(mlatp) >= (float(latp) - shift) ) and \
                   (float(mlatp) <= (float(latp) + shift) ):
                    latok = True
                if (float(mlonp) >= (float(lonp) - shift) ) and \
                   (float(mlonp) <= (float(lonp) + shift) ):
                    lonok = True
                if latok and lonok:
                    mark_selected.append(mark)
        _LOG.debug("%s" % time.strftime("  end is_there_a_place_here : "
                   "%a %d %b %Y %H:%M:%S", time.gmtime()))
        return mark_selected

    def build_nav_menu(self, osm, event, lat, lon):
        """
        Must be implemented in the caller class
        """
        raise NotImplementedError

    def is_there_a_marker_here(self, event, lat, lon):
        """
        Must be implemented in the caller class
        """
        raise NotImplementedError

    def set_crosshair(self, active):
        """
        Show or hide the crosshair ?
        """
        if active:
            self.cross_map = osmgpsmap.MapOsd( show_crosshair=True)
            self.osm.layer_add( self.cross_map )
            # The two following are to force the map to update
            self.osm.zoom_in()
            self.osm.zoom_out()
        else:
            self.osm.layer_remove(self.cross_map)

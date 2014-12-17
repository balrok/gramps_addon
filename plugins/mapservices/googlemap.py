#
# Gramps - a GTK+/GNOME based genealogy program
#
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
Google Maps map service plugin. Open place in maps.google.com
"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.plugins.lib.libmapservice import MapService
from gramps.gen.utils.location import get_main_location
from gramps.gen.lib import PlaceType

class GoogleMapService(MapService):
    """Map  service using http://maps.google.com"""
    def __init__(self):
        MapService.__init__(self)
    
    def calc_url(self):
        """ Determine the url to use on maps.google.com
            Logic: use lat lon if present
                   otherwise use city and country if present
                   otherwise use description of the place
        """
        place = self._get_first_place()[0]
        latitude, longitude = self._lat_lon(place)
        if longitude and latitude:
            self.url = "http://maps.google.com/maps/mm?sll=%s,%s&z=15" % (latitude, 
                                                               longitude)
            return
        
        location = get_main_location(self.database, place)
        city = location.get(PlaceType.CITY)
        country = location.get(PlaceType.COUNTRY)
        if city and country:
            self.url = "http://maps.google.com/maps?q=%s,%s" % (city, country)
            return
        
        titledescr = place.get_title()
        self.url = "http://maps.google.com/maps?q=%s" % \
                                            '+'.join(titledescr.split())

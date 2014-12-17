#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
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
Package providing filtering framework for GRAMPS.
"""

#SystemFilters = None
CustomFilters = None

from ..const import CUSTOM_FILTERS
from ._filterlist import FilterList
from ._genericfilter import GenericFilter, GenericFilterFactory
from ._paramfilter import ParamFilter
from ._searchfilter import SearchFilter, ExactSearchFilter

#def reload_system_filters():
    #global SystemFilters
    #SystemFilters = FilterList(SYSTEM_FILTERS)
    #SystemFilters.load()
    
def reload_custom_filters():
    global CustomFilters
    CustomFilters = FilterList(CUSTOM_FILTERS)
    CustomFilters.load()
    
#if not SystemFilters:
    #reload_system_filters()

if not CustomFilters:
    reload_custom_filters()

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2010      Nick Hall
# Copyright (C) 2013      Doug Blank <doug.blank@gmail.com>
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
Table Object class for Gramps.
"""

#-------------------------------------------------------------------------
#
# standard python modules
#
#-------------------------------------------------------------------------
from __future__ import unicode_literals
import time

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .baseobj import BaseObject
from ..constfunc import cuni

#-------------------------------------------------------------------------
#
# Localized constants
#
#-------------------------------------------------------------------------
from ..const import GRAMPS_LOCALE as glocale
CODESET = glocale.encoding
#-------------------------------------------------------------------------
#
# Table Object class
#
#-------------------------------------------------------------------------
class TableObject(BaseObject):
    """
    The TableObject is the base class for all objects that are stored in a
    seperate database table.  Each object has a database handle and a last
    changed time.  The database handle is used as the unique key for a record
    in the database.  This is not the same as the Gramps ID, which is a user
    visible identifier for a record.
    
    It is the base class for the BasicPrimaryObject class and Tag class.    
    """
    
    def __init__(self, source=None):
        """
        Initialize a TableObject. 
        
        If source is None, the handle is assigned as an empty string.
        If source is not None, then the handle is initialized from the value in
        the source object.

        :param source: Object used to initialize the new object
        :type source: TableObject
        """
        if source:
            self.handle = source.handle
            self.change = source.change
        else:
            self.handle = None
            self.change = 0

    def get_change_time(self):
        """
        Return the time that the data was last changed. 
        
        The value in the format returned by the :meth:`time.time()` command.
           
        :returns: Time that the data was last changed. The value in the format 
                  returned by the :meth:`time.time()` command.
        :rtype: int
        """
        return self.change

    def set_change_time(self, change):
        """
        Modify the time that the data was last changed. 
        
        The value must be in the format returned by the :meth:`time.time()`
        command.

        :param change: new time
        :type change: int in format as :meth:`time.time()` command
        """
        self.change = change

    def get_change_display(self):
        """
        Return the string representation of the last change time.

        :returns: string representation of the last change time.
        :rtype: str
        
        """
        if self.change:
            return cuni(time.strftime('%x %X', time.localtime(self.change)),
                           CODESET)
        else:
            return ''

    def set_handle(self, handle):
        """
        Set the database handle for the primary object.

        :param handle: object database handle
        :type handle: str
        """
        self.handle = handle

    def get_handle(self):
        """
        Return the database handle for the primary object.

        :returns: database handle associated with the object
        :rtype: str
        """
        return self.handle

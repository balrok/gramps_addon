#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2002       Gary Shao
# Copyright (C) 2007       Brian G. Matherly
# Copyright (C) 2009       Benny Malengier
# Copyright (C) 2009       Gary Burton
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
Provide base interface to text based documents. Specific document
interfaces should be derived from the core classes.
"""

#-------------------------------------------------------------------------
#
# standard python modules
#
#-------------------------------------------------------------------------

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from .stylesheet import StyleSheet

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
log = logging.getLogger(".basedoc")

#------------------------------------------------------------------------
#
# BaseDoc
#
#------------------------------------------------------------------------
class BaseDoc(object):
    """
    Base class for document generators. Different output formats,
    such as OpenOffice, AbiWord, and LaTeX are derived from this base
    class, providing a common interface to all document generators.
    """
    def __init__(self, styles, paper_style):
        """
        Create a BaseDoc instance, which provides a document generation
        interface. This class should never be instantiated directly, but
        only through a derived class.

        :param styles: :class:`.StyleSheet` containing the styles used.
        :param paper_style: :class:`.PaperStyle` instance containing information
                            about the paper. If set to None, then the document
                            is not a page oriented document (e.g. HTML)
        """
        self.paper = paper_style
        self._style_sheet = styles
        self._creator = ""
        self.init_called = False

    def init(self):
        self.init_called = True

    def set_creator(self, name):
        "Set the owner name"
        self._creator = name
        
    def get_creator(self):
        "Return the owner name"
        return self._creator
        
    def get_style_sheet(self):
        """
        Return the :class:`.StyleSheet` of the document.
        """
        return StyleSheet(self._style_sheet)
    
    def set_style_sheet(self, style_sheet):
        """
        Set the :class:`.StyleSheet` of the document.

        :param style_sheet: The new style sheet for the document
        :type  style_sheet: :class:`.StyleSheet`
        """
        self._style_sheet = StyleSheet(style_sheet)

    def open(self, filename):
        """
        Opens the file so that it can be generated.

        :param filename: path name of the file to create
        """
        raise NotImplementedError

    def close(self):
        "Closes the generated file."
        raise NotImplementedError

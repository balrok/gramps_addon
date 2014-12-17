#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2003-2006  Donald N. Allingham
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

"""Handling of selection dialog for selecting notes
"""

#-------------------------------------------------------------------------
#
# Python Modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# GRAMPS Modules
#
#-------------------------------------------------------------------------
from ..views.treemodels import NoteModel
from .baseselector import BaseSelector

#-------------------------------------------------------------------------
#
# SelectNote
#
#-------------------------------------------------------------------------
class SelectNote(BaseSelector):
    """ Class that handles the selection of a note
    """

    def _local_init(self):
        """
        Perform local initialisation for this class
        """
        self.width_key = 'interface.note-sel-width'
        self.height_key = 'interface.note-sel-height'

    def get_window_title(self):
        return _("Select Note")
        
    def get_model_class(self):
        return NoteModel

    def get_column_titles(self):
        return [
            (_('Preview'), 350, BaseSelector.TEXT, 0),
            (_('ID'),      75,  BaseSelector.TEXT, 1),
            (_('Type'),    100, BaseSelector.TEXT, 2),
            (_('Tags'),    100, BaseSelector.TEXT, 4),
            (_('Last Change'), 150, BaseSelector.TEXT, 5),
            ]
            
    def get_from_handle_func(self):
        return self.db.get_note_from_handle

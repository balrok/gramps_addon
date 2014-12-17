#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
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
# Python classes
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gi.repository import GObject, GLib

#-------------------------------------------------------------------------
#
# GRAMPS classes
#
#-------------------------------------------------------------------------
from gramps.gen.lib import Attribute
from gramps.gen.errors import WindowActiveError
from ...ddtargets import DdTargets
from .attrmodel import AttrModel
from .embeddedlist import EmbeddedList, TEXT_COL, MARKUP_COL, ICON_COL

#-------------------------------------------------------------------------
#
# 
#
#-------------------------------------------------------------------------
class AttrEmbedList(EmbeddedList):

    _HANDLE_COL = 3
    _DND_TYPE   = DdTargets.ATTRIBUTE

    _MSG = {
        'add'   : _('Create and add a new attribute'),
        'del'   : _('Remove the existing attribute'),
        'edit'  : _('Edit the selected attribute'),
        'up'    : _('Move the selected attribute upwards'),
        'down'  : _('Move the selected attribute downwards'),
    }

    #index = column in model. Value =
    #  (name, sortcol in model, width, markup/text, weigth_col
    _column_names = [
        (_('Type'), 0, 250, TEXT_COL, -1, None),
        (_('Value'), 1, 200, TEXT_COL, -1, None),
        (_('Private'), 2, 30, ICON_COL, -1, 'gramps-lock')
        ]
    
    def __init__(self, dbstate, uistate, track, data):
        """
        Initialize the displaytab. The dbstate and uistate is needed
        track is the list of parent windows
        data is an attribute_list (as obtained by AttributeBase) to display and
            edit
        """
        self.data = data
        EmbeddedList.__init__(self, dbstate, uistate, track, _('_Attributes'), 
                              AttrModel, move_buttons=True)

    def get_editor(self):
        from .. import EditAttribute
        return EditAttribute

    def get_user_values(self):
        return self.dbstate.db.get_person_attribute_types()        

    def get_icon_name(self):
        return 'gramps-attribute'
    
    def get_data(self):
        return self.data

    def column_order(self):
        return ((1, 2), (1, 0), (1, 1))

    def add_button_clicked(self, obj):
        pname = ''
        attr = Attribute()
        try:
            self.get_editor()(
                self.dbstate, self.uistate, self.track, attr, 
                pname, self.get_user_values(), self.add_callback)
        except WindowActiveError:
            pass

    def add_callback(self, name):
        data = self.get_data()
        data.append(name)
        self.changed = True
        self.rebuild()
        GLib.idle_add(self.tree.scroll_to_cell, len(data)-1)

    def edit_button_clicked(self, obj):
        attr = self.get_selected()
        if attr:
            pname = ''
            try:
                self.get_editor()(
                    self.dbstate, self.uistate, self.track, attr, 
                    pname, self.get_user_values(), self.edit_callback)
            except WindowActiveError:
                pass

    def edit_callback(self, name):
        self.changed = True
        self.rebuild()

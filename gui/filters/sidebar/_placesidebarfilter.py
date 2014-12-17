#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
# Copyright (C) 2008       Gary Burton
# Copyright (C) 2010       Nick Hall
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
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# gtk
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------------------------------
from ... import widgets
from .. import build_filter_model
from . import SidebarFilter
from gramps.gen.constfunc import cuni
from gramps.gen.filters import GenericFilterFactory, rules
from gramps.gen.filters.rules.place import (RegExpIdOf, HasPlace, HasTag,
                                            HasNoteRegexp, MatchesFilter)

GenericPlaceFilter = GenericFilterFactory('Place')
#-------------------------------------------------------------------------
#
# PlaceSidebarFilter class
#
#-------------------------------------------------------------------------
class PlaceSidebarFilter(SidebarFilter):

    def __init__(self, dbstate, uistate, clicked):
        self.clicked_func = clicked

        self.filter_id = widgets.BasicEntry()
        self.filter_title = widgets.BasicEntry()
        self.filter_street = widgets.BasicEntry()
        self.filter_locality = widgets.BasicEntry()
        self.filter_city = widgets.BasicEntry()
        self.filter_county = widgets.BasicEntry()
        self.filter_state = widgets.BasicEntry()
        self.filter_country = widgets.BasicEntry()
        self.filter_zip = widgets.BasicEntry()
        self.filter_parish = widgets.BasicEntry()
        self.filter_note = widgets.BasicEntry()
        
        self.filter_regex = Gtk.CheckButton(label=_('Use regular expressions'))
        self.tag = Gtk.ComboBox()
        self.generic = Gtk.ComboBox()

        SidebarFilter.__init__(self, dbstate, uistate, "Place")

    def create_widget(self):
        cell = Gtk.CellRendererText()
        cell.set_property('width', self._FILTER_WIDTH)
        cell.set_property('ellipsize', self._FILTER_ELLIPSIZE)
        self.generic.pack_start(cell, True)
        self.generic.add_attribute(cell, 'text', 0)
        self.on_filters_changed('Place')

        cell = Gtk.CellRendererText()
        cell.set_property('width', self._FILTER_WIDTH)
        cell.set_property('ellipsize', self._FILTER_ELLIPSIZE)
        self.tag.pack_start(cell, True)
        self.tag.add_attribute(cell, 'text', 0)

        self.add_text_entry(_('ID'), self.filter_id)
        self.add_text_entry(_('Place Name'), self.filter_title)
        self.add_text_entry(_('Street'), self.filter_street)
        self.add_text_entry(_('Locality'), self.filter_locality)
        self.add_text_entry(_('City'), self.filter_city)
        self.add_text_entry(_('County'), self.filter_county)
        self.add_text_entry(_('State'), self.filter_state)
        self.add_text_entry(_('Country'), self.filter_country)
        self.add_text_entry(_('ZIP/Postal code'), self.filter_zip)
        self.add_text_entry(_('Church parish'), self.filter_parish)
        self.add_text_entry(_('Note'), self.filter_note)
        self.add_entry(_('Tag'), self.tag)
        self.add_filter_entry(_('Custom filter'), self.generic)
        self.add_regex_entry(self.filter_regex)

    def clear(self, obj):
        self.filter_id.set_text('')
        self.filter_title.set_text('')
        self.filter_street.set_text('')
        self.filter_locality.set_text('')
        self.filter_city.set_text('')
        self.filter_county.set_text('')
        self.filter_state.set_text('')
        self.filter_country.set_text('')
        self.filter_zip.set_text('')
        self.filter_parish.set_text('')
        self.filter_note.set_text('')
        self.tag.set_active(0)
        self.generic.set_active(0)

    def get_filter(self):
        gid = cuni(self.filter_id.get_text()).strip()
        title = cuni(self.filter_title.get_text()).strip()
        street = cuni(self.filter_street.get_text()).strip()
        locality = cuni(self.filter_locality.get_text()).strip()
        city = cuni(self.filter_city.get_text()).strip()
        county = cuni(self.filter_county.get_text()).strip()
        state = cuni(self.filter_state.get_text()).strip()
        country = cuni(self.filter_country.get_text()).strip()
        zipc = cuni(self.filter_zip.get_text()).strip()
        parish = cuni(self.filter_parish.get_text()).strip()
        note = cuni(self.filter_note.get_text()).strip()
        regex = self.filter_regex.get_active()
        tag = self.tag.get_active() > 0
        gen = self.generic.get_active() > 0

        empty = not (gid or title or street or locality or city or county or
                     state or country or zipc or parish or note or regex or tag
                     or gen)
        if empty:
            generic_filter = None
        else:
            generic_filter = GenericPlaceFilter()
            if gid:
                rule = RegExpIdOf([gid], use_regex=regex)
                generic_filter.add_rule(rule)

            rule = HasPlace([title, street, locality, city, county, state,
                             country, zipc, parish], use_regex=regex)
            generic_filter.add_rule(rule)
                
            if note:
                rule = HasNoteRegexp([note], use_regex=regex)
                generic_filter.add_rule(rule)

            # check the Tag
            if tag:
                model = self.tag.get_model()
                node = self.tag.get_active_iter()
                attr = model.get_value(node, 0)
                rule = HasTag([attr])
                generic_filter.add_rule(rule)

            if self.generic.get_active() != 0:
                model = self.generic.get_model()
                node = self.generic.get_active_iter()
                obj = cuni(model.get_value(node, 0))
                rule = MatchesFilter([obj])
                generic_filter.add_rule(rule)

        return generic_filter

    def on_filters_changed(self, name_space):
        if name_space == 'Place':
            all_filter = GenericPlaceFilter()
            all_filter.set_name(_("None"))
            all_filter.add_rule(rules.place.AllPlaces([]))
            self.generic.set_model(build_filter_model('Place', [all_filter]))
            self.generic.set_active(0)

    def on_tags_changed(self, tag_list):
        """
        Update the list of tags in the tag filter.
        """
        model = Gtk.ListStore(str)
        model.append(('',))
        for tag_name in tag_list:
            model.append((tag_name,))
        self.tag.set_model(model)
        self.tag.set_active(0)

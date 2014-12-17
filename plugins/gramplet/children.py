# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2011 Nick Hall
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

from gramps.gui.editors import EditPerson
from gramps.gui.listmodel import ListModel, NOSORT
from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback
from gramps.gen.datehandler import get_date
from gramps.gen.errors import WindowActiveError
from gi.repository import Gtk

class Children(Gramplet):
    """
    Displays the children of a person or family.
    """
    def init(self):
        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()
        self.uistate.connect('nameformat-changed', self.update)

    def get_date_place(self, event):
        """
        Return the date and place of the given event.
        """
        event_date = ''
        event_place = ''
        event_sort = '%012d' % 0
        if event:
            event_date = get_date(event)
            event_sort = '%012d' % event.get_date_object().get_sort_value()
            handle = event.get_place_handle()
            if handle:
                place = self.dbstate.db.get_place_from_handle(handle)
                event_place = place.get_title()
        return (event_date, event_sort, event_place)

    def edit_person(self, treeview):
        """
        Edit the selected child.
        """
        model, iter_ = treeview.get_selection().get_selected()
        if iter_:
            handle = model.get_value(iter_, 0)
            try:
                person = self.dbstate.db.get_person_from_handle(handle)
                EditPerson(self.dbstate, self.uistate, [], person)
            except WindowActiveError:
                pass

class PersonChildren(Children):
    """
    Displays the children of a person.
    """
    def build_gui(self):
        """
        Build the GUI interface.
        """
        tip = _('Double-click on a row to edit the selected child.')
        self.set_tooltip(tip)
        top = Gtk.TreeView()
        titles = [('', NOSORT, 50,),
                  (_('Child'), 1, 250),
                  (_('Birth Date'), 3, 100),
                  ('', 3, 100),
                  (_('Death Date'), 5, 100),
                  ('', 5, 100),
                  (_('Spouse'), 6, 250)]
        self.model = ListModel(top, titles, event_func=self.edit_person)
        return top

    def db_changed(self):
        self.dbstate.db.connect('person-update', self.update)

    def active_changed(self, handle):
        self.update()

    def main(self):
        active_handle = self.get_active('Person')
        self.model.clear()
        if active_handle:
            self.display_person(active_handle)
        else:
            self.set_has_data(False)

    def update_has_data(self):
        active_handle = self.get_active('Person')
        if active_handle:
            active = self.dbstate.db.get_person_from_handle(active_handle)
            self.set_has_data(self.get_has_data(active))
        else:
            self.set_has_data(False)

    def get_has_data(self, active_person):
        """
        Return True if the gramplet has data, else return False.
        """
        if active_person is None:
            return False
        for family_handle in active_person.get_family_handle_list():
            family = self.dbstate.db.get_family_from_handle(family_handle)
            if family.get_child_ref_list():
                return True
        return False

    def display_person(self, active_handle):
        """
        Display the children of the active person.
        """
        active_person = self.dbstate.db.get_person_from_handle(active_handle)
        for family_handle in active_person.get_family_handle_list():
            family = self.dbstate.db.get_family_from_handle(family_handle)
            self.display_family(family, active_handle)
        self.set_has_data(self.model.count > 0)

    def display_family(self, family, active_handle):
        """
        Display the children of given family.
        """
        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        if father_handle == active_handle:
            spouse = self.dbstate.db.get_person_from_handle(mother_handle)
        else:
            spouse = self.dbstate.db.get_person_from_handle(father_handle)

        for child_ref in family.get_child_ref_list():
            child = self.dbstate.db.get_person_from_handle(child_ref.ref)
            self.add_child(child, spouse)

    def add_child(self, child, spouse):
        """
        Add a child to the model.
        """
        name = name_displayer.display(child)
        if spouse:
            spouse = name_displayer.display(spouse)
        spouse = spouse or ''
        birth = get_birth_or_fallback(self.dbstate.db, child)
        birth_date, birth_sort, birth_place = self.get_date_place(birth)
        death = get_death_or_fallback(self.dbstate.db, child)
        death_date, death_sort, death_place = self.get_date_place(death)
        self.model.add((child.get_handle(),
                        name,
                        birth_date,
                        birth_sort,
                        death_date,
                        death_sort,
                        spouse))

class FamilyChildren(Children):
    """
    Displays the children of a family.
    """
    def build_gui(self):
        """
        Build the GUI interface.
        """
        tip = _('Double-click on a row to edit the selected child.')
        self.set_tooltip(tip)
        top = Gtk.TreeView()
        titles = [('', NOSORT, 50,),
                  (_('Child'), 1, 250),
                  (_('Birth Date'), 3, 100),
                  ('', 3, 100),
                  (_('Death Date'), 5, 100),
                  ('', 5, 100)]
        self.model = ListModel(top, titles, event_func=self.edit_person)
        return top

    def db_changed(self):
        self.dbstate.db.connect('family-update', self.update)
        self.connect_signal('Family', self.update)

    def main(self):
        active_handle = self.get_active('Family')
        self.model.clear()
        if active_handle:
            family = self.dbstate.db.get_family_from_handle(active_handle)
            self.display_family(family)
        else:
            self.set_has_data(False)

    def update_has_data(self):
        active_handle = self.get_active('Family')
        if active_handle:
            active = self.dbstate.db.get_family_from_handle(active_handle)
            self.set_has_data(self.get_has_data(active))
        else:
            self.set_has_data(False)

    def get_has_data(self, active_family):
        """
        Return True if the gramplet has data, else return False.
        """
        if active_family is None:
            return False
        if active_family.get_child_ref_list():
            return True
        return False

    def display_family(self, family):
        """
        Display the children of given family.
        """
        for child_ref in family.get_child_ref_list():
            child = self.dbstate.db.get_person_from_handle(child_ref.ref)
            self.add_child(child)
        self.set_has_data(self.model.count > 0)

    def add_child(self, child):
        """
        Add a child to the model.
        """
        name = name_displayer.display(child)
        birth = get_birth_or_fallback(self.dbstate.db, child)
        birth_date, birth_sort, birth_place = self.get_date_place(birth)
        death = get_death_or_fallback(self.dbstate.db, child)
        death_date, death_sort, death_place = self.get_date_place(death)
        self.model.add((child.get_handle(),
                        name,
                        birth_date,
                        birth_sort,
                        death_date,
                        death_sort))

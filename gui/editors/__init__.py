#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
# Copyright (C) 2011       Tim G L Lyons
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
# gui/editors/__init__.py

from .editaddress import EditAddress
from .editattribute import EditAttribute, EditSrcAttribute
from .editchildref import EditChildRef
from .editcitation import EditCitation, DeleteCitationQuery
from .editdate import EditDate
from .editevent import EditEvent, DeleteEventQuery
from .editeventref import EditEventRef
from .editfamily import EditFamily
from .editldsord import EditLdsOrd, EditFamilyLdsOrd
from .editlocation import EditLocation
from .editmedia import EditMedia, DeleteMediaQuery
from .editmediaref import EditMediaRef
from .editname import EditName
from .editnote import EditNote, DeleteNoteQuery
from .editperson import EditPerson
from .editpersonref import EditPersonRef
from .editplace import EditPlace, DeletePlaceQuery
from .editplacename import EditPlaceName
from .editplaceref import EditPlaceRef
from .editrepository import EditRepository, DeleteRepositoryQuery
from .editreporef import EditRepoRef
from .editsource import EditSource, DeleteSrcQuery
from .edittaglist import EditTagList
from .editurl import EditUrl
from .editlink import EditLink
from .filtereditor import FilterEditor, EditFilter

# Map from gramps.gen.lib name to Editor:
EDITORS = {
    'Person': EditPerson,
    'Event': EditEvent,
    'Family': EditFamily,
    'Media': EditMedia,
    'Source': EditSource,
    'Citation': EditCitation,
    'Place': EditPlace,
    'Repository': EditRepository,
    'Note': EditNote,
    }

def EditObject(dbstate, uistate, track, obj_class, prop=None, value=None, callback=None):
    """
    Generic Object Editor. 
    obj_class is Person, Source, Repository, etc.
    prop is 'handle', 'gramps_id', or None (for new object)
    value is string handle, string gramps_id, or None (for new object)
    """
    import logging
    LOG = logging.getLogger(".Edit")
    if obj_class in dbstate.db.get_table_names():
        if value is None:
            obj = dbstate.db.get_table_metadata(obj_class)["class_func"]()
            try:
                EDITORS[obj_class](dbstate, uistate, track, obj, callback=callback)
            except Exception as msg:
                LOG.warn(str(msg)) 
        elif prop in ("gramps_id", "handle"):
            obj = dbstate.db.get_table_metadata(obj_class)[prop + "_func"](value)
            if obj:
                try:
                    EDITORS[obj_class](dbstate, uistate, track, obj, callback=callback)
                except Exception as msg:
                    LOG.warn(str(msg)) 
            else:
                LOG.warn("gramps://%s/%s/%s not found" % 
                         (obj_class, prop, value))
        else:
            LOG.warn("unknown property to edit '%s'; "
                     "should be 'gramps_id' or 'handle'" % prop)
    else:
        LOG.warn("unknown object to edit '%s'; "
                 "should be one of %s" % (obj_class, list(EDITORS.keys())))


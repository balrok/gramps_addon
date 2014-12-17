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

"Import from GEDCOM"

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
import sys

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
LOG = logging.getLogger(".GedcomImport")

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.errors import DbError, GedcomError
from gramps.gui.glade import Glade
from gramps.plugins.lib.libmixin import DbMixin
from gramps.plugins.lib import libgedcom
# The following code is necessary to ensure that when Help->Plugin
# Manager->Reload is executed, not only is the top-level exportgedcom file
# reloaded, but also the dependent libgedcom. This ensures that testing can have
# a quick turnround, without having to restart Gramps.
module = __import__("gramps.plugins.lib.libgedcom",
                    fromlist=["gramps.plugins.lib"])   # why o why ?? as above!
if sys.version_info[0] < 3:
    reload (module)
else:
    import imp
    imp.reload(module)

from gramps.gen.config import config
from gramps.gen.constfunc import STRTYPE
    
#-------------------------------------------------------------------------
#
# importData
#
#-------------------------------------------------------------------------
def importData(database, filename, user):
    """
    Try to handle ANSEL encoded files that are not really ANSEL encoded
    """

    if DbMixin not in database.__class__.__bases__:
        database.__class__.__bases__ = (DbMixin,) +  \
                                        database.__class__.__bases__

    try:
        ifile = open(filename, "r")
    except IOError:
        return

    ansel = False
    gramps = False
    for index in range(50):
        line = ifile.readline().split()
        if len(line) == 0:
            break
        if len(line) > 2 and line[1][0:4] == 'CHAR' and line[2] == "ANSEL":
            ansel = True
        if len(line) > 2 and line[1][0:4] == 'SOUR' and line[2] == "GRAMPS":
            gramps = True
    ifile.close()

    if not gramps and ansel:
        top = Glade()
        code = top.get_object('codeset')
        code.set_active(0)
        dialog = top.toplevel
        dialog.run()
        enc = ['ANSEL', 'ANSEL', 'ANSI', 'ASCII', 'UTF-8']
        code_set = enc[ code.get_active()]
        dialog.destroy()
    else:
        code_set = ""

    assert(isinstance(code_set, STRTYPE))

    try:
        if sys.version_info[0] < 3:
            ifile = open(filename, "rU")
        else:
            ifile = open(filename, "rb")
        stage_one = libgedcom.GedcomStageOne(ifile)
        stage_one.parse()

        if code_set:
            stage_one.set_encoding(code_set)
        ifile.seek(0)
        if database.get_feature("skip-import-additions"): # don't add source or tags
            gedparse = libgedcom.GedcomParser(
                database, ifile, filename, user, stage_one, None, None)
        else:
            gedparse = libgedcom.GedcomParser(
                database, ifile, filename, user, stage_one, 
                config.get('preferences.default-source'),
                (config.get('preferences.tag-on-import-format') if 
                 config.get('preferences.tag-on-import') else None))
    except IOError as msg:
        user.notify_error(_("%s could not be opened\n") % filename, str(msg))
        return
    except GedcomError as msg:
        user.notify_error(_("Invalid GEDCOM file"), 
                          _("%s could not be imported") % filename + "\n" + str(msg))
        return

    try:
        read_only = database.readonly
        database.readonly = False
        gedparse.parse_gedcom_file(False)
        database.readonly = read_only
        ifile.close()
    except IOError as msg:
        msg = _("%s could not be opened\n") % filename
        user.notify_error(msg, str(msg))
        return
    except DbError as msg:
        user.notify_db_error(str(msg.value))
        return
    except GedcomError as msg:
        user.notify_error(_('Error reading GEDCOM file'), str(msg))
        return

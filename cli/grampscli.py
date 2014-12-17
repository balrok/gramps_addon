#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2001-2006  Donald N. Allingham
# Copyright (C) 2009 Benny Malengier
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
Provides the startcli function, which the main program calls for CLI
execution of Gramps.

Provides also two small base classes: :class:`CLIDbLoader`, :class:`CLIManager`
"""

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
from __future__ import print_function

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
import os
import sys

import logging

LOG = logging.getLogger(".grampscli")
#-------------------------------------------------------------------------
#
# GRAMPS  modules
#
#-------------------------------------------------------------------------
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.config import config
from gramps.gen.const import PLUGINS_DIR, USER_PLUGINS
from gramps.gen.errors import DbError
from gramps.gen.dbstate import DbState
from gramps.gen.db import DbBsddb
from gramps.gen.db.exceptions import (DbUpgradeRequiredError, 
                                      BsddbDowngradeError, 
                                      DbVersionError, 
                                      DbEnvironmentError,
                                      BsddbUpgradeRequiredError,
                                      BsddbDowngradeRequiredError,
                                      PythonUpgradeRequiredError,
                                      PythonDowngradeError)
from gramps.gen.plug import BasePluginManager
from gramps.gen.utils.config import get_researcher
from gramps.gen.recentfiles import recent_files

#-------------------------------------------------------------------------
#
# CLI DbLoader class
#
#-------------------------------------------------------------------------
class CLIDbLoader(object):
    """
    Base class for Db loading action inside a :class:`.DbState`. Only the
    minimum is present needed for CLI handling
    """
    def __init__(self, dbstate):
        self.dbstate = dbstate
    
    def _warn(self, title, warnmessage):
        """
        Issue a warning message. Inherit for GUI action
        """
        print(_('WARNING: %s') % warnmessage, file=sys.stderr)
    
    def _errordialog(self, title, errormessage):
        """
        Show the error. A title for the error and an errormessage
        Inherit for GUI action
        """
        print(_('ERROR: %s') % errormessage, file=sys.stderr)
        sys.exit(1)
    
    def _dberrordialog(self, msg):
        """
        Show a database error. 

        :param msg: an error message
        :type msg : string

        .. note:: Inherit for GUI action
        """
        self._errordialog( '', _("Low level database corruption detected") 
            + '\n' +
            _("Gramps has detected a problem in the underlying "
              "Berkeley database. This can be repaired from "
              "the Family Tree Manager. Select the database and "
              'click on the Repair button') + '\n\n' + str(msg))
    
    def _begin_progress(self):
        """
        Convenience method to allow to show a progress bar if wanted on load
        actions. Inherit if needed
        """
        pass
    
    def _pulse_progress(self, value):
        """
        Convenience method to allow to show a progress bar if wanted on load
        actions. Inherit if needed
        """
        pass

    def _end_progress(self):
        """
        Convenience method to allow to hide the progress bar if wanted at
        end of load actions. Inherit if needed
        """
        pass

    def read_file(self, filename):
        """
        This method takes care of changing database, and loading the data.
        In 3.0 we only allow reading of real databases of filetype 
        'x-directory/normal'
        
        This method should only return on success.
        Returning on failure makes no sense, because we cannot recover,
        since database has already been changed.
        Therefore, any errors should raise exceptions.

        On success, return with the disabled signals. The post-load routine
        should enable signals, as well as finish up with other UI goodies.
        """

        if os.path.exists(filename):
            if not os.access(filename, os.W_OK):
                mode = "r"
                self._warn(_('Read only database'), 
                                             _('You do not have write access '
                                               'to the selected file.'))
            else:
                mode = "w"
        else:
            mode = 'w'

        dbclass = DbBsddb
        
        self.dbstate.change_database(dbclass())
        self.dbstate.db.disable_signals()

        self._begin_progress()
        
        try:
            self.dbstate.db.load(filename, self._pulse_progress, mode)
            self.dbstate.db.set_save_path(filename)
        except DbEnvironmentError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except BsddbUpgradeRequiredError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except BsddbDowngradeRequiredError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except BsddbDowngradeError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except DbUpgradeRequiredError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except PythonDowngradeError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except PythonUpgradeRequiredError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except DbVersionError as msg:
            self.dbstate.no_database()
            self._errordialog( _("Cannot open database"), str(msg))
        except OSError as msg:
            self.dbstate.no_database()
            self._errordialog(
                _("Could not open file: %s") % filename, str(msg))
        except DbError as msg:
            self.dbstate.no_database()
            self._dberrordialog(msg)
        except Exception:
            self.dbstate.no_database()
            LOG.error("Failed to open database.", exc_info=True)
        return True

#-------------------------------------------------------------------------
#
# CLIManager class
#
#-------------------------------------------------------------------------

class CLIManager(object):
    """
    Sessionmanager for Gramps. This is in effect a reduced :class:`.ViewManager` 
    instance (see gui/viewmanager), suitable for CLI actions. 
    Aim is to manage a dbstate on which to work (load, unload), and interact
    with the plugin session
    """
    def __init__(self, dbstate, setloader, user):
        self.dbstate = dbstate
        if setloader:
            self.db_loader = CLIDbLoader(self.dbstate)
        else:
            self.db_loader = None
        self.file_loaded = False
        self._pmgr = BasePluginManager.get_instance()
        self.user = user

    def open_activate(self, path):
        """
        Open and make a family tree active
        """
        self._read_recent_file(path)
    
    def _errordialog(self, title, errormessage):
        """
        Show the error. A title for the error and an errormessage
        """
        print(_('ERROR: %s') % errormessage, file=sys.stderr)
        sys.exit(1)
        
    def _read_recent_file(self, filename):
        """
        Called when a file needs to be loaded
        """
        # A recent database should already have a directory If not, do nothing,
        #  just return. This can be handled better if family tree delete/rename
        #  also updated the recent file menu info in displaystate.py
        if not  os.path.isdir(filename):
            self._errordialog(
                    _("Could not load a recent Family Tree."), 
                    _("Family Tree does not exist, as it has been deleted."))
            return

        if self.db_loader.read_file(filename):
            # Attempt to figure out the database title
            path = os.path.join(filename, "name.txt")
            try:
                ifile = open(path)
                title = ifile.readline().strip()
                ifile.close()
            except:
                title = filename

            self._post_load_newdb(filename, 'x-directory/normal', title)
    
    def _post_load_newdb(self, filename, filetype, title=None):
        """
        The method called after load of a new database. 
        Here only CLI stuff is done, inherit this method to add extra stuff
        """
        self._post_load_newdb_nongui(filename, title)
    
    def _post_load_newdb_nongui(self, filename, title=None):
        """
        Called after a new database is loaded.
        """
        if not filename:
            return
        
        if filename[-1] == os.path.sep:
            filename = filename[:-1]
        name = os.path.basename(filename)
        self.dbstate.db.db_name = title
        if title:
            name = title

        # This method is for UI stuff when the database has changed.
        # Window title, recent files, etc related to new file.

        self.dbstate.db.set_save_path(filename)
        
        # apply preferred researcher if loaded file has none
        res = self.dbstate.db.get_researcher()
        owner = get_researcher()
        if res.get_name() == "" and owner.get_name() != "":
            self.dbstate.db.set_researcher(owner)
        
        name_displayer.set_name_format(self.dbstate.db.name_formats)
        fmt_default = config.get('preferences.name-format')
        name_displayer.set_default_format(fmt_default)

        self.dbstate.db.enable_signals()
        self.dbstate.signal_change()

        config.set('paths.recent-file', filename)

        recent_files(filename, name)
        self.file_loaded = True
    
    def do_reg_plugins(self, dbstate, uistate):
        """
        Register the plugins at initialization time.
        """
        self._pmgr.reg_plugins(PLUGINS_DIR, dbstate, uistate)
        self._pmgr.reg_plugins(USER_PLUGINS, dbstate, uistate, load_on_reg=True)

def startcli(errors, argparser):
    """
    Starts a cli session of Gramps.

    :param errors: errors already encountered
    :param argparser: :class:`.ArgParser` instance
    """
    if errors:
        #already errors encountered. Show first one on terminal and exit
        errmsg = _('Error encountered: %s') % errors[0][0]
        print(errmsg, file=sys.stderr)
        errmsg = _('  Details: %s') % errors[0][1]
        print(errmsg, file=sys.stderr)
        sys.exit(1)
    
    if argparser.errors: 
        errmsg = _('Error encountered in argument parsing: %s') \
                                                    % argparser.errors[0][0]
        print(errmsg, file=sys.stderr)
        errmsg = _('  Details: %s') % argparser.errors[0][1]
        print(errmsg, file=sys.stderr)
        sys.exit(1)
    
    #we need to keep track of the db state
    dbstate = DbState()

    #we need a manager for the CLI session
    from .user import User
    user=User(auto_accept=argparser.auto_accept,
            quiet=argparser.quiet)
    climanager = CLIManager(dbstate, setloader=True, user=user)

    #load the plugins
    climanager.do_reg_plugins(dbstate, uistate=None)
    # handle the arguments
    from .arghandler import ArgHandler
    handler = ArgHandler(dbstate, argparser, climanager)
    # create a manager to manage the database
    
    handler.handle_args_cli()
    
    sys.exit(0)

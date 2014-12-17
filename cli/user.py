#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2010  Brian G. Matherly
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
The User class provides basic interaction with the user.
"""

#------------------------------------------------------------------------
#
# Python Modules
#
#------------------------------------------------------------------------
from __future__ import print_function, unicode_literals
import sys

#------------------------------------------------------------------------
#
# Gramps Modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen import user

#------------------------------------------------------------------------
#
# Private Constants
#
#------------------------------------------------------------------------
_SPINNER = ['|', '/', '-', '\\']

#-------------------------------------------------------------------------
#
# User class
#
#-------------------------------------------------------------------------
class User(user.User):
    """
    This class provides a means to interact with the user via CLI.
    It implements the interface in :class:`.gen.user.User`
    """
    def __init__(self, callback=None, error=None, auto_accept=False, quiet=False):
        """
        Init.

        :param error: If given, notify_error delegates to this callback
        :type error: function(title, error)
        """
        user.User.__init__(self, callback, error)
        self.steps = 0;
        self.current_step = 0;
        self._input = raw_input if sys.version_info[0] < 3 else input

        def yes(*args): 
            return True

        if auto_accept:
            self.prompt = yes
        if quiet:
            self.begin_progress = self.end_progress = self.step_progress = \
                    self._default_callback = yes
    
    def begin_progress(self, title, message, steps):
        """
        Start showing a progress indicator to the user.
        
        :param title: the title of the progress meter
        :type title: str
        :param message: the message associated with the progress meter
        :type message: str
        :param steps: the total number of steps for the progress meter.
                      a value of 0 indicates that the ending is unknown and the
                      meter should just show activity.
        :type steps: int
        :returns: none
        """
        self._fileout.write(message)
        self.steps = steps
        self.current_step = 0;
        if self.steps == 0:
            self._fileout.write(_SPINNER[self.current_step])
        else:
            self._fileout.write("00%")
    
    def step_progress(self):
        """
        Advance the progress meter.
        """
        self.current_step += 1
        if self.steps == 0:
            self.current_step %= 4
            self._fileout.write("\r  %s  " % _SPINNER[self.current_step])
        else:
            percent = int((float(self.current_step) / self.steps) * 100)
            self._fileout.write("\r%02d%%" % percent)

    def end_progress(self):
        """
        Stop showing the progress indicator to the user.
        """
        self._fileout.write("\r100%\n")
    
    def prompt(self, title, message, accept_label, reject_label):
        """
        Prompt the user with a message to select an alternative.
        
        :param title: the title of the question, e.g.: "Undo history warning"
        :type title: str
        :param message: the message, e.g.: "Proceeding with the tool will erase
                        the undo history. If you think you may want to revert
                        running this tool, please stop here and make a backup
                        of the DB."
        :type question: str
        :param accept_label: what to call the positive choice, e.g.: "Proceed"
        :type accept_label: str
        :param reject_label: what to call the negative choice, e.g.: "Stop"
        :type reject_label: str
        :returns: the user's answer to the question
        :rtype: bool
        """
        accept_label = accept_label.replace("_", "")
        reject_label = reject_label.replace("_", "")
        text = "{t}\n{m} ([{y}]/{n}): ".format(
                t = title,
                m = message,
                y = accept_label,
                n = reject_label)
        print (text, file = self._fileout) # TODO python3 add flush=True
        try:
            reply = self._input()
            return reply == "" or reply == accept_label
        except EOFError:
            return False
    
    def warn(self, title, warning=""):
        """
        Warn the user.
        
        :param title: the title of the warning
        :type title: str
        :param warning: the warning
        :type warning: str
        :returns: none
        """
        self._fileout.write("%s %s" % (title, warning))
    
    def notify_error(self, title, error=""):
        """
        Notify the user of an error.
        
        :param title: the title of the error
        :type title: str
        :param error: the error message
        :type error: str
        :returns: none
        """
        if self.error_function:
            self.error_function(title, error)
        else:
            self._fileout.write("%s %s" % (title, error))

    def notify_db_error(self, error):
        """
        Notify the user of a DB error.
        
        :param error: the error message
        :type error: str
        :returns: none
        """
        self.notify_error(
            _("Low level database corruption detected"),
            _("Gramps has detected a problem in the underlying "
              "Berkeley database. This can be repaired from "
              "the Family Tree Manager. Select the database and "
              'click on the Repair button') + '\n\n' + error)

    def info(self, msg1, infotext, parent=None, monospaced=False):
        """
        Displays information to the CLI
        """
        self._fileout.write("{} {}\n".format(msg1, infotext))

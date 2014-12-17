# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2012       Doug Blank <doug.blank@gmail.com>
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

from __future__ import unicode_literals

import sys
import subprocess

if sys.version_info[0] < 3:
    cuni = unicode
else:
    def to_utf8(s):
        return s.decode("utf-8", errors = 'replace')
    cuni = to_utf8

def get_git_revision(path=""):
    stdout = ""
    command = "git log -1 --format=%h"
    try:
        p = subprocess.Popen(
                "{} \"{}\"".format(command, path),
                shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
    except:
        return "" # subprocess failed
    # subprocess worked
    if stdout and len(stdout) > 0: # has output
        try:
            stdout = cuni(stdout) # get a proper string
        except UnicodeDecodeError:
            pass
        return "-" + stdout if stdout else ""
    else: # no output from git log
        return ""

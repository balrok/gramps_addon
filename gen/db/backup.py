#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007  Donald N. Allingham
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
# gen/db/backup.py

"""
Description
===========

This module Provides backup and restore functions for a database. The
backup function saves the data into backup files, while the restore
function loads the data back into a database.

You should only restore the data into an empty database.

Implementation
==============

Not all of the database tables need to be backed up, since many are
automatically generated from the others. The tables that are backed up
are the primary tables and the metadata table.

The database consists of a table of "pickled" tuples. Each of the
primary tables is "walked", and the pickled tuple is extracted, and
written to the backup file.

Restoring the data is just as simple. The backup file is parsed an
entry at a time, and inserted into the associated database table. The
derived tables are built automatically as the items are entered into
db.
"""

#-------------------------------------------------------------------------
#
# load standard python libraries
#
#-------------------------------------------------------------------------
import os
import sys
if sys.version_info[0] < 3:
    import cPickle as pickle
else:
    import pickle

#------------------------------------------------------------------------
#
# Gramps libs
#
#------------------------------------------------------------------------
from .exceptions import DbException
from .write import FAMILY_TBL, PLACES_TBL, SOURCES_TBL, MEDIA_TBL, \
    EVENTS_TBL, PERSON_TBL, REPO_TBL, NOTE_TBL, TAG_TBL, META, CITATIONS_TBL

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
LOG = logging.getLogger(".Backup")

def backup(database):
    """
    Exports the database to a set of backup files. These files consist
    of the pickled database tables, one file for each table.

    The heavy lifting is done by the private :py:func:`__do__export` function.
    The purpose of this function is to catch any exceptions that occur.

    :param database: database instance to backup
    :type database: DbDir
    """
    try:
        __do_export(database)
    except (OSError, IOError) as msg:
        raise DbException(str(msg))

def __mk_backup_name(database, base):
    """
    Return the backup name of the database table

    :param database: database instance 
    :type database: DbDir
    :param base: base name of the table
    :type base: str
    """
    return os.path.join(database.get_save_path(), base + ".gbkp")

def __mk_tmp_name(database, base):
    """
    Return the temporary backup name of the database table

    :param database: database instance 
    :type database: DbDir
    :param base: base name of the table
    :type base: str
    """
    return os.path.join(database.get_save_path(), base + ".gbkp.new")

def __do_export(database):
    """
    Loop through each table of the database, saving the pickled data
    a file.

    :param database: database instance to backup
    :type database: DbDir
    """
    try:
        for (base, tbl) in __build_tbl_map(database):
            backup_name = __mk_tmp_name(database, base)
            backup_table = open(backup_name, 'wb')
    
            cursor = tbl.cursor()
            data = cursor.first()
            while data:
                pickle.dump(data, backup_table, 2)
                data = cursor.next()
            cursor.close()
            backup_table.close()
    except (IOError,OSError):
        return

    for (base, tbl) in __build_tbl_map(database):
        new_name = __mk_backup_name(database, base)
        old_name = __mk_tmp_name(database, base)
        if os.path.isfile(new_name):
            os.unlink(new_name)
        os.rename(old_name, new_name)

def restore(database):
    """
    Restores the database to a set of backup files. These files consist
    of the pickled database tables, one file for each table.

    The heavy lifting is done by the private :py:func:`__do__restore` function.
    The purpose of this function is to catch any exceptions that occur.

    :param database: database instance to restore
    :type database: DbDir
    """
    try:
        __do_restore(database)
    except (OSError, IOError) as msg:
        raise DbException(str(msg))

def __do_restore(database):
    """
    Loop through each table of the database, restoring the pickled data
    to the appropriate database file.

    :param database: database instance to backup
    :type database: DbDir
    """
    for (base, tbl) in __build_tbl_map(database):
        backup_name = __mk_backup_name(database, base)
        backup_table = open(backup_name, 'rb')
        __load_tbl_txn(database, backup_table, tbl)

    database.rebuild_secondary()

def __load_tbl_txn(database, backup_table, tbl):
    """
    Return the temporary backup name of the database table

    :param database: database instance 
    :type database: DbDir
    :param backup_table: file containing the backup data
    :type backup_table: file
    :param tbl: Berkeley db database table
    :type tbl: Berkeley db database table
    """
    try:
        while True:
            data = pickle.load(backup_table)
            txn = database.env.txn_begin()
            tbl.put(data[0], data[1], txn=txn)
            txn.commit()
    except EOFError:
        backup_table.close()

def __build_tbl_map(database):
    """
    Builds a table map of names to database tables.

    :param database: database instance to backup
    :type database: DbDir
    """
    return [
        ( PERSON_TBL,  database.person_map.db),
        ( FAMILY_TBL,  database.family_map.db),
        ( PLACES_TBL,  database.place_map.db),
        ( SOURCES_TBL, database.source_map.db),
        ( CITATIONS_TBL, database.citation_map.db),
        ( REPO_TBL,    database.repository_map.db),
        ( NOTE_TBL,    database.note_map.db),
        ( MEDIA_TBL,   database.media_map.db),
        ( EVENTS_TBL,  database.event_map.db),
        ( TAG_TBL,     database.tag_map.db),
        ( META,        database.metadata.db),
        ]

#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2004-2006 Donald N. Allingham
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
Exports the DbTxn class for managing Gramps transactions and the undo
database.
"""

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
from __future__ import print_function, with_statement

import sys
if sys.version_info[0] < 3:
    import cPickle as pickle
else:
    import pickle
import logging

from collections import defaultdict

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from .dbconst import (DBLOGNAME, TXNADD, TXNUPD, TXNDEL)

_LOG = logging.getLogger(DBLOGNAME)


#-------------------------------------------------------------------------
#
# Gramps transaction class
#
#-------------------------------------------------------------------------
class DbTxn(defaultdict):
    """
    Define a group of database commits that define a single logical operation.
    """

    __slots__ = ('msg', 'commitdb', 'db', 'batch', 'first',
                 'last', 'timestamp', '__dict__')

    def __enter__(self):
        """
        Context manager entry method
        """
        self.db.transaction_begin(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit method
        """
        if exc_type is None:
            self.db.transaction_commit(self)
        else:
            self.db.transaction_abort(self)
        return False
    
    def __init__(self, msg, grampsdb, batch=False, **kwargs):
        """
        Create a new transaction. 
        
        The grampsdb should have transaction_begin/commit/abort methods, and 
        a get_undodb method to store undo actions.
        
        A Transaction instance can be created directly, but it is advised to
        use a context to do this. Like this the user must not worry about 
        calling the transaction_xx methods on the database.
         
        The grampsdb parameter is a reference to the DbWrite object to which
        this transaction will be applied.
        grampsdb.get_undodb() should return a list-like interface that 
        stores the commit data. This could be a simple list, or a RECNO-style
        database object. 

        The data structure used to handle the transactions (see the add method)
        is a Python dictionary where:
        
        key = (object type, transaction type) where:
            object type = the numeric type of an object. These are
                          defined as PERSON_KEY = 0, FAMILY_KEY = 1, etc.
                          as imported from dbconst.
            transaction type = a numeric representation of the type of
                          transaction: TXNADD = 0, TXNUPD = 1, TXNDEL = 2
        
        data = Python list where:
            list element = (handle, data) where:
                handle = handle (database key) of the object in the transaction
                data   = pickled representation of the object        
        """

        defaultdict.__init__(self, list, {})

        self.msg = msg
        self.commitdb = grampsdb.get_undodb()
        self.db = grampsdb
        self.batch = batch
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.first = None
        self.last = None
        self.timestamp = 0

    def get_description(self):
        """
        Return the text string that describes the logical operation performed 
        by the Transaction.
        """
        return self.msg

    def set_description(self, msg):
        """
        Set the text string that describes the logical operation performed by 
        the Transaction.
        """
        self.msg = msg

    def add(self, obj_type, trans_type, handle, old_data, new_data):
        """
        Add a commit operation to the Transaction. 
        
        The obj_type is a constant that indicates what type of PrimaryObject 
        is being added. The handle is the object's database handle, and the 
        data is the tuple returned by the object's serialize method.
        """
        self.last = self.commitdb.append(
            pickle.dumps((obj_type, trans_type, handle, old_data, new_data), 1))
        if self.last is None:
            self.last = len(self.commitdb) -1
        if self.first is None:
            self.first = self.last
        _LOG.debug('added to trans: %d %d %s' % (obj_type, trans_type, handle))
        self[(obj_type, trans_type)] += [(handle, new_data)]
        return

    def get_recnos(self, reverse=False):
        """
        Return a list of record numbers associated with the transaction.
        
        While the list is an arbitrary index of integers, it can be used
        to indicate record numbers for a database.
        """

        if self.first is None or self.last is None:
            return []
        if not reverse:
            return range(self.first, self.last+1)
        else:
            return range(self.last, self.first-1, -1)

    def get_record(self, recno):
        """
        Return a tuple representing the PrimaryObject type, database handle
        for the PrimaryObject, and a tuple representing the data created by
        the object's serialize method.
        """
        return pickle.loads(self.commitdb[recno])

    def __len__(self):
        """
        Return the number of commits associated with the Transaction.
        """
        if self.first is None or self.last is None:
            return 0
        return self.last - self.first + 1

# Test functions

def testtxn():
    """
    Test suite
    """    
    class FakeMap(dict):
        """Fake database map with just two methods"""
        def put(self, key, data):
            """Set a property"""
            super(FakeMap, self).__setitem__(key, data)
        def delete(self, key):
            """Delete a proptery"""
            super(FakeMap, self).__delitem__(key)

    class FakeDb:
        """Fake gramps database"""
        def __init__(self):
            self.person_map = FakeMap()
            self.family_map = FakeMap()
            self.event_map  = FakeMap()
            self.reference_map  = FakeMap()
            self.readonly = False
            self.env = None
            self.undodb = FakeCommitDb()
        def transaction_commit(self, transaction):
            """Commit the transaction to the undo database and cleanup."""
            transaction.clear()
            self.undodb.commit(transaction)
        def emit(self, obj, value):
            """send signal"""
            pass

    class FakeCommitDb(list):
        """ Fake commit database"""
        def commit(self, transaction):
            """commit transaction to undo db"""
            pass
        def undo(self):
            """undo last transaction"""
            pass

    grampsdb = FakeDb()
    commitdb = grampsdb.undodb
    trans = DbTxn("Test Transaction", commitdb, grampsdb, batch=False)
    grampsdb.person_map.put('1', "data1")
    trans.add(0, TXNADD, '1', None, "data1")
    grampsdb.person_map.put('2', "data2")
    trans.add(0, TXNADD, '2', None, "data2")
    grampsdb.person_map.put('2', "data3")
    trans.add(0, TXNUPD, '2', None, "data3")
    grampsdb.person_map.delete('1')
    trans.add(0, TXNDEL, '1', None, None)

    print(trans)
    print(trans.get_description())
    print(trans.set_description("new text"))
    print(trans.get_description())
    for i in trans.get_recnos():
        print(trans.get_record(i))
    print(list(trans.get_recnos()))
    print(list(trans.get_recnos(reverse=True)))
    print(grampsdb.person_map)

if __name__ == '__main__':
    testtxn()

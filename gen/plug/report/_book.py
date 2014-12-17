#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2003-2007  Donald N. Allingham
# Copyright (C) 2007-2008  Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2011-2014  Paul Franklin
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

# Written by Alex Roitman, 
# largely based on the BaseDoc classes by Don Allingham

#-------------------------------------------------------------------------
#
# Standard Python modules
#
#-------------------------------------------------------------------------
from ...const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
import copy

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
log = logging.getLogger(".Book")
import os

#-------------------------------------------------------------------------
#
# SAX interface
#
#-------------------------------------------------------------------------
try:
    from xml.sax import make_parser, handler, SAXParseException
    from xml.sax.saxutils import escape
except:
    from _xmlplus.sax import make_parser, handler, SAXParseException
    from _xmlplus.sax.saxutils import escape

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from ...const import HOME_DIR
from ...utils.cast import get_type_converter_by_name, type_name
from ..docgen import StyleSheet, StyleSheetList
from .. import BasePluginManager
from . import book_categories
from ...constfunc import cuni

#------------------------------------------------------------------------
#
# Private Constants
#
#------------------------------------------------------------------------
_UNSUPPORTED = _("Unsupported")

#------------------------------------------------------------------------
#
# Book Item class
#
#------------------------------------------------------------------------
class BookItem(object):
    """
    Interface into the book item -- a smallest element of the book.
    """

    def __init__(self, dbase, name):
        """
        Create a new empty BookItem.
        
        name:   the book item is retrieved 
                from the book item registry using name for lookup
        """
        self.dbase = dbase
        self.style_name = "default"
        pmgr = BasePluginManager.get_instance()

        for pdata in pmgr.get_reg_bookitems():
            if pdata.id == name:
                self.translated_name = pdata.name
                if not pdata.supported:
                    self.category = _UNSUPPORTED
                else:
                    self.category = book_categories[pdata.category]
                mod = pmgr.load_plugin(pdata)
                self.write_item = eval('mod.' + pdata.reportclass)
                self.name = pdata.id
                oclass = eval('mod.' + pdata.optionclass)
                self.option_class = oclass(self.name, self.dbase)
                self.option_class.load_previous_values()

    def get_name(self):
        """
        Return the name of the item.
        """
        return self.name

    def get_translated_name(self):
        """
        Return the translated name of the item.
        """
        return self.translated_name

    def get_category(self):
        """
        Return the category of the item.
        """
        return self.category

    def get_write_item(self):
        """
        Return the report-writing function of the item.
        """
        return self.write_item

    def set_style_name(self, style_name):
        """
        Set the style name for the item.
        
        style_name: name of the style to set.
        """
        self.style_name = style_name

    def get_style_name(self):
        """
        Return the style name of the item.
        """
        return self.style_name

#------------------------------------------------------------------------
#
# Book class
#
#------------------------------------------------------------------------
class Book(object):
    """
    Interface into the user-defined book -- a collection of book items.
    """

    def __init__(self, obj=None):
        """
        Create a new empty Book.

        obj:    if not None, creates the Book from the values in
                obj, instead of creating an empty Book.
        """

        self.name = ""
        self.dbname = ""
        self.paper_name = None
        self.paper_orientation = None
        self.paper_metric = None
        self.paper_custom_size = None
        self.paper_margins = None
        self.paper_format = None
        self.paper_output = None
        if obj:
            self.item_list = obj.item_list
        else:
            self.item_list = []
        
    def set_name(self, name):
        """
        Set the name of the book.
        
        name:   the name to set.
        """
        self.name = name

    def get_name(self):
        """
        Return the name of the book.
        """
        return self.name

    def get_dbname(self):
        """
        Return the name of the database file used for the book.
        """
        return self.dbname

    def set_dbname(self, name):
        """
        Set the name of the database file used for the book.

        name:   a filename to set.
        """
        self.dbname = name

    def clear(self):
        """
        Clears the contents of the book.
        """
        self.item_list = []

    def append_item(self, item):
        """
        Add an item to the book.
        
        item:   an item to append.
        """
        self.item_list.append(item)

    def insert_item(self, index, item):
        """
        Inserts an item into the given position in the book.
        
        index:  a position index. 
        item:   an item to append.
        """
        self.item_list.insert(index, item)

    def pop_item(self, index):
        """
        Pop an item from given position in the book.
        
        index:  a position index. 
        """
        return self.item_list.pop(index)

    def get_item(self, index):
        """
        Return an item at a given position in the book.
        
        index:  a position index. 
        """
        return self.item_list[index]

    def set_item(self, index, item):
        """
        Set an item at a given position in the book.
        
        index:  a position index. 
        item:   an item to set.
        """
        self.item_list[index] = item

    def get_item_list(self):
        """
        Return list of items in the current book.
        """
        return self.item_list

    def set_paper_name(self, paper_name):
        """
        Set the paper name for the Book.
        @param paper_name: name of the paper to set.
        @type paper_name: str
        """
        self.paper_name = paper_name

    def get_paper_name(self):
        """
        Return the paper name of the Book.
        @returns: returns the paper name
        @rtype: str
        """
        return self.paper_name

    def set_orientation(self, orientation):
        """
        Set the paper orientation for the Book.
        @param orientation: orientation to set. Possible values are
            PAPER_LANDSCAPE or PAPER_PORTRAIT
        @type orientation: int
        """
        self.paper_orientation = orientation

    def get_orientation(self):
        """
        Return the paper orientation for the Book.
        @returns: returns the selected orientation. Valid values are
            PAPER_LANDSCAPE or PAPER_PORTRAIT
        @rtype: int
        """
        return self.paper_orientation

    def set_paper_metric(self, paper_metric):
        """
        Set the paper metric for the Book.
        @param paper_metric: whether to use metric.
        @type paper_metric: boolean
        """
        self.paper_metric = paper_metric

    def get_paper_metric(self):
        """
        Return the paper metric of the Book.
        @returns: returns whether to use metric
        @rtype: boolean
        """
        return self.paper_metric

    def set_custom_paper_size(self, paper_size):
        """
        Set the custom paper size for the Book.
        @param paper_size: paper size to set in cm.
        @type paper_size: [float, float]
        """
        self.paper_custom_size = paper_size

    def get_custom_paper_size(self):
        """
        Return the custom paper size for the Book.
        @returns: returns the custom paper size in cm
        @rtype: [float, float]
        """
        return self.paper_custom_size

    def set_margins(self, margins):
        """
        Set the paper margins for the Book.
        @param margins: margins to set. Possible values are floats in cm
        @type margins: [float, float, float, float]
        """
        self.paper_margins = copy.copy(margins)

    def get_margins(self):
        """
        Return the paper margins for the Book.
        @returns margins: returns the margins, floats in cm
        @rtype margins: [float, float, float, float]
        """
        return copy.copy(self.paper_margins)

    def set_margin(self, pos, value):
        """
        Set a paper margin for the Book.
        @param pos: Position of margin [left, right, top, bottom]
        @param value: floating point in cm
        @type pos: int
        @type value: float
        """
        self.paper_margins[pos] = value

    def get_margin(self, pos):
        """
        Return a paper margin for the Book.
        @param pos: Position of margin [left, right, top, bottom]
        @type pos: int
        @returns: float cm of margin
        @rtype: float
        """
        return self.paper_margins[pos]

    def set_format_name(self, format_name):
        """
        Set the format name for the Book.
        @param format_name: name of the format to set.
        @type format_name: str
        """
        self.paper_format = format_name

    def get_format_name(self):
        """
        Return the format name of the Book.
        @returns: returns the format name
        @rtype: str
        """
        return self.paper_format

    def set_output(self, output):
        """
        Set the output for the Book.
        @param output: name of the output to set.
        @type output: str
        """
        self.paper_output = output

    def get_output(self):
        """
        Return the output of the Book.
        @returns: returns the output name
        @rtype: str
        """
        return self.paper_output

#------------------------------------------------------------------------
#
# BookList class
#
#------------------------------------------------------------------------
class BookList(object):
    """
    Interface into the user-defined list of books.  

    BookList is loaded from a specified XML file if it exists.
    """

    def __init__(self, filename, dbase):
        """
        Create a new BookList from the books that may be defined in the 
        specified file.

        file:   XML file that contains book items definitions
        """
        self.dbase = dbase
        self.bookmap = {}
        self.file = os.path.join(HOME_DIR, filename)
        self.parse()
    
    def delete_book(self, name):
        """
        Remove a book from the list. Since each book must have a
        unique name, the name is used to delete the book.

        name:   name of the book to delete
        """
        del self.bookmap[name]

    def get_book_map(self):
        """
        Return the map of names to books.
        """
        return self.bookmap

    def get_book(self, name):
        """
        Return the Book associated with the name

        name:   name associated with the desired Book.
        """
        return self.bookmap[name]

    def get_book_names(self):
        "Return a list of all the book names in the BookList, sorted"
        return sorted(self.bookmap.keys())

    def set_book(self, name, book):
        """
        Add or replaces a Book in the BookList. 

        name:   name associated with the Book to add or replace.
        book:   definition of the Book
        """
        self.bookmap[name] = book

    def save(self):
        """
        Saves the current BookList to the associated file.
        """
        f = open(self.file, "w")
        f.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
        f.write('<booklist>\n')
        for name in sorted(self.bookmap): # enable a diff of archived copies
            book = self.get_book(name)
            dbname = book.get_dbname()
            f.write('<book name="%s" database="%s">\n' % (name, dbname) )
            for item in book.get_item_list():
                f.write('  <item name="%s" trans_name="%s">\n' % 
                            (item.get_name(),item.get_translated_name() ) )
                options = item.option_class.handler.options_dict
                for option_name in sorted(options.keys()): # enable a diff
                    option_value = options[option_name]
                    if isinstance(option_value, (list, tuple)):
                        f.write('    <option name="%s" value="" '
                                'length="%d">\n' % (
                                    escape(option_name),
                                    len(options[option_name]) ) )
                        for list_index in range(len(option_value)):
                            option_type = type_name(option_value[list_index])
                            value = escape(cuni(option_value[list_index]))
                            value = value.replace('"', '&quot;')
                            f.write('      <listitem number="%d" type="%s" '
                                    'value="%s"/>\n' % (
                                        list_index,
                                        option_type,
                                        value ) )
                        f.write('    </option>\n')
                    else:
                        option_type = type_name(option_value)
                        value = escape(cuni(option_value))
                        value = value.replace('"', '&quot;')
                        f.write('    <option name="%s" type="%s" '
                                'value="%s"/>\n' % (
                                    escape(option_name),
                                    option_type,
                                    value) )

                f.write('    <style name="%s"/>\n' % item.get_style_name() )
                f.write('  </item>\n')
            if book.get_paper_name():
                f.write('  <paper name="%s"/>\n' % book.get_paper_name() )
            if book.get_orientation() is not None: # 0 is legal
                f.write('  <orientation value="%s"/>\n' % 
                        book.get_orientation() )
            if book.get_paper_metric() is not None: # 0 is legal
                f.write('  <metric value="%s"/>\n' % book.get_paper_metric() )
            if book.get_custom_paper_size():
                size = book.get_custom_paper_size()
                f.write('  <size value="%f %f"/>\n' % (size[0], size[1]) )
            if book.get_margins():
                for pos in range(len(book.get_margins())):
                    f.write('  <margin number="%s" value="%f"/>\n' %
                                (pos, book.get_margin(pos)) )
            if book.get_format_name():
                f.write('  <format name="%s"/>\n' % book.get_format_name() )
            if book.get_output():
                f.write('  <output name="%s"/>\n' % book.get_output() )
            f.write('</book>\n')

        f.write('</booklist>\n')
        f.close()
        
    def parse(self):
        """
        Loads the BookList from the associated file, if it exists.
        """
        try:
            p = make_parser()
            p.setContentHandler(BookParser(self, self.dbase))
            the_file = open(self.file)
            p.parse(the_file)
            the_file.close()
        except (IOError, OSError, ValueError, SAXParseException, KeyError,
               AttributeError):
            pass


#-------------------------------------------------------------------------
#
# BookParser
#
#-------------------------------------------------------------------------
class BookParser(handler.ContentHandler):
    """
    SAX parsing class for the Books XML file.
    """
    
    def __init__(self, booklist, dbase):
        """
        Create a BookParser class that populates the passed booklist.

        booklist:   BookList to be loaded from the file.
        """
        handler.ContentHandler.__init__(self)
        self.dbase = dbase
        self.booklist = booklist
        self.b = None
        self.i = None
        self.o = None
        self.an_o_name = None
        self.an_o_value = None
        self.s = None
        self.bname = None
        self.iname = None
        
    def startElement(self, tag, attrs):
        """
        Overridden class that handles the start of a XML element
        """
        if tag == "book":
            self.b = Book()
            self.bname = attrs['name']
            self.b.set_name(self.bname)
            self.dbname = attrs['database']
            self.b.set_dbname(self.dbname)
            self.b_p_name = None
            self.b_p_orient = None
            self.b_p_metric = None
            self.b_p_size = None
            self.b_p_margins = None
            self.b_p_format = None
            self.b_p_output = None
        elif tag == "item":
            self.i = BookItem(self.dbase, attrs['name'])
            self.o = {}
        elif tag == "option":
            self.an_o_name = attrs['name']
            if 'length' in attrs:
                self.an_o_value = []
            else:
                converter = get_type_converter_by_name(attrs['type'])
                self.an_o_value = converter(attrs['value'])
        elif tag == "listitem":
            converter = get_type_converter_by_name(attrs['type'])
            self.an_o_value.append(converter(attrs['value']))
        elif tag == "style":
            self.s = attrs['name']
        elif tag == 'paper':
            self.b_p_name = attrs['name']
        elif tag == 'orientation':
            self.b_p_orient = int(attrs['value'])
        elif tag == 'metric':
            self.b_p_metric = int(attrs['value'])
        elif tag == 'size':
            width, height = attrs['value'].split()
            self.b_p_size = [float(width), float(height)]
        elif tag == 'margin':
            if self.b_p_margins is None:
                self.b_p_margins = [0.0, 0.0, 0.0, 0.0]
            self.b_p_margins[int(attrs['number'])] = float(attrs['value'])
        elif tag == 'format':
            self.b_p_format = attrs['name']
        elif tag == 'output':
            self.b_p_output = attrs['name']
        else:
            pass

    def endElement(self, tag):
        "Overridden class that handles the end of a XML element"
        if tag == "option":
            self.o[self.an_o_name] = self.an_o_value
        elif tag == "item":
            self.i.option_class.handler.options_dict.update(self.o)
            self.i.set_style_name(self.s)
            self.b.append_item(self.i)
        elif tag == "book":
            if self.b_p_name:
                self.b.set_paper_name(self.b_p_name)
            if self.b_p_orient is not None: # 0 is legal
                self.b.set_orientation(self.b_p_orient)
            if self.b_p_metric is not None: # 0 is legal
                self.b.set_paper_metric(self.b_p_metric)
            if self.b_p_size:
                self.b.set_custom_paper_size(self.b_p_size)
            if self.b_p_margins:
                self.b.set_margins(self.b_p_margins)
            if self.b_p_format:
                self.b.set_format_name(self.b_p_format)
            if self.b_p_output:
                self.b.set_output(self.b_p_output)
            self.booklist.set_book(self.bname, self.b)

#-------------------------------------------------------------------------
#
# Functions
#
#-------------------------------------------------------------------------
def append_styles(selected_style, item):
    """
    Append the styles for a book item to the stylesheet.
    """
    handler = item.option_class.handler

    # Set up default style
    handler.set_default_stylesheet_name(item.get_style_name())
    default_style = StyleSheet()
    make_default_style = item.option_class.make_default_style
    make_default_style(default_style)

    # Read all style sheets available for this item
    style_file = handler.get_stylesheet_savefile()
    style_list = StyleSheetList(style_file, default_style)

    # Get the selected stylesheet
    style_name = handler.get_default_stylesheet_name()
    style_sheet = style_list.get_style_sheet(style_name)

    for this_style_name in style_sheet.get_paragraph_style_names():
        selected_style.add_paragraph_style(
                this_style_name, 
                style_sheet.get_paragraph_style(this_style_name))

    for this_style_name in style_sheet.get_draw_style_names():
        selected_style.add_draw_style(
                this_style_name,
                style_sheet.get_draw_style(this_style_name))

    for this_style_name in style_sheet.get_table_style_names():
        selected_style.add_table_style(
                this_style_name,
                style_sheet.get_table_style(this_style_name))

    for this_style_name in style_sheet.get_cell_style_names():
        selected_style.add_cell_style(
                this_style_name,
                style_sheet.get_cell_style(this_style_name))

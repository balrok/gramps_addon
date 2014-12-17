#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2006  Donald N. Allingham
# Copyright (C) 2007-2009  Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2013       Paul Franklin
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
SVG document generator.
"""

#-------------------------------------------------------------------------
#
# python modules
#
#-------------------------------------------------------------------------
import sys
if sys.version_info[0] < 3:
    from StringIO import StringIO
else:
    from io import StringIO

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.plug.docgen import BaseDoc, DrawDoc, SOLID, FONT_SANS_SERIF
from gramps.gen.errors import ReportError
from gramps.gen.plug.menu import EnumeratedListOption
from gramps.gen.plug.report import DocOptions

#-------------------------------------------------------------------------
#
# SvgDrawDoc
#
#-------------------------------------------------------------------------
class SvgDrawDoc(BaseDoc, DrawDoc):

    def __init__(self, styles, type, options=None):
        BaseDoc.__init__(self, styles, type)
        self.f = None
        self.filename = None
        self.level = 0
        self.time = "0000-00-00T00:00:00"
        self.page = 0

        self._bg = 'none' # SVG background, in case options are ignored
        if options:
            menu = options.menu
            self._bg = menu.get_option_by_name('svg_background').get_value()
            if self._bg == 'transparent':
                self._bg = 'none'

    def open(self, filename):
        if filename[-4:] != ".svg":
            self.root = filename
        else:
            self.root = filename[:-4]

    def close(self):
        pass

    def start_page(self):
        self.page += 1
        if self.page != 1:
            name = "%s-%d.svg" % (self.root, self.page)
        else:
            name = "%s.svg" % self.root

        try:
            self.f = open(name,"w")
        except IOError as msg:
            raise ReportError(_("Could not create %s") % name, msg)
        except:
            raise ReportError(_("Could not create %s") % name)
        
        self.t = StringIO()
            
        width = self.paper.get_size().get_width()
        height = self.paper.get_size().get_height()

        self.f.write(
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.0//EN" '
            '"http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">\n'
            '<svg width="%5.2fcm" height="%5.2fcm" '
            'xmlns="http://www.w3.org/2000/svg">\n'
            '<rect width="%5.2fcm" height="%5.2fcm" '
            'style="fill: %s;"/>\n'
                % (width, height, width, height, self._bg)
            )

    def rotate_text(self, style, text, x, y, angle, mark=None):
        """ @param mark:  IndexMark to use for indexing (not supported) """
        style_sheet = self.get_style_sheet()
        stype = style_sheet.get_draw_style(style)
        pname = stype.get_paragraph_style()
        p = style_sheet.get_paragraph_style(pname)
        font = p.get_font()
        size = font.get_size()

        width = height = 0
        for line in text:
            width = max(width, self.string_width(font, line))
            height += size

        centerx, centery = units(( x+self.paper.get_left_margin(),
                                  y+self.paper.get_top_margin() ))
        xpos = (centerx - (width/2.0)) 
        ypos = (centery - (height/2.0)) 

        self.t.write(
            '<text ' +
            'x="%4.2f" y="%4.2f" ' % (xpos, ypos) +
            'transform="rotate(%d %4.2f %4.2f)" ' % (angle, centerx, centery) +
            'style="fill:#%02x%02x%02x; '% font.get_color()
            )
        if font.get_bold():
            self.t.write('font-weight:bold;')
        if font.get_italic():
            self.t.write('font-style:italic;')
        self.t.write('font-size:%d; ' % size)
        if font.get_type_face() == FONT_SANS_SERIF:
            self.t.write('font-family:sans-serif;')
        else:
            self.t.write('font-family:serif;')
        self.t.write('">')
    
        for line in text:
            # Center this line relative to the rest of the text
            linex = xpos + (width - self.string_width(font, line) ) / 2
            self.t.write(
                '<tspan x="%4.2f" dy="%d">' % (linex, size) +
                line +
                '</tspan>'
                )
        self.t.write('</text>\n')
                           
    def end_page(self):
        # Print the text last for each page so that it is rendered on top of 
        # other graphic elements.
        self.f.write(self.t.getvalue())
        self.t.close()
        self.f.write('</svg>\n')
        self.f.close()
    
    def draw_line(self, style, x1, y1, x2, y2):
        x1 += self.paper.get_left_margin()
        x2 += self.paper.get_left_margin()
        y1 += self.paper.get_top_margin()
        y2 += self.paper.get_top_margin()

        style_sheet = self.get_style_sheet()
        s = style_sheet.get_draw_style(style)

        line_out = '<line x1="%4.2fcm" y1="%4.2fcm" ' % (x1, y1)
        line_out += 'x2="%4.2fcm" y2="%4.2fcm" ' % (x2, y2)
        line_out += 'style="stroke:#%02x%02x%02x; ' % s.get_color()
        if s.get_line_style() != SOLID:
            line_out += 'stroke-dasharray: %s; ' % (
                ",".join(map(str, s.get_dash_style()))
                )
        line_out += 'stroke-width:%.2fpt;"/>\n' % s.get_line_width()
        self.f.write(line_out)

    def draw_path(self, style, path):
        style_sheet = self.get_style_sheet()
        stype = style_sheet.get_draw_style(style)

        point = path[0]
        line_out = '<polygon fill="#%02x%02x%02x"' % stype.get_fill_color()
        line_out += ' style="stroke:#%02x%02x%02x; ' % stype.get_color()
        if stype.get_line_style() != SOLID:
            line_out += 'stroke-dasharray: %s; ' % (
                ",".join(map(str, stype.get_dash_style()))
                )
        line_out += ' stroke-width:%.2fpt;"' % stype.get_line_width()
        line_out += ' points="%.2f,%.2f' % units((point[0]+self.paper.get_left_margin(),
                                                  point[1]+self.paper.get_top_margin()))
        self.f.write(line_out)
        for point in path[1:]:
            self.f.write(
                ' %.2f,%.2f'
                    % units((point[0]+self.paper.get_left_margin(),
                             point[1]+self.paper.get_top_margin()))
                )
        self.f.write('"/>\n')

    def draw_box(self, style, text, x, y, w, h, mark=None):
        """ @param mark:  IndexMark to use for indexing (not supported) """
        x += self.paper.get_left_margin()
        y += self.paper.get_top_margin()

        style_sheet = self.get_style_sheet()
        box_style = style_sheet.get_draw_style(style)

        if box_style.get_shadow():
            self.f.write(
                '<rect ' +
                'x="%4.2fcm" ' % (x+0.15) +
                'y="%4.2fcm" ' % (y+0.15) +
                'width="%4.2fcm" ' % w +
                'height="%4.2fcm" ' % h +
                'style="fill:#808080; stroke:#808080; stroke-width:1;"/>\n'
                )

        line_out = '<rect '
        line_out += 'x="%4.2fcm" ' % x
        line_out += 'y="%4.2fcm" ' % y
        line_out += 'width="%4.2fcm" ' % w
        line_out += 'height="%4.2fcm" ' % h
        line_out += 'style="fill:#%02x%02x%02x; ' % box_style.get_fill_color()
        line_out += 'stroke:#%02x%02x%02x; ' % box_style.get_color()
        if box_style.get_line_style() != SOLID:
            line_out += 'stroke-dasharray: %s; ' % (
                ",".join(map(str, box_style.get_dash_style()))
                )            
        line_out += 'stroke-width:%f;"/>\n' % box_style.get_line_width()
        self.f.write(line_out)

        if text:
            para_name = box_style.get_paragraph_style()
            assert( para_name != '' )
            p = style_sheet.get_paragraph_style(para_name)
            font = p.get_font()
            font_size = font.get_size()
            lines = text.split('\n')
            mar = 10/28.35
            fs = (font_size/28.35) * 1.2
            center = y + (h + fs)/2.0 + (fs*0.2)
            ystart = center - (fs/2.0) * len(lines)
            for i, line in enumerate(lines):
                ypos = ystart + (i * fs)
                self.t.write(
                    '<text ' +
                    'x="%4.2fcm" ' % (x+mar) +
                    'y="%4.2fcm" ' % ypos +
                    'style="fill:#%02x%02x%02x; '% font.get_color()
                    )
                if font.get_bold():
                    self.t.write(' font-weight:bold;')
                if font.get_italic():
                    self.t.write(' font-style:italic;')
                self.t.write(' font-size:%d;' % font_size)
                if font.get_type_face() == FONT_SANS_SERIF:
                    self.t.write(' font-family:sans-serif;')
                else:
                    self.t.write(' font-family:serif;')
                self.t.write(
                    '">' +
                    line +
                    '</text>\n'
                    )

    def draw_text(self, style, text, x, y, mark=None):
        """ @param mark:  IndexMark to use for indexing (not supported) """
        x += self.paper.get_left_margin()
        y += self.paper.get_top_margin()
        
        style_sheet = self.get_style_sheet()
        box_style = style_sheet.get_draw_style(style)
        para_name = box_style.get_paragraph_style()
        p = style_sheet.get_paragraph_style(para_name)
        
        font = p.get_font()
        font_size = font.get_size()
        fs = (font_size/28.35) * 1.2
        self.t.write(
            '<text ' +
            'x="%4.2fcm" ' % x +
            'y="%4.2fcm" ' % (y+fs) +
            'style="fill:#%02x%02x%02x;'% font.get_color()
            )
        if font.get_bold():
            self.t.write('font-weight:bold;')
        if font.get_italic():
            self.t.write('font-style:italic;')
        self.t.write('font-size:%d; ' % font_size)
        if font.get_type_face() == FONT_SANS_SERIF:
            self.t.write('font-family:sans-serif;')
        else:
            self.t.write('font-family:serif;')
        self.t.write(
            '">' +
            text +
            '</text>\n'
            )

    def center_text(self, style, text, x, y, mark=None):
        """ @param mark:  IndexMark to use for indexing (not supported) """
        style_sheet = self.get_style_sheet()
        box_style = style_sheet.get_draw_style(style)
        para_name = box_style.get_paragraph_style()
        p = style_sheet.get_paragraph_style(para_name)
        font = p.get_font()
        width = self.string_width(font, text) / 72
        x -= width
        self.draw_text(style, text, x, y)

def units(val):
    return (val[0]*35.433, val[1]*35.433)

#------------------------------------------------------------------------
#
# SvgDrawDocOptions class
#
#------------------------------------------------------------------------
class SvgDrawDocOptions(DocOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        DocOptions.__init__(self, name)
        
    def add_menu_options(self, menu):
        """
        Add options to the document menu for the docgen.
        """
        category_name = 'Document Options' # internal name: don't translate

        background = EnumeratedListOption(_('SVG background color'),
                                            'transparent')
        background.set_items([('transparent', _('transparent background')),
                              ('white', _('white')),
                              ('black', _('black')),
                              ('red', _('red')),
                              ('green', _('green')),
                              ('blue', _('blue')),
                              ('cyan', _('cyan')),
                              ('magenta', _('magenta')),
                              ('yellow', _('yellow')) ])
        background.set_help(_('The color, if any, of the SVG background'))
        menu.add_option(category_name, 'svg_background', background)

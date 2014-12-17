# -*- python -*-
# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2009  Serge Noiraud
# Copyright (C) 2008  Benny Malengier
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
Html Renderer
Can use the Webkit or Gecko ( Mozilla ) library
"""
#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
import os
import sys
if sys.version_info[0] < 3:
    from urlparse import urlunsplit
else:
    from urllib.parse import urlunsplit

#-------------------------------------------------------------------------
#
# set up logging
#
#-------------------------------------------------------------------------
import logging
_LOG = logging.getLogger("HtmlRenderer")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# Gramps Modules
#
#-------------------------------------------------------------------------
from gramps.gui.views.navigationview import NavigationView
from gramps.gui.views.bookmarks import PersonBookmarks
from gramps.gen.utils.file import get_empty_tempdir
from gramps.gen.constfunc import lin, mac, win
from gramps.gen.config import config
from gramps.gen.const import TEMP_DIR
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# Functions
#
#-------------------------------------------------------------------------

def get_identity():
    if lin():
        platform = "X11"
    elif win():
        platform = "Windows"
    elif mac():
        platform = "Macintosh"
    else:
        platform = "Unknown"
    lang = glocale.lang[:5].replace('_','-')
    return "Mozilla/5.0 (%s; U; %s) Gramps/3.2" % ( platform, lang)

#-------------------------------------------------------------------------
#
# Constants
#
#-------------------------------------------------------------------------
GEOVIEW_SUBPATH = get_empty_tempdir('geoview')
NOWEB   = 0
WEBKIT  = 1
MOZILLA = 2
KITNAME = [ "None", "WebKit", "Mozilla" ]
URL_SEP = '/'
MOZJS = '''
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", %(host)s);
user_pref("network.proxy.http_port", %(port)s);
user_pref("network.proxy.no_proxies_on",
 "127.0.0.1,localhost,localhost
 .localdomain")
user_pref("network.proxy.share_proxy_settings", true);
user_pref("network.http.proxy.pipelining", true);
user_pref("network.http.proxy.keep-alive", true);
user_pref("network.http.proxy.version", 1.1);
user_pref("network.http.sendRefererHeader, 0);
user_pref("general.useragent.extra.firefox, "Mozilla/5.0");
user_pref("general.useragent.locale, %(lang)s);
'''
#-------------------------------------------------------------------------
#
# What Web interfaces ?
#
# We use firstly webkit if it is present. If not, we use gtkmozembed.
# If no web interface is present, we don't register GeoView in the gui.
#-------------------------------------------------------------------------

TOOLKIT = NOWEB

try:
    from gi.repository import WebKit as webkit
    TOOLKIT = WEBKIT
except:
    pass

#no interfaces present, raise Error so that options for GeoView do not show
if TOOLKIT == NOWEB :
    raise ImportError('No GTK html plugin found')
else:
    _LOG.debug("webkit or/and mozilla (gecko) is/are loaded : %d" % TOOLKIT)

def get_toolkits():
    return TOOLKIT

#-------------------------------------------------------------------------
#
# Renderer
#
#-------------------------------------------------------------------------
#class Renderer(object):
class Renderer():
    """
    Renderer renders the webpage. Several backend implementations are 
    possible
    """
    def __init__(self):
        self.window = None

    def get_window(self):
        """
        Returns a container class with the widget that contains browser
        window
        """
        return self.window

    def get_uri(self):
        """
        Get the current url
        """
        raise NotImplementedError

    def show_all(self):
        """
        show all in the main window.
        """
        self.window.show_all()

    def open(self, url):
        """
        open the webpage at url
        """
        raise NotImplementedError

    def refresh(self):
        """
        We need to reload the page.
        """
        raise NotImplementedError

    def go_back(self):
        """
        Go to the previous page.
        """
        self.window.go_back()

    def can_go_back(self):
        """
        is the browser able to go backward ?
        """
        return self.window.can_go_back()

    def go_forward(self):
        """
        Go to the next page.
        """
        self.window.go_forward()

    def can_go_forward(self):
        """
        is the browser able to go forward ?
        """
        return self.window.can_go_forward()

    def get_title(self):
        """
        We need to get the html title page.
        """
        raise NotImplementedError

    def execute_script(self, url):
        """
        execute javascript in the current html page
        """
        raise NotImplementedError

    def page_loaded(self, *args):
        """
        The page is completely loaded.
        """
        raise NotImplementedError

    def set_button_sensitivity(self):
        """
        We must set the back and forward button in the HtmlView class.
        """
        raise NotImplementedError

#-------------------------------------------------------------------------
#
# Renderer with WebKit
#
#-------------------------------------------------------------------------
class RendererWebkit(Renderer):
    """
    Implementation of Renderer with Webkit
    """
    def __init__(self):
        Renderer.__init__(self)
        self.window = webkit.WebView()
        try:
            self.window.set_custom_encoding('utf-8') # needs webkit 1.1.10
        except: # pylint: disable-msg=W0702
            pass
        settings = self.window.get_settings()
        try:
            proxy = os.environ['http_proxy']
            # webkit use libsoup instead of libcurl.
            #if proxy:
            #    settings.set_property("use-proxy", True)
        except: # pylint: disable-msg=W0702
            pass
        try: # needs webkit 1.1.22
            settings.set_property("auto-resize-window", True) 
        except: # pylint: disable-msg=W0702
            pass
        try: # needs webkit 1.1.2
            settings.set_property("enable-private-browsing", True)
        except: # pylint: disable-msg=W0702
            pass
        #settings.set_property("ident-string", get_identity())
        # do we need it ? Yes if webkit avoid to use local files for security
        ## The following available starting from WebKitGTK+ 1.1.13
        #settings.set_property("enable-universal-access-from-file-uris", True)
        self.browser = WEBKIT
        self.title = None
        self.frame = self.window.get_main_frame()
        self.window.connect("document-load-finished", self.page_loaded)
        self.fct = None

    def page_loaded(self, *args):
        """
        We just loaded one page in the browser.
        Set the button sensitivity 
        """
        self.set_button_sensitivity()

    def set_button_sensitivity(self):
        """
        We must set the back and forward button in the HtmlView class.
        """
        self.fct()

    def open(self, url):
        """
        We need to load the page in the browser.
        """
        self.window.open(url)

    def refresh(self):
        """
        We need to reload the page in the browser.
        """
        self.window.reload()

    def execute_script(self, url):
        """
        We need to execute a javascript function into the browser
        """
        self.window.execute_script(url)

    def get_uri(self):
        """
        What is the uri loaded in the browser ?
        """
        return self.window.get_main_frame().get_uri()

#-------------------------------------------------------------------------
#
# HtmlView
#
#-------------------------------------------------------------------------
class HtmlView(NavigationView):
    """
    HtmlView is a view showing a top widget with controls, and a bottom part
    with an embedded webbrowser showing a given URL
    """

    def __init__(self, pdata, dbstate, uistate, title=_('HtmlView')):
        NavigationView.__init__(self, title, pdata, dbstate, uistate,
                                PersonBookmarks,
                                nav_group=0
                               )
        self.dbstate = dbstate
        self.back_action = None
        self.forward_action = None
        self.renderer = None
        self.urlfield = ""
        self.htmlfile = ""
        self.filter = Gtk.HBox()
        self.table = ""
        self.browser = NOWEB
        #self.bootstrap_handler = None
        self.box = None
        self.toolkit = None

        self.additional_uis.append(self.additional_ui())

    def build_widget(self):
        """
        Builds the interface and returns a Gtk.Container type that
        contains the interface. This containter will be inserted into
        a Gtk.Notebook page.
        """
        self.box = Gtk.VBox(homogeneous=False, spacing=4)
        #top widget at the top
        self.box.pack_start(self.top_widget(), False, False, 0 )
        #web page under it in a scrolled window
        #self.table = Gtk.Table(1, 1, False)
        self.toolkit = TOOLKIT = get_toolkits()
        self.renderer = RendererWebkit()
        self.frames = Gtk.HBox(homogeneous=False, spacing=4)
        frame = Gtk.ScrolledWindow(hadjustment=None,
                                                    vadjustment=None)
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        frame.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        frame.add(self.renderer.get_window())
        self.frames.set_homogeneous(False)
        self.frames.pack_start(frame, True, True, 0)
        self.frames.pack_end(self.filter, False, False, 0)
        self.box.pack_start(self.frames, True, True, 0)
        # this is used to activate the back and forward button
        # from the renderer class.
        self.renderer.fct = lambda: self.set_button_sensitivity
        self.renderer.show_all()
        self.filter.hide()
        #load a welcome html page
        urlhelp = self._create_start_page()
        self.open(urlhelp)
        return self.box

    def top_widget(self):
        """
        The default class gives a widget where user can type an url
        """
        hbox = Gtk.HBox(homogeneous=False, spacing=4)
        self.urlfield = Gtk.Entry()
        self.urlfield.set_text(config.get("htmlview.start-url"))
        self.urlfield.connect('activate', self._on_activate)
        hbox.pack_start(self.urlfield, True, True, 4)
        button = Gtk.Button(stock=Gtk.STOCK_APPLY)
        button.connect('clicked', self._on_activate)
        hbox.pack_start(button, False, False, 4)
        return hbox

    def set_button_sensitivity(self):
        """
        Set the backward and forward button in accordance to the browser.
        """
        self.forward_action.set_sensitive(self.renderer.can_go_forward())
        self.back_action.set_sensitive(self.renderer.can_go_back())
        
    def open(self, url):
        """
        open an url
        """
        self.renderer.open(url)

    def go_back(self, button):
        """
        Go to the previous loaded url.
        """
        self.renderer.go_back()
        self.set_button_sensitivity()
        self.external_uri()

    def go_forward(self, button):
        """
        Go to the next loaded url.
        """
        self.renderer.go_forward()
        self.set_button_sensitivity()
        self.external_uri()

    def refresh(self, button):
        """
        Force to reload the page.
        """
        self.renderer.refresh()

    def external_uri(self):
        """
        used to resize or not resize depending on external or local file.
        """
        uri = self.renderer.get_uri()

    def _on_activate(self, nobject):
        """
        Here when we activate the url button.
        """
        url = self.urlfield.get_text()
        if url.find('://') == -1:
            url = 'http://'+ url
        self.open(url)
        
    def build_tree(self):
        """
        Rebuilds the current display. Called from ViewManager
        """
        pass #htmlview is build on click and startup

    def get_stock(self):
        """
        Returns the name of the stock icon to use for the display.
        This assumes that this icon has already been registered 
        as a stock icon.
        """
        return 'gramps-view'
    
    def get_viewtype_stock(self):
        """Type of view in category
        """
        return 'gramps-view'

    def additional_ui(self):
        """
        Specifies the UIManager XML code that defines the menus and buttons
        associated with the interface.
        """
        return '''<ui>
          <toolbar name="ToolBar">
            <placeholder name="CommonNavigation">
              <toolitem action="Back"/>  
              <toolitem action="Forward"/>  
              <toolitem action="Refresh"/>
            </placeholder>
          </toolbar>
        </ui>'''

    def define_actions(self):
        """
        Required define_actions function for NavigationView. Builds the action
        group information required. 
        """
        NavigationView.define_actions(self)
        HtmlView._define_actions_fw_bw(self)

    def _define_actions_fw_bw(self):
        """
        prepare the forward and backward buttons.
        add the Backward action to handle the Backward button
        accel doesn't work in webkit and gtkmozembed !
        we must do that ...
        """
        self.back_action = Gtk.ActionGroup(name=self.title + '/Back')
        self.back_action.add_actions([
            ('Back', Gtk.STOCK_GO_BACK, _("_Back"), 
             "<ALT>Left", _("Go to the previous page in the history"), 
             self.go_back)
            ])
        self._add_action_group(self.back_action)
        # add the Forward action to handle the Forward button
        self.forward_action = Gtk.ActionGroup(name=self.title + '/Forward')
        self.forward_action.add_actions([
            ('Forward', Gtk.STOCK_GO_FORWARD, _("_Forward"), 
             "<ALT>Right", _("Go to the next page in the history"), 
             self.go_forward)
            ])
        self._add_action_group(self.forward_action)
        # add the Refresh action to handle the Refresh button
        self._add_action('Refresh', Gtk.STOCK_REFRESH, _("_Refresh"), 
                          callback=self.refresh,
                          accel="<Ctl>R",
                          tip=_("Stop and reload the page."))

    def init_parent_signals_for_map(self, widget, event):
        """
        TODO GTK3: No longer called
        Required to properly bootstrap the signal handlers.
        This handler is connected by build_widget.
        After the outside ViewManager has placed this widget we are
        able to access the parent container.
        """
        pass

    def get_renderer(self):
        """
        return the renderer : Webkit, Mozilla or None
        """
        #return self.browser
        return KITNAME[self.browser]

    def get_toolkit(self):
        """
        return the available toolkits : 1=Webkit, 2=Mozilla or 3=both
        """
        return self.toolkit

    def _create_start_page(self):
        """
        This command creates a default start page, and returns the URL of
        this page.
        """
        tmpdir = GEOVIEW_SUBPATH
        data = """
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" \
                 "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml"  >
         <head>
          <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
          <title>%(title)s</title>
         </head>
         <body >
           <H4>%(content)s</H4>
         </body>
        </html>
        """ % { 'height' : 600,
                'title'  : _('Start page for the Html View'),
                'content': _('Type a webpage address at the top, and hit'
                             ' the execute button to load a webpage in this'
                             ' page\n<br>\n'
                             'For example: <b>http://gramps-project.org</p>')
        }
        filename = os.path.join(tmpdir, 'startpage.html')
        # Now we have two views : Web and Geography, we need to create the
        # startpage only once.
        if not os.path.exists(filename):
            ufd = file(filename, "w+")
            ufd.write(data)
            ufd.close()
        return urlunsplit(('file', '',
                            URL_SEP.join(filename.split(os.sep)), '', ''))

    def navigation_group(self):
        """
        Return the navigation group.
        """
        return self.nav_group

    def navigation_type(self):
        return 'Person'

    def get_history(self):
        """
        Return the history object.
        """
        _LOG.debug("htmlrenderer : get_history" )
        return self.uistate.get_history(self.navigation_type(),
                                        self.navigation_group())

    def goto_handle(self, handle):
        _LOG.debug("htmlrenderer : gtoto_handle" )
        pass


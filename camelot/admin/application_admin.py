#  ============================================================================
#
#  Copyright (C) 2007-2016 Conceptive Engineering bvba.
#  www.conceptive.be / info@conceptive.be
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#      * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#      * Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#      * Neither the name of Conceptive Engineering nor the
#        names of its contributors may be used to endorse or promote products
#        derived from this software without specific prior written permission.
#  
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#  ============================================================================

import itertools
import logging
import os
import sys

logger = logging.getLogger('camelot.admin.application_admin')



from .action.base import Action
from .action.application_action import OpenTableView
from .admin_route import AdminRoute, register_list_actions
from .entity_admin import EntityAdmin
from .menu import MenuItem
from .object_admin import ObjectAdmin
from ..core.orm import Entity
from ..core.qt import Qt, QtCore
from camelot.admin.action import application_action, form_action, list_action
from camelot.view import art

#
# The translations data needs to be kept alive during the
# running of the application
#
_translations_data_ = []

class ApplicationAdmin(AdminRoute):
    """The ApplicationAdmin class defines how the application should look
like, it also ties Python classes to their associated 
:class:`camelot.admin.object_admin.ObjectAdmin` class or subclass.  It's
behaviour can be steered by overwriting its static attributes or it's
methods :

.. attribute:: name

    The name of the application, as it will appear in the title of the main
    window.

.. attribute:: application_url

    The url of the web site where the user can find more information on
    the application.

.. attribute:: help_url

    Points to either a local html file or a web site that contains the
    documentation of the application.

.. attribute:: author

    The name of the author of the application

.. attribute:: domain

    The domain name of the author of the application, eg 'mydomain.com', this
    domain will be used to store settings of the application.

.. attribute:: version

    A string with the version of the application

When the same action is returned in the :meth:`get_toolbar_actions` and 
:meth:`get_main_menu` method, it should be exactly the same object, to avoid
shortcut confusion and reduce the number of status updates.
    """

    name = 'Camelot'
    application_url = None
    help_url = 'http://www.python-camelot.com/docs.html'
    author = 'Conceptive Engineering'
    domain = 'python-camelot.com'

    version = '1.0'

    #
    # actions that will be shared between the toolbar and the main menu
    #
    list_toolbar_actions = [
        list_action.close_list,
        list_action.list_label,
    ]
    change_row_actions = [ list_action.to_first_row,
                           list_action.to_last_row ]
    edit_actions = [ list_action.add_new_object,
                     list_action.delete_selection,
                     list_action.duplicate_selection ]
    help_actions = []
    export_actions = [ list_action.print_preview,
                       list_action.export_spreadsheet ]
    form_toolbar_actions = [ form_action.CloseForm(),
                             form_action.ToFirstForm(),
                             form_action.ToPreviousForm(),
                             form_action.ToNextForm(),
                             form_action.ToLastForm(),
                             application_action.Refresh(),
                             form_action.ShowHistory() ]
    onetomany_actions = [ list_action.add_new_object,
                          list_action.delete_selection,
                          list_action.duplicate_selection,
                          list_action.export_spreadsheet ]
    manytomany_actions = [
        list_action.add_existing_object,
        list_action.remove_selection,
        list_action.export_spreadsheet ]

    def __init__(self, name=None, author=None, domain=None):
        #
        # Cache created ObjectAdmin objects
        #
        self._object_admin_cache = {}
        self._memento = None
        self.admins = {
            object: ObjectAdmin,
            Entity: EntityAdmin,
        }
        if name is not None:
            self.name = name
        if author is not None:
            self.author = author
        if domain is not None:
            self.domain = domain
        self._admin_route = super()._register_admin_route(self)
        self._main_menu = MenuItem()
        self._navigation_menu = MenuItem()

    def get_admin_route(self):
        return self._admin_route

    def register(self, entity, admin_class):
        """Associate a certain ObjectAdmin class with another class.  This
        ObjectAdmin will be used as default to render object the specified
        type.

        :param entity: :class:`class`
        :param admin_class: a subclass of 
            :class:`camelot.admin.object_admin.ObjectAdmin` or
            :class:`camelot.admin.entity_admin.EntityAdmin`
        """
        self.admins[entity] = admin_class

    def get_navigation_menu(self):
        """
        :return: a :class:`camelot.admin.menu.MenuItem` object
        """
        return self._navigation_menu

    def get_memento( self ):
        """Returns an instance of :class:`camelot.core.memento.SqlMemento` that
        can be used to store changes made to objects.  Overwrite this method to
        make it return `None` if no changes should be stored to the database, or
        to return another instance if the changes should be stored elsewhere.

        :return: `None` or an :class:`camelot.core.memento.SqlMemento` instance
        """
        from camelot.core.memento import SqlMemento
        if self._memento == None:
            self._memento = SqlMemento()
        return self._memento

    def get_application_admin( self ):
        """Get the :class:`ApplicationAdmin` class of this application, this
        method is here for compatibility with the :class:`ObjectAdmin`

        :return: this object itself
        """
        return self

    def get_related_admin(self, cls):
        """Get the default :class:`camelot.admin.object_admin.ObjectAdmin` class
        for a specific class, return None, if not known.  The ObjectAdmin
        should either be registered through the :meth:`register` method or be
        defined as an inner class with name :keyword:`Admin` of the entity.

        :param entity: a :class:`class`

        """
        return self.get_entity_admin( cls )

    def get_entity_admin(self, entity):
        """Get the default :class:`camelot.admin.object_admin.ObjectAdmin` class
        for a specific entity, return None, if not known.  The ObjectAdmin
        should either be registered through the :meth:`register` method or be
        defined as an inner class with name :keyword:`Admin` of the entity.

        :param entity: a :class:`class`

        deprecated : use get_related_admin instead
        """
        try:
            return self._object_admin_cache[entity]
        except KeyError:
            for cls in entity.__mro__:
                admin_class = self.admins.get(cls, None)
                if admin_class is None:
                    if hasattr(cls, 'Admin'):
                        admin_class = cls.Admin
                        break
                else:
                    break
            else:
                raise Exception('Could not construct a default admin class')
            admin = admin_class(self, entity)
            self._object_admin_cache[entity] = admin
            return admin

    def get_actions(self):
        """
        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that should be displayed on the desktop of the user.
        """
        return []

    @register_list_actions('_admin_route')
    def get_related_toolbar_actions( self, toolbar_area, direction ):
        """Specify the toolbar actions that should appear by default on every
        OneToMany editor in the application.

        :param toolbar_area: the position of the toolbar
        :param direction: the direction of the relation : 'onetomany' or 
            'manytomany'
        :return: a list of :class:`camelot.admin.action.base.Action` objects
        """
        if toolbar_area == Qt.ToolBarAreas.RightToolBarArea and direction == 'onetomany':
            return self.onetomany_actions
        if toolbar_area == Qt.ToolBarAreas.RightToolBarArea and direction == 'manytomany':
            return self.manytomany_actions

    def get_form_actions( self ):
        """Specify the action buttons that should appear on each form in the
        application.  
        The :meth:`camelot.admin.object_admin.ObjectAdmin.get_form_actions`
        method will call this method and prepend the result to the actions
        of that specific form.

        :return: a list of :class:`camelot.admin.action.base.Action` objects
        """
        return []

    def get_form_toolbar_actions( self, toolbar_area ):
        """
        :param toolbar_area: an instance of :class:`Qt.ToolBarArea` indicating
            where the toolbar actions will be positioned

        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that should be displayed on the toolbar of a form view.  return
            None if no toolbar should be created.
        """
        if toolbar_area == Qt.ToolBarAreas.TopToolBarArea:
            if sys.platform.startswith('darwin'):
                #
                # NOTE We remove the CloseForm from the toolbar action list
                #      on Mac because this regularly causes segfaults.
                #      The user can still close the form with the
                #      OS close button (i.e. "X").
                #
                return [action for action in self.form_toolbar_actions
                        if type(action) != form_action.CloseForm]
            return self.form_toolbar_actions

    @register_list_actions('_admin_route', '_toolbar_actions')
    def get_list_toolbar_actions( self ):
        """
        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that should be displayed on the toolbar of the application.  return
            None if no toolbar should be created.
        """
        return self.list_toolbar_actions + \
               self.edit_actions + \
               self.change_row_actions + \
               self.export_actions

    @register_list_actions('_admin_route', '_select_toolbar_actions')
    def get_select_list_toolbar_actions( self ):
        """
        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that should be displayed on the toolbar of the application.  return
            None if no toolbar should be created.
        """
        return self.list_toolbar_actions + self.change_row_actions

    def add_main_menu(self, verbose_name, icon=None, role=None, parent_menu=None):
        """
        add a new item to the main menu

        :return: a `MenuItem` object that can be used in subsequent calls to
            add other items as children of this item.
        """
        menu = MenuItem(verbose_name, icon, role=role)
        if parent_menu is None:
            parent_menu = self._main_menu
        parent_menu.items.append(menu)
        return menu

    def add_navigation_menu(self, verbose_name, icon=None, role=None, parent_menu=None):
        """
        add a new item to the navigation menu

        :return: a `MenuItem` object that can be used in subsequent calls to
            add other items as children of this item.
        """
        menu = MenuItem(verbose_name, icon, role=role)
        if parent_menu is None:
            parent_menu = self._navigation_menu
        parent_menu.items.append(menu)
        return menu

    def add_navigation_entity_table(self, entity, parent_menu, add_before=None):
        """
        Add an action to open a table view of an entity to the navigation menu
        """
        admin = self.get_related_admin(entity)
        return self.add_navigation_admin_table(admin, parent_menu, add_before)

    def add_navigation_admin_table(self, admin, parent_menu, add_before=None):
        """
        Add an action to open a table view for a specified admin
        """
        action = OpenTableView(admin)
        action_route = self._register_action_route(admin._admin_route, action)
        menu = MenuItem(action_route=action_route)
        if add_before is None:
            parent_menu.items.append(menu)
        else:
            parent_menu.items.insert(parent_menu.items.index(add_before), menu)
        return menu

    def add_navigation_action(self, action, parent_menu, role=None, add_before=None):
        action_route = self._register_action_route(self._admin_route, action)
        menu = MenuItem(action_route=action_route, role=role)
        if add_before is None:
            parent_menu.items.append(menu)
        else:
            parent_menu.items.insert(parent_menu.items.index(add_before), menu)
        return menu

    def add_main_action(self, action, parent_menu):
        assert isinstance(action, Action)
        assert isinstance(parent_menu, MenuItem)
        action_route = self._register_action_route(self._admin_route, action)
        parent_menu.items.append(MenuItem(action_route=action_route))

    def add_main_separator(self, parent_menu):
        assert isinstance(parent_menu, MenuItem)
        parent_menu.items.append(MenuItem())

    def get_main_menu(self) -> MenuItem:
        """
        :return: a :class:`camelot.admin.menu.MenuItem` object
        """
        return self._main_menu

    def get_name(self):
        """
        :return: the name of the application, by default this is the class
            attribute name"""
        return str( self.name )

    def get_version(self):
        """:return: string representing version of the application, by default this
                    is the class attribute verion"""
        return self.version

    def get_icon(self):
        """:return: the :class:`QtGui.QIcon` that should be used for the application"""
        from camelot.view.art import FontIcon
        return FontIcon('users').getQIcon() # 'tango/32x32/apps/system-users.png'

    def get_splashscreen(self):
        """:return: a :class:`QtGui.QPixmap` to be used as splash screen"""
        from camelot.view.art import Pixmap
        qpm = Pixmap('splashscreen.png').getQPixmap()
        img = qpm.toImage()
        # support transparency
        if not qpm.mask(): 
            if img.hasAlphaBuffer(): bm = img.createAlphaMask() 
            else: bm = img.createHeuristicMask() 
            qpm.setMask(bm) 
        return qpm

    def get_organization_name(self):
        """
        :return: a string with the name of the organization that wrote the
            application. By default returns the :attr:`ApplicationAdmin.author`
            attribute.
        """
        return self.author

    def get_organization_domain(self):
        """
        :return: a string with the domain name of the organization that wrote the
            application. By default returns the :attr:`ApplicationAdmin.domain`
            attribute.
        """
        return self.domain

    def get_help_url(self):
        """:return: a :class:`QtCore.QUrl` pointing to the index page for help"""
        if self.help_url:
            return QtCore.QUrl( self.help_url )

    def get_stylesheet(self):
        """
        :return: a string with the content of a qt stylesheet to be used for 
        this application as a string or None if no stylesheet needed.

        Camelot comes with a couple of default stylesheets :

         * stylesheet/office2007_blue.qss
         * stylesheet/office2007_black.qss
         * stylesheet/office2007_silver.qss

        Have a look at the default implementation to use another stylesheet.
        """
        #
        # Try to load a custom QStyle, if that fails use a stylesheet from
        # a file
        #
        try:
            from PyTitan import QtnOfficeStyle
            QtnOfficeStyle.setApplicationStyle( QtnOfficeStyle.Windows7Scenic )
        except:
            pass
        return art.read('stylesheet/office2007_blue.qss').decode('utf-8')


    @classmethod
    def _load_translator_from_file( cls, 
                                    module_name, 
                                    file_name, 
                                    directory = '', 
                                    search_delimiters = '_', 
                                    suffix = '.qm' ):
        """
        Tries to create a translator based on a file stored within a module.
        The file is loaded through the pkg_resources, to enable loading it from
        within a Python egg.  This method tries to mimic the behavior of
        :meth:`QtCore.QTranslator.load` while looking for an appropriate
        translation file.

        :param module_name: the name of the module in which to look for
            the translation file with pkg_resources.
        :param file_name: the filename of the the tranlations file, without 
            suffix
        :param directory: the directory, relative to the module in which
            to look for translation files
        :param suffix: the suffix of the filename
        :param search_delimiters: list of characters by which to split the file
            name to search for variations of the file name
        :return: :keyword:None if unable to load the file, otherwise a
            :obj:`QtCore.QTranslator` object.

        This method tries to load all file names with or without suffix, and
        with or without the part after the search delimiter.
        """
        from camelot.core.resources import resource_string

        #
        # split the directory names and file name
        #
        file_name_parts = [ file_name ]
        head, tail = os.path.split( file_name_parts[0] )
        while tail:
            file_name_parts[0] = tail
            file_name_parts = [ head ] + file_name_parts
            head, tail = os.path.split( file_name_parts[0] )
        #
        # for each directory and file name, generate all possibilities
        #
        file_name_parts_possibilities = []
        for file_name_part in file_name_parts:
            part_possibilities = []
            for search_delimiter in search_delimiters:
                delimited_parts = file_name_part.split( search_delimiter )
                for i in range( len( delimited_parts ) ):
                    part_possibility = search_delimiter.join( delimited_parts[:len(delimited_parts)-i] )
                    part_possibilities.append( part_possibility )
            file_name_parts_possibilities.append( part_possibilities )
        #
        # make the combination of all those possibilities
        #
        file_names = []
        for parts_possibility in itertools.product( *file_name_parts_possibilities ):
            file_name = os.path.join( *parts_possibility )
            file_names.append( file_name )
            file_names.append( file_name + suffix )
        #
        # now try all file names
        #
        translations = None
        for file_name in file_names:
            try:
                logger.debug( u'try %s'%file_name )
                translations = resource_string( module_name, os.path.join(directory,file_name) )
                break
            except IOError:
                pass
        if translations:
            _translations_data_.append( translations ) # keep the data alive
            translator = QtCore.QTranslator()
            # PySide workaround for missing loadFromData method
            if not hasattr( translator, 'loadFromData' ):
                return
            if translator.loadFromData( translations ):
                logger.info("add translation %s" % (directory + file_name))
                return translator

    def get_translator(self):
        """Reimplement this method to add application specific translations
        to your application.  The default method returns a list with the
        default Qt and the default Camelot translator for the current system
        locale.  Call :meth:`QLocale.setDefault` before this method is called
        if you want to load different translations then the system default.

        :return: a list of :obj:`QtCore.QTranslator` objects that should be 
            used to translate the application
        """
        translators = []
        qt_translator = QtCore.QTranslator()
        locale_name = QtCore.QLocale().name()
        logger.info( u'using locale %s'%locale_name )
        if qt_translator.load( "qt_" + locale_name,
                               QtCore.QLibraryInfo.path( QtCore.QLibraryInfo.LibraryPath.TranslationsPath ) ):
            translators.append(qt_translator)
        logger.debug("Qt translator found for {} : {}".format(locale_name, len(translators)>0))
        camelot_translator = self._load_translator_from_file(
            'camelot', 
            os.path.join( '%s/LC_MESSAGES/'%locale_name, 'camelot' ),
            'art/translations/'
        )
        logger.debug("Camelot translator found for {} : {}".format(locale_name, camelot_translator is not None))
        if camelot_translator:
            translators.append( camelot_translator )
        return translators

    def get_about(self):
        """:return: the content of the About dialog, a string with html
                    syntax"""
        import datetime
        from camelot.core import license
        today = datetime.date.today()
        return """<b>Camelot</b><br/>
                  Building desktop applications at warp speed
                  <p>
                  Copyright &copy; 2007-%s Conceptive Engineering.
                  All rights reserved.
                  </p>
                  <p>
                  %s
                  </p>
                  <p>
                  http://www.python-camelot.com<br/>
                  http://www.conceptive.be
                  </p>
                  """%(today.year, license.license_type)


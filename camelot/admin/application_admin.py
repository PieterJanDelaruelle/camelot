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

import six

from .object_admin import ObjectAdmin
from ..core.qt import Qt, QtCore
from camelot.admin.action import application_action, form_action, list_action
from camelot.core.utils import ugettext_lazy as _
from camelot.view import art

#
# The translations data needs to be kept alive during the
# running of the application
#
_translations_data_ = []

class ApplicationAdmin(object):
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
    change_row_actions = [ list_action.ToFirstRow(),
                           list_action.ToPreviousRow(),
                           list_action.ToNextRow(),
                           list_action.ToLastRow(), ]
    edit_actions = [ list_action.AddNewObject(),
                     list_action.DeleteSelection(),
                     list_action.DuplicateSelection(),]
    help_actions = [ application_action.ShowHelp(), ]
    export_actions = [ list_action.PrintPreview(),
                       list_action.ExportSpreadsheet() ]
    form_toolbar_actions = [ form_action.CloseForm(),
                             form_action.ToFirstForm(),
                             form_action.ToPreviousForm(),
                             form_action.ToNextForm(),
                             form_action.ToLastForm(),
                             application_action.Refresh(),
                             form_action.ShowHistory() ]
    hidden_actions = [ application_action.DumpState(),
                       application_action.RuntimeInfo() ]

    def __init__(self, name=None, author=None, domain=None):
        """Construct an ApplicationAdmin object and register it as the 
        prefered ApplicationAdmin to use througout the application"""
        #
        # Cache created ObjectAdmin objects
        #
        self._object_admin_cache = {}
        self._memento = None
        self.admins = {object: ObjectAdmin}
        if name is not None:
            self.name = name
        if author is not None:
            self.author = author
        if domain is not None:
            self.domain = domain

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

    def get_sections( self ):
        """A list of :class:`camelot.admin.section.Section` objects,
        these are the sections to be displayed in the left panel.

        .. image:: /_static/picture2.png
        """
        from camelot.admin.section import Section

        return [ Section( _('Relations'), self ),
                 Section( _('Configuration'), self ),
                 ]

    def get_settings( self ):
        """A :class:`QtCore.QSettings` object in which Camelot related settings
        can be stored.  This object is intended for Camelot internal use.  If an
        application specific settings object is needed, simply construct one.

        :return: a :class:`QtCore.QSettings` object
        """
        settings = QtCore.QSettings()
        settings.beginGroup( 'Camelot' )
        return settings

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
            self._object_admin_cache[admin_class] = admin
            return admin

    def get_actions(self):
        """
        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that should be displayed on the desktop of the user.
        """
        return []

    def get_hidden_actions( self ):
        """
        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that can only be triggered using shortcuts and are not visibile in
            the UI.
        """
        return self.hidden_actions

    def get_related_toolbar_actions( self, toolbar_area, direction ):
        """Specify the toolbar actions that should appear by default on every
        OneToMany editor in the application.

        :param toolbar_area: the position of the toolbar
        :param direction: the direction of the relation : 'onetomany' or 
            'manytomany'
        :return: a list of :class:`camelot.admin.action.base.Action` objects
        """
        if toolbar_area == Qt.RightToolBarArea and direction == 'onetomany':
            return [ list_action.AddNewObject(),
                     list_action.DeleteSelection(),
                     list_action.DuplicateSelection(),
                     list_action.ExportSpreadsheet(), ]
        if toolbar_area == Qt.RightToolBarArea and direction == 'manytomany':
            return [ list_action.AddExistingObject(),
                     list_action.RemoveSelection(),
                     list_action.ExportSpreadsheet(), ]

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
        if toolbar_area == Qt.TopToolBarArea:
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

    def get_main_menu( self ):
        """
        :return: a list of :class:`camelot.admin.menu.Menu` objects, or None if 
            there should be no main menu
        """
        from camelot.admin.menu import Menu

        return [ Menu( _('&File'),
                       [ application_action.Backup(),
                         application_action.Restore(),
                         None,
                         Menu( _('Export To'),
                               self.export_actions ),
                         Menu( _('Import From'),
                               [list_action.ImportFromFile()] ),
                         None,
                         application_action.Exit(),
                         ] ),
                 Menu( _('&Edit'),
                       self.edit_actions + [
                           None,
                           list_action.SelectAll(),
                           None,
                           list_action.ReplaceFieldContents(),   
                           ]),
                 Menu( _('View'),
                       [ application_action.Refresh(),
                         Menu( _('Go To'), self.change_row_actions) ] ),
                 Menu( _('&Help'),
                       self.help_actions + [
                           application_action.ShowAbout() ] )
                 ]

    def get_toolbar_actions( self, toolbar_area ):
        """
        :param toolbar_area: an instance of :class:`Qt.ToolBarArea` indicating
            where the toolbar actions will be positioned

        :return: a list of :class:`camelot.admin.action.base.Action` objects
            that should be displayed on the toolbar of the application.  return
            None if no toolbar should be created.
        """
        if toolbar_area == Qt.TopToolBarArea:
            return self.edit_actions + self.change_row_actions + \
                   self.export_actions + self.help_actions

    def get_name(self):
        """
        :return: the name of the application, by default this is the class
            attribute name"""
        return six.text_type( self.name )

    def get_version(self):
        """:return: string representing version of the application, by default this
                    is the class attribute verion"""
        return self.version

    def get_icon(self):
        """:return: the :class:`camelot.view.art.Icon` that should be used for the application"""
        from camelot.view.art import Icon
        return Icon('tango/32x32/apps/system-users.png').getQIcon()

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
                               QtCore.QLibraryInfo.location( QtCore.QLibraryInfo.TranslationsPath ) ):
            translators.append( qt_translator )
        camelot_translator = self._load_translator_from_file( 'camelot', 
                                                              os.path.join( '%s/LC_MESSAGES/'%locale_name, 'camelot' ),
                                                              'art/translations/' )
        if camelot_translator:
            translators.append( camelot_translator )
        else:
            logger.debug( 'no camelot translations found for %s'%locale_name )
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


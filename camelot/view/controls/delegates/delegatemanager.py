#  ============================================================================
#
#  Copyright (C) 2007-2013 Conceptive Engineering bvba. All rights reserved.
#  www.conceptive.be / info@conceptive.be
#
#  This file is part of the Camelot Library.
#
#  This file may be used under the terms of the GNU General Public
#  License version 2.0 as published by the Free Software Foundation
#  and appearing in the file license.txt included in the packaging of
#  this file.  Please review this information to ensure GNU
#  General Public Licensing requirements will be met.
#
#  If you are unsure which license is appropriate for your use, please
#  visit www.python-camelot.com or contact info@conceptive.be
#
#  This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
#  WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
#
#  For use of this library in commercial applications, please contact
#  info@conceptive.be
#
#  ============================================================================

import logging
logger = logging.getLogger('camelot.view.controls.delegates.delegatemanager')

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

from .plaintextdelegate import PlainTextDelegate

class DelegateManager(QtGui.QItemDelegate):
    """Manages custom delegates, should not be used by the application
  developer
  """

    def __init__(self, columns, parent=None):
        QtGui.QItemDelegate.__init__(self, parent)
        # set a delegate for the vertical header
        self.insertColumnDelegate(-1, PlainTextDelegate(parent=self))
        for i, c in enumerate(columns):
            field_name = c[0]
            logger.debug( 'creating delegate for %s' % field_name )
            delegate = c[1]['delegate'](parent = self, **c[1])
            self.insertColumnDelegate( i, delegate )

    def get_column_delegate(self, column):
        return self.findChild(QtGui.QAbstractItemDelegate, str(column))

    def insertColumnDelegate(self, column, delegate):
        """Inserts a custom column delegate"""
        assert delegate != None
        delegate.setParent(self)
        delegate.setObjectName(str(column))
        delegate.commitData.connect(self._commit_data)
        delegate.closeEditor.connect(self._close_editor)

    def _commit_data(self, editor):
        self.commitData.emit(editor)

    @QtCore.pyqtSlot( QtGui.QWidget, QtGui.QAbstractItemDelegate.EndEditHint )
    def _close_editor(self, editor, hint):
        self.closeEditor.emit(editor, hint )

    def paint(self, painter, option, index):
        """Use a custom delegate paint method if it exists"""
        delegate = self.get_column_delegate(index.column())
        delegate.paint(painter, option, index)

    def createEditor(self, parent, option, index):
        """Use a custom delegate createEditor method if it exists"""
        try:
            delegate = self.get_column_delegate(index.column())
            editor = delegate.createEditor(parent, option, index)
        except Exception, e:
            logger.error('Programming Error : could not createEditor editor data for editor at column %s'%(index.column()), exc_info=e)
            return QtGui.QWidget( parent = parent ) 
        return editor

    def setEditorData(self, editor, index):
        """Use a custom delegate setEditorData method if it exists"""
        logger.debug('setting editor data for column %s' % index.column())
        try:
            delegate = self.get_column_delegate(index.column())
            delegate.setEditorData(editor, index)
        except Exception, e:
            logger.error('Programming Error : could not set editor data for editor at column %s'%(index.column()), exc_info=e)
            logger.error('value that could not be set : %s'%unicode(index.model().data(index, Qt.EditRole)))

    def setModelData(self, editor, model, index):
        """Use a custom delegate setModelData method if it exists"""
        logger.debug('setting model data for column %s' % index.column())
        delegate = self.get_column_delegate(index.column())
        delegate.setModelData(editor, model, index)

    def sizeHint(self, option, index):
        option = QtGui.QStyleOptionViewItem()
        delegate = self.get_column_delegate(index.column())
        return delegate.sizeHint(option, index)


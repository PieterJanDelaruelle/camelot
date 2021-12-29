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

"""ModelContext, GuiContext and Actions that are used in the context of
editing a single field on a form or in a table.  This module contains the
various actions that are beyond the icons shown in the editors of a form.
"""

import os

from ...core.qt import QtWidgets, QtGui
from ...core.utils import ugettext_lazy as _
from ...admin.icon import Icon
from .base import Action, RenderHint
from .list_action import AddNewObjectMixin
from .application_action import ApplicationActionModelContext


class FieldActionModelContext( ApplicationActionModelContext ):
    """The context for a :class:`Action` on a field.  On top of the attributes of the
    :class:`camelot.admin.action.application_action.ApplicationActionGuiContext`,
    this context contains :

    .. attribute:: obj

       the object of which the field displays a field

    .. attribute:: field

       the name of the field that is being displayed

       attribute:: value

       the value of the field as it is displayed in the editor

    .. attribute:: field_attributes

        A dictionary of field attributes of the field to which the context
        relates.

    """

    def __init__(self):
        super( FieldActionModelContext, self ).__init__()
        self.obj = None
        self.field = None
        self.value = None
        self.field_attributes = {}


class FieldAction(Action):
    """Action class that renders itself as a toolbutton, small enough to
    fit in an editor"""

    name = 'field_action'
    render_hint = RenderHint.TOOL_BUTTON


class SelectObject(FieldAction):
    """Allows the user to select an object, and set the selected object as
    the new value of the editor"""

    icon = Icon('search') # 'tango/16x16/actions/system-search.png'
    tooltip = _('select existing')
    name = 'select_object'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        field_admin = model_context.field_attributes.get('admin')
        if field_admin is not None:
            selected_objects = yield action_steps.SelectObjects(field_admin)
            for selected_object in selected_objects:
                model_context.admin.set_field_value(
                    model_context.obj, model_context.field, selected_object
                )
                model_context.admin.set_defaults(model_context.obj)
                yield None
                break

    def get_state(self, model_context):
        state = super(SelectObject, self).get_state(model_context)
        state.visible = (model_context.value is None)
        state.enabled = model_context.field_attributes.get('editable', False)
        return state

class NewObject(SelectObject):
    """Open a form for the creation of a new object, and set this
    object as the new value of the editor"""

    icon = Icon('plus-circle') # 'tango/16x16/actions/document-new.png'
    tooltip = _('create new')
    name = 'new_object'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        admin = model_context.field_attributes['admin']
        admin = yield action_steps.SelectSubclass(admin)
        obj = admin.entity()
        # Give the default fields their value
        admin.add(obj)
        admin.set_defaults(obj)
        yield action_steps.UpdateEditor('new_value', obj)
        yield action_steps.OpenFormView(obj, admin.get_proxy([obj]), admin)

class OpenObject(SelectObject):
    """Open the value of an editor in a form view"""

    icon = Icon('folder-open') # 'tango/16x16/places/folder.png'
    tooltip = _('open')
    name = 'open_object'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        obj = model_context.value
        if obj is not None:
            admin = model_context.field_attributes['admin']
            admin = admin.get_related_admin(obj.__class__)
            yield action_steps.OpenFormView(obj, admin.get_proxy([obj]), admin)

    def get_state(self, model_context):
        state = super(OpenObject, self).get_state(model_context)
        state.visible = (model_context.value is not None)
        state.enabled = (model_context.value is not None)
        return state

class ClearObject(OpenObject):
    """Set the new value of the editor to `None`"""

    icon = Icon('eraser') # 'tango/16x16/actions/edit-clear.png'
    tooltip = _('clear')
    name = 'clear_object'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        yield action_steps.UpdateEditor('selected_object', None)

    def get_state(self, model_context):
        state = super(ClearObject, self).get_state(model_context)
        state.enabled = model_context.field_attributes.get('editable', False)
        return state

class UploadFile(FieldAction):
    """Upload a new file into the storage of the field"""

    icon = Icon('plus') # 'tango/16x16/actions/list-add.png'
    tooltip = _('Attach file')
    file_name_filter = 'All files (*)'
    name = 'attach_file'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        filenames = yield action_steps.SelectFile(self.file_name_filter)
        storage = model_context.field_attributes['storage']
        for file_name in filenames:
            # the storage cannot checkin empty file names
            if not file_name:
                continue
            remove = False
            if model_context.field_attributes.get('remove_original'):
                reply = yield action_steps.MessageBox(
                    text = _('Do you want to remove the original file?'),
                    icon = QtWidgets.QMessageBox.Icon.Warning,
                    title = _('The file will be stored.'),
                    standard_buttons = [QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.Yes]
                    )
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    remove = True
            yield action_steps.UpdateProgress(text='Attaching file')
            stored_file = storage.checkin(file_name)
            yield action_steps.UpdateEditor('value', stored_file, propagate=True)
            if remove:
                os.remove(file_name)

    def get_state(self, model_context):
        state = super(UploadFile, self).get_state(model_context)
        state.enabled = model_context.field_attributes.get('editable', False)
        state.enabled = (state.enabled is True) and (model_context.value is None)
        state.visible = (model_context.value is None)
        return state

class DetachFile(FieldAction):
    """Set the new value of the editor to `None`, leaving the
    actual file in the storage alone"""

    icon = Icon('trash') # 'tango/16x16/actions/edit-delete.png'
    tooltip = _('Detach file')
    message_title = _('Detach this file ?')
    message_text = _('If you continue, you will no longer be able to open this file.')
    name = 'detach_file'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        buttons = [QtWidgets.QMessageBox.StandardButton.Yes, QtWidgets.QMessageBox.StandardButton.No]
        answer = yield action_steps.MessageBox(title=self.message_title,
                                               text=self.message_text,
                                               standard_buttons=buttons)
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            yield action_steps.UpdateEditor('value', None, propagate=True)

    def get_state(self, model_context):
        state = super(DetachFile, self).get_state(model_context)
        state.enabled = model_context.field_attributes.get('editable', False)
        state.enabled = (state.enabled is True) and (model_context.value is not None)
        state.visible = (model_context.value is not None)
        return state

class OpenFile(FieldAction):
    """Open the file shown in the editor"""

    icon = Icon('folder-open') # 'tango/16x16/actions/document-open.png'
    tooltip = _('Open file')
    name = 'open_file'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        yield action_steps.UpdateProgress(text=_('Checkout file'))
        storage = model_context.field_attributes['storage']
        local_path = storage.checkout(model_context.value)
        yield action_steps.UpdateProgress(text=_('Open file'))
        yield action_steps.OpenFile(local_path)

    def get_state(self, model_context):
        state = super(OpenFile, self).get_state(model_context)
        state.enabled = model_context.value is not None
        state.visible = state.enabled
        return state

class SaveFile(OpenFile):
    """Copy the file shown in the editor to another location"""

    icon = Icon('save') # 'tango/16x16/actions/document-save-as.png'
    tooltip = _('Save as')
    name = 'file_save_as'

    def model_run(self, model_context, mode):
        from camelot.view import action_steps
        stored_file = model_context.value
        storage = model_context.field_attributes['storage']
        local_path = yield action_steps.SaveFile()
        with open(local_path, 'wb') as destination:
            yield action_steps.UpdateProgress(text=_('Saving file'))
            destination.write(storage.checkout_stream(stored_file).read())


class AddNewObject( AddNewObjectMixin, FieldAction ):
    """Add a new object to a collection. Depending on the
    'create_inline' field attribute, a new form is opened or not.

    This action will also set the default values of the new object, add the
    object to the session, and flush the object if it is valid.
    """

    shortcut = QtGui.QKeySequence.StandardKey.New
    icon = Icon('plus-circle') # 'tango/16x16/actions/document-new.png'
    tooltip = _('New')
    verbose_name = _('New')
    name = 'new_object'

    def get_admin(self, model_context, mode):
        """
        Return the admin used for creating and handling the new entity instance with.
        By default, the given model_context's admin is used.
        """
        return model_context.field_attributes.get('admin')

    def get_proxy(self, model_context, admin):
        return model_context.value

    def get_state( self, model_context ):
        assert isinstance(model_context, FieldActionModelContext)
        state = super().get_state( model_context )
        # Check for editability on the level of the field
        editable = model_context.field_attributes.get( 'editable', True )
        if editable == False:
            state.enabled = False
        # Check for editability on the level of the entity
        admin = self.get_admin(model_context, None)
        if admin and not admin.is_editable():
            state.visible = False
            state.enabled = False
        return state

add_new_object = AddNewObject()

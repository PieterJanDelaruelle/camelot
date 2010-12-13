#  ============================================================================
#
#  Copyright (C) 2007-2010 Conceptive Engineering bvba. All rights reserved.
#  www.conceptive.be / project-camelot@conceptive.be
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
#  visit www.python-camelot.com or contact project-camelot@conceptive.be
#
#  This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
#  WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
#
#  For use of this library in commercial applications, please contact
#  project-camelot@conceptive.be
#
#  ============================================================================

"""Helper functions related to the connection between the SQLAlchemy
ORM and the Camelot Views.
"""

import logging
logger = logging.getLogger('camelot.core.orm')

def refresh_session(session):
    """Session refresh expires all objects in the current session and sends
    a local entity update signal via the remote_signals mechanism"""
    logger.debug('session refresh requested')
    from camelot.view.model_thread import post

    def refresh_objects():
        from camelot.view.remote_signals import get_signal_handler
        signal_handler = get_signal_handler()
        refreshed_objects = []
        for _key, value in session.identity_map.items():
            session.refresh(value)
            refreshed_objects.append(value)
        for o in refreshed_objects:
            signal_handler.sendEntityUpdate(None, o)
        return refreshed_objects

    post( refresh_objects )
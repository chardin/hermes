# -*- coding: utf-8 -*-
"""app - Controller objects for the Hermes system.

This module supplies controller objects for use by views, scripts, and
other consumers.

Example:
    import app
    audio = AudioController()

"""

import model


class AudioController:
    """An audio controller in the Hermes system.

    This class provides resources for a consumer to interact with
    audio files in the Hermes system.

    """
    def __init__(self, user):
        self.username = User.username

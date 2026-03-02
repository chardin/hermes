# -*- coding: utf-8 -*-
"""app - Controller objects for the Hermes system.

This module supplies controller objects for use by views, scripts, and
other consumers.

Example:
    import app
    audio = AudioController()

"""

from sqlalchemy import exc
from model import session, add_to_session_and_commit, RenderedPhrase
import tempfile
from gtts import gTTS
from pydub import AudioSegment


class AudioController:
    """An audio controller in the Hermes system.

    This class provides resources for a consumer to interact with
    audio files in the Hermes system.

    """
    def __init__(self, lang='en'):
        self.lang = lang

    def get_rendered_phrase(self, phrase, force_regen=False):
        rp = False
        if (not force_regen):
            try:
                rp = session.query(RenderedPhrase).filter(RenderedPhrase.phrase == phrase, RenderedPhrase.lang == self.lang).one()
            except exc.NoResultFound as e:
                rp = False
        if (force_regen or not rp):
            mp3 = tempfile.NamedTemporaryFile(mode='w+b', suffix='.mp3')
            tts = gTTS(text=phrase, lang=self.lang)
            tts.save(mp3.name)
            mp3.flush()
            mp3_data = mp3.read()
            audio = AudioSegment.from_mp3(mp3.name)
        if rp:
            rp.mp3_data = mp3_data
            rp.duration = audio.duration_seconds
        else:
            rp = RenderedPhrase(phrase=phrase, lang=self.lang, mp3_data=mp3_data, duration=audio.duration_seconds)
        add_to_session_and_commit([rp])
        return rp

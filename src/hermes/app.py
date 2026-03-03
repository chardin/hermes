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
    def __init__(self, engine='gtts', lang='en'):
        self.lang = lang
        self.engine = engine

    def _rendered_phrase_audio(self, phrase, force_regen=False):
        mp3 = tempfile.NamedTemporaryFile(mode='w+b', suffix='.mp3', delete=False)

        rp = None
        mp3_data = None
        duration = None

        try:
            rp = session.query(RenderedPhrase).filter(RenderedPhrase.phrase == phrase, RenderedPhrase.lang == self.lang).one()
            mp3_data = rp.mp3_data
            duration = rp.duration
            mp3.write(rp.mp3_data)
            mp3.flush()
        except exc.NoResultFound as e:
            rp = None

        if (force_regen or not rp):
            tts = gTTS(text=phrase, lang=self.lang)
            tts.save(mp3.name)
            mp3.flush()
            mp3_data = mp3.read()
            audio = AudioSegment.from_mp3(mp3.name)
            duration = audio.duration_seconds

        if rp:
            if force_regen:
                rp.mp3_data = mp3_data
                rp.duration = duration
                add_to_session_and_commit([rp])            
        else:
            rp = RenderedPhrase(phrase=phrase, lang=self.lang, mp3_data=mp3_data, duration=duration)
            add_to_session_and_commit([rp])
        return mp3.name

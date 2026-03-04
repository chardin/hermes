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
import pydub


class AudioController:
    """An audio controller in the Hermes system.

    This class provides resources for a consumer to interact with
    audio files in the Hermes system.

    """
    def __init__(self, engine='gtts', lang='en', begin_set='Begin', begin_exercise='Begin',
                 prompt_before_next_exercise='Pause', pause_before_next_exercise = 5,
                 end_of_routine='Exercise routine finished.  Good job!'):
        self.lang = lang
        self.engine = engine
        self.begin_set = begin_set
        self.begin_exercise = begin_exercise
        self.prompt_before_next_exercise = prompt_before_next_exercise
        self.pause_before_next_exercise = pause_before_next_exercise
        self.end_of_routine = end_of_routine

    def _rendered_phrase_audio_path(self, phrase, force_regen=False):
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
            if (phrase == ' '):
                audio = pydub.AudioSegment.silent(duration=100)
                audio.export(mp3.name, format='mp3')
            else:
                tts = gTTS(text=phrase, lang=self.lang)
                tts.save(mp3.name)
            mp3.flush()
            mp3_data = mp3.read()
            audio = pydub.AudioSegment.from_mp3(mp3.name)
            duration = audio.duration_seconds

        if rp:
            if force_regen:
                rp.mp3_data = mp3_data
                rp.duration = duration
                add_to_session_and_commit([rp])            
        else:
            rp = RenderedPhrase(phrase=phrase, lang=self.lang, mp3_data=mp3_data, duration=duration)
            add_to_session_and_commit([rp])
        mp3.close()
        return mp3.name

    def _padded_phrase(self, rp_path, padded_duration=0):        
        audio = pydub.AudioSegment.from_file(rp_path, format='mp3')
        padding_msec = (padded_duration - audio.duration_seconds) * 1000
        if (padding_msec > 0):
            audio = audio + pydub.AudioSegment.silent(duration=padding_msec)

        padded_mp3 = tempfile.NamedTemporaryFile(mode='rb', suffix='.mp3', delete=False)
        audio.export(padded_mp3.name, format='mp3')
        padded_mp3.close()
        return padded_mp3.name

    def _build_sound_element_dict(self, routine):
        sound_element_dict = {routine.routine_id: self._padded_phrase(self._rendered_phrase_audio_path(routine.name)),
                              'begin_set': self._padded_phrase(self._rendered_phrase_audio_path(self.begin_set)),
                              'begin_exercise': self._padded_phrase(self._rendered_phrase_audio_path(self.begin_exercise)),
                              'prompt_before_next_exercise': self._padded_phrase(self._rendered_phrase_audio_path(self.prompt_before_next_exercise), self.pause_before_next_exercise),
                              'end_of_routine': self._padded_phrase(self._rendered_phrase_audio_path(self.end_of_routine)),
                              }
        for exercise in routine.exercises:
            if not (exercise.exercise_id in sound_element_dict):
                sound_element_dict[exercise.exercise_id] = self._padded_phrase(self._rendered_phrase_audio_path(exercise.name))
            for move in exercise.moves:
                if not (move.move_id in sound_element_dict):
                    sound_element_dict[move.move_id] = self._padded_phrase(self._rendered_phrase_audio_path(move.name), move.duration)

        return sound_element_dict

    def build_audio_for_routine(self, routine):
        mp3 = tempfile.NamedTemporaryFile(mode='w+b', suffix='.mp3', delete=False)

        sound_element_dict = self._build_sound_element_dict(routine)

        audio = pydub.AudioSegment.from_file(sound_element_dict[routine.routine_id], format='mp3')
        audio = audio + pydub.AudioSegment.silent(duration=2000)

        for exercise in routine.exercises:
            audio = audio + pydub.AudioSegment.from_file(sound_element_dict[exercise.exercise_id], format='mp3')
            audio = audio + pydub.AudioSegment.silent(duration=2000)
            
            audio = audio + pydub.AudioSegment.from_file(sound_element_dict['begin_exercise'], format='mp3')

            for i in range(1, exercise.num_sets):
                for j in range(1, exercise.num_reps):
                    for move in exercise.moves:
                        audio = audio + pydub.AudioSegment.from_file(sound_element_dict[move.move_id], format='mp3')
                        
                audio = audio + pydub.AudioSegment.from_file(sound_element_dict['begin_set'], format='mp3')

            audio = audio + pydub.AudioSegment.from_file(sound_element_dict['prompt_before_next_exercise'], format='mp3')

        audio = audio + pydub.AudioSegment.from_file(sound_element_dict['end_of_routine'], format='mp3')

        audio.export(mp3.name, format='mp3')

        return mp3.name

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

    def __init__(self, engine='gtts', lang='en', begin_set='Begin',
                 begin_exercise='Begin', prompt_before_next_exercise='Pause',
                 pause_before_next_exercise=5,
                 end_of_routine='Exercise routine finished.  Good job!'):
        """Initialize the audio controller.

        Args:
            engine (str): The engine to use to render text to voice.
                Optional.  Supports ``gtts`` only at this writing.
            lang (str): The ISO 639-1 languae code to use to render
                text.  Optional.  Defaults to ``en``.
            begin_set (str): The text to speak when beginning a set.
                Optional.  Defaults to ``Begin``.
            begin_exercise (str): The text to speak when beginning an
                exercise.  Optional.  Defaults to ``Begin``.
            prompt_before_next_exercise (str): The text to speak before
                the next exercise.  Optional.  Defaults to ``Pause``.
            pause_before_next_exercise (float): The delay in seconds before
                prompting the next exercise.  Optional.  Defaults to 5.
            end_of_routine (str): The text to speak when the routine is
                done.  Optional.  Defaults to ``Exercise routine finished.
                Good job!``

        Returns:
            None.
        """
        self.lang = lang
        self.engine = engine
        self.begin_set = begin_set
        self.begin_exercise = begin_exercise
        self.prompt_before_next_exercise = prompt_before_next_exercise
        self.pause_before_next_exercise = pause_before_next_exercise
        self.end_of_routine = end_of_routine

    def _rendered_phrase_audio_path(self, phrase, force_regen=False):
        """Return the path to an MP3 audio file for the given phrase.

        If the phrase is not yet stored as a RenderedPhrase, it is when
        this method is called successfully.  If the phrase exists in
        the database and ``force_regen`` is False, the audio is fetched
        from the database.

        Args:
            phrase (str): The text of the phrase to render.
            force_regen (bool): If True, the phrase is regenerated even if
                it already exists in the database.  Optional.  Defaults to
                False.

        Returns:
            The file path to the audio for the given phrase.
        """
        mp3 = tempfile.NamedTemporaryFile(mode='w+b', suffix='.mp3',
                                          delete=False)

        rp = None
        mp3_data = None

        try:
            rp = session.query(RenderedPhrase).\
                filter(RenderedPhrase.phrase == phrase,
                       RenderedPhrase.lang == self.lang,
                       RenderedPhrase.engine == self.engine).one()
            mp3_data = rp.mp3_data
            mp3.write(rp.mp3_data)
            mp3.flush()
        except exc.NoResultFound as e:
            rp = None

        if (force_regen or not rp):
            if phrase:
                tts = gTTS(text=phrase, lang=self.lang)
                tts.save(mp3.name)
            else:
                audio = pydub.AudioSegment.silent(duration=100)
                audio.export(mp3.name, format='mp3')
            mp3.flush()
            mp3_data = mp3.read()

        if rp:
            if force_regen:
                rp.mp3_data = mp3_data
                add_to_session_and_commit([rp])
        else:
            rp = RenderedPhrase(phrase=phrase,
                                lang=self.lang,
                                engine=self.engine,
                                mp3_data=mp3_data)
            add_to_session_and_commit([rp])
        mp3.close()
        return mp3.name

    def _padded_phrase(self, rp_path, padded_duration=0):
        """Return the path to an MP3 audio file with the specified padding.

        Args:
            rp_path (str): The path to the audio for the unpadded rendered
                phrase.
            padded_duration (float): The minimum duration in seconds of
                the padded audio.  Optional.  Defaults to 0.

        Returns:
            The file path to the padded audio.
        """
        audio = pydub.AudioSegment.from_file(rp_path, format='mp3')
        padding_msec = (padded_duration - audio.duration_seconds) * 1000
        if (padding_msec > 0):
            audio = audio + pydub.AudioSegment.silent(duration=padding_msec)

        padded_mp3 = tempfile.NamedTemporaryFile(mode='rb',
                                                 suffix='.mp3',
                                                 delete=False)
        audio.export(padded_mp3.name, format='mp3')
        padded_mp3.close()
        return padded_mp3.name

    def _build_sound_element_dict(self, routine):
        """Return a dict of generated audio for the given routine.

        The keys are globally unique IDs of entities in the Hermes
        system (the given routine, exercises for that routine, and
        moves for those exercises, and items in the AudioController
        to be rendered as sounds), and values indicating paths to
        the corresponding audio files.

        Args:
            routine (Routine): The routine for which to build the dict.

        Returns:
            The dict for the audio files.
        """
        sound_element_dict = {
            routine.routine_id: self._padded_phrase(
                self._rendered_phrase_audio_path(routine.name)),
            'begin_set': self._padded_phrase(
                self._rendered_phrase_audio_path(self.begin_set)),
            'begin_exercise': self._padded_phrase(
                self._rendered_phrase_audio_path(self.begin_exercise)),
            'prompt_before_next_exercise': self._padded_phrase(
                self._rendered_phrase_audio_path(
                    self.prompt_before_next_exercise),
                self.pause_before_next_exercise),
            'end_of_routine': self._padded_phrase(
                self._rendered_phrase_audio_path(self.end_of_routine)),
        }
        for exercise in routine.exercises:
            if not (exercise.exercise_id in sound_element_dict):
                sound_element_dict[exercise.exercise_id] = \
                    self._padded_phrase(self._rendered_phrase_audio_path(
                        exercise.name))
            for move in exercise.moves:
                if not (move.move_id in sound_element_dict):
                    sound_element_dict[move.move_id] = \
                        self._padded_phrase(self._rendered_phrase_audio_path(
                            move.name), move.duration)

        return sound_element_dict

    def build_audio_for_routine(self, routine):
        """Return the generated audio for the given routine.

        Args:
            routine (Routine): The routine for which to build the dict.

        Returns:
            The pathname to the generated audio.
        """
        mp3 = tempfile.NamedTemporaryFile(
            mode='w+b', suffix='.mp3', delete=False)

        sound_element_dict = self._build_sound_element_dict(routine)

        audio = pydub.AudioSegment.from_file(
            sound_element_dict[routine.routine_id], format='mp3')
        audio = audio + pydub.AudioSegment.silent(duration=2000)

        for exercise in routine.exercises:
            audio = audio + pydub.AudioSegment.from_file(
                sound_element_dict[exercise.exercise_id], format='mp3')
            audio = audio + pydub.AudioSegment.silent(duration=2000)

            audio = audio + pydub.AudioSegment.from_file(
                sound_element_dict['begin_exercise'], format='mp3')

            for i in range(1, exercise.num_sets):
                for j in range(1, exercise.num_reps):
                    for move in exercise.moves:
                        audio = audio + pydub.AudioSegment.from_file(
                            sound_element_dict[move.move_id], format='mp3')

                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict['begin_set'], format='mp3')

            audio = audio + pydub.AudioSegment.from_file(
                sound_element_dict['prompt_before_next_exercise'],
                format='mp3')

        audio = audio + pydub.AudioSegment.from_file(
            sound_element_dict['end_of_routine'], format='mp3')

        audio.export(mp3.name, format='mp3')

        return mp3.name

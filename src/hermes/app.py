# -*- coding: utf-8 -*-
"""app - Controller objects for the Hermes system.

This module supplies controller objects for use by views, scripts, and
other consumers.

Example:

.. code-block:: python3

    import app
    audio = AudioController()

"""

from sqlalchemy import exc
from model import session, add_to_session_and_commit, RenderedPhrase, \
    User, Routine
import tempfile
from gtts import gTTS
import pydub
import os
import random
import string
from passlib.context import CryptContext


class AudioController:
    """An audio controller in the Hermes system.

    This class provides resources for a consumer to interact with
    audio files in the Hermes system.
    """

    def __init__(self, verbose=False, engine='gtts', lang='en',
                 begin_set='Begin', begin_exercise='Begin',
                 prompt_before_next_exercise='Pause',
                 pause_before_next_exercise=5,
                 end_of_routine='Exercise routine finished.  Good job!'):
        """Initialize the audio controller.

        Args:
            verbose (bool): If True, produces verbose output on
                generating audio.  Defaults to False.
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
        self.verbose = verbose
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
        mp3_filename = self._generate_random_mp3_tempfile_name()
        rp = None
        mp3_data = None

        try:
            rp = session.query(RenderedPhrase).\
                filter(RenderedPhrase.phrase == phrase,
                       RenderedPhrase.lang == self.lang,
                       RenderedPhrase.engine == self.engine).one()
            mp3_data = rp.mp3_data
            with open(mp3_filename, 'wb') as mp3:
                mp3.write(mp3_data)
                mp3.close()
        except exc.NoResultFound:
            rp = None

        if (force_regen or not rp):
            if phrase:
                tts = gTTS(text=phrase, lang=self.lang)
                tts.save(mp3_filename)
            else:
                audio = pydub.AudioSegment.silent(duration=100)
                afh = audio.export(mp3_filename, format='mp3')
                afh.close()
            with open(mp3_filename, 'rb') as mp3:
                mp3_data = mp3.read()
                mp3.close()

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
        return mp3_filename

    def _padded_phrase(self, rp_path, padded_duration):
        """Return the path to an MP3 audio file with the specified padding.

        Args:
            rp_path (str): The path to the audio for the unpadded rendered
                phrase.
            padded_duration (float): The minimum duration in seconds of
                the padded audio.

        Returns:
            The file path to the padded audio.
        """
        audio = pydub.AudioSegment.from_file(rp_path, format='mp3')
        padding_msec = (padded_duration - audio.duration_seconds) * 1000
        if padding_msec > 0:
            audio = audio + pydub.AudioSegment.silent(duration=padding_msec)

        padded_mp3_filename = self._generate_random_mp3_tempfile_name()
        afh = audio.export(padded_mp3_filename, format='mp3')
        afh.close()
        os.unlink(rp_path)
        return padded_mp3_filename

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
            routine.routine_id:
                self._rendered_phrase_audio_path(routine.name),
            'begin_set':
                self._rendered_phrase_audio_path(self.begin_set),
            'begin_exercise':
                self._rendered_phrase_audio_path(self.begin_exercise),
            'prompt_before_next_exercise': self._padded_phrase(
                self._rendered_phrase_audio_path(
                    self.prompt_before_next_exercise),
                self.pause_before_next_exercise),
            'end_of_routine':
                self._rendered_phrase_audio_path(self.end_of_routine),
        }
        for exercise in routine.active_exercises():
            if not exercise.exercise_id in sound_element_dict:
                sound_element_dict[exercise.exercise_id] = \
                    self._padded_phrase(
                        self._rendered_phrase_audio_path(exercise.name), 5)
            for move in exercise.moves:
                if not move.move_id in sound_element_dict:
                    sound_element_dict[move.move_id] = \
                        self._padded_phrase(self._rendered_phrase_audio_path(
                            move.name), move.duration)

        return sound_element_dict

    def build_audio_for_routine(self, username, routine_name):
        """Return the generated audio for the given user and routine.

        Args:
            username (str): The user which to build the dict.
            routine_name (str): The routine for which to build the dict.

        Returns:
            The pathname to the generated audio.
        """
        user = session.query(User).\
            filter(User.username == username).one()
        routine = session.query(Routine).\
            filter(Routine.user_id == user.user_id,
                   Routine.name == routine_name).one()
        mp3_filename = self._generate_random_mp3_tempfile_name()

        if self.verbose:
            print('Initializing...')
        sound_element_dict = self._build_sound_element_dict(routine)

        if self.verbose:
            print('Speak routine name: ' + routine.name)
        audio = pydub.AudioSegment.from_file(
            sound_element_dict[routine.routine_id], format='mp3')
        audio = audio + pydub.AudioSegment.silent(duration=2000)

        for e_index in range(len(routine.active_exercises())):
            exercise = routine.active_exercises()[e_index]
            for i in range(exercise.num_sets):
                if self.verbose:
                    print('  Speak exercise name: ' + exercise.name)
                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict[exercise.exercise_id], format='mp3')
                if self.verbose:
                    print('  Speak begin exercise: ' + self.begin_exercise)
                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict['begin_exercise'], format='mp3')

                for _ in range(exercise.num_reps):
                    for move in exercise.moves:
                        if self.verbose:
                            print('    Speak move name: ' + move.name)
                        audio = audio + pydub.AudioSegment.from_file(
                            sound_element_dict[move.move_id], format='mp3')

                if i < exercise.num_sets - 1:
                    if self.verbose:
                        print('  Speak prompt before next set: ' +
                              self.prompt_before_next_exercise)
                    audio = audio + pydub.AudioSegment.from_file(
                        sound_element_dict['prompt_before_next_exercise'],
                        format='mp3')

            if e_index < len(routine.active_exercises()) - 1:
                if self.verbose:
                    print('  Speak prompt before next exercise: ' +
                          self.prompt_before_next_exercise)
                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict['prompt_before_next_exercise'],
                    format='mp3')

        if self.verbose:
            print('Speak end of routine: ' + self.end_of_routine)
        audio = audio + pydub.AudioSegment.from_file(
            sound_element_dict['end_of_routine'], format='mp3')

        afh = audio.export(mp3_filename, format='mp3')
        afh.close()

        for element_id, sound_file in sound_element_dict.items():
            try:
                os.unlink(sound_file)
            except OSError as e:
                print('Could not delete file for element' + element_id)
                raise e
        return mp3_filename

    def _generate_random_mp3_tempfile_name(self):
        random_string = ''.join(
            random.choices(string.ascii_letters + string.digits, k=10))
        return os.path.join(tempfile.gettempdir(), random_string + '.mp3')


class AuthController:
    """An authentication controller in the Hermes system.

    This class provides resources for a resource to check
    authentication and to change authentication credentials.
    """

    def __init__(self):
        self.ctx = CryptContext(
            schemes=['bcrypt'],
            deprecated='auto'
        )

    def set_password(self, username, password):
        """Set the password for the given user.

        Args:
            username (str): The user fior whom to set the password.
            password (str): The password to set.

        Returns:
            True on success,
        """
        if not username:
            raise ValueError('No username supplied!')
        if not password:
            raise ValueError('No password supplied!')

        user = session.query(User).filter(User.username == username).one()
        user.hashed_password = self.ctx.hash(password)
        add_to_session_and_commit([user])
        return True

    def is_valid_password(self, username, password):
        """Verifies the given password for the given user.

        Args:
            username (str): The user fior whom to check the password.
            password (str): The password to check.

        Returns:
            True if the password is valid, False otherwise.
        """
        if not username:
            raise ValueError('No username supplied!')
        if not password:
            raise ValueError('No password supplied!')
        user = session.query(User).filter(User.username == username).one()
        return self.ctx.verify(password, user.hashed_password)

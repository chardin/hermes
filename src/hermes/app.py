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
from config import Config
from model import session, add_to_session_and_commit, RenderedPhrase, \
    User, Routine, RoutineHistory, Exercise
import tempfile
from gtts import gTTS
import pydub
import os
import uuid
import random
import string
from passlib.context import CryptContext
from platformdirs import user_data_dir
from flask import Flask, render_template, flash, redirect, url_for, request, send_file
from flask_login import LoginManager, login_required, login_user, current_user, logout_user
from flask_pagedown import PageDown
from forms import LoginForm, PickRoutineForm, RecordRoutineForm

c = Config()


class AudioController:
    """An audio controller in the Hermes system.

    This class provides resources for a consumer to interact with
    audio files in the Hermes system.
    """

    def __init__(self, verbose=False, engine='gtts', lang='en',
                 audio_output_dir=None):
        """Initialize the audio controller.

        Args:
            verbose (bool): If True, produces verbose output on
                generating audio.  Defaults to False.
            engine (str): The engine to use to render text to voice.
                Optional.  Supports ``gtts`` only at this writing.
            lang (str): The ISO 639-1 languae code to use to render
                text.  Optional.  Defaults to ``en``.
            audio_output_dir (str): The directory to which to write audio
                files.  Defaults to ``platformdirs.user_data_dir('hermes')``.

        Returns:
            None.
        """
        self.verbose = verbose
        self.lang = lang
        self.engine = engine
        self.audio_output_dir = audio_output_dir
        if not self.audio_output_dir:
            data_dir = user_data_dir('hermes')
            self.audio_output_dir = data_dir

    def audio_output_path(self, username:str, routine_name:str) -> str:
        """Return the pathname for the potential generated audio
        for the given user and routine.

        Args:
            username (str): The user which to build the dict.
            routine_name (str): The routine for which to build the dict.

        Returns:
            The pathname to the potential generated audio.
        """
        userdir = os.path.join(self.audio_output_dir, username)
        os.makedirs(userdir, exist_ok=True)
        user = session.query(User).\
            filter(User.username == username).one()
        routine = session.query(Routine).\
            filter(Routine.user_id == user.user_id,
                   Routine.name == routine_name).one()
        return os.path.join(userdir, routine.routine_id + '.mp3')

    def _rendered_phrase_audio_path(self, phrase:str, force_regen:bool=False):
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

    def _padded_phrase(self, rp_path:str, padded_duration:float) -> str:
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

    def _build_sound_element_dict(self, routine) -> dict[str, str]:
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
                self._rendered_phrase_audio_path(
                    routine.user.get_prompt('begin_set')),
            'begin_exercise':
                self._rendered_phrase_audio_path(
                    routine.user.get_prompt('begin_exercise')),
            'prompt_before_next_exercise': self._padded_phrase(
                self._rendered_phrase_audio_path(
                    routine.user.get_prompt('prompt_before_next_exercise')),
                float(routine.user.get_prompt('pause_before_next_exercise'))),
            'end_of_routine':
                self._rendered_phrase_audio_path(
                    routine.user.get_prompt('end_of_routine')),
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

    def build_audio_for_routine(self, username:str, routine_name:str) -> str:
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

        mp3_filename = self.audio_output_path(username, routine_name)

        if self.verbose:
            print('Initializing...')
        sound_element_dict = self._build_sound_element_dict(routine)

        if self.verbose:
            print('Speak routine name: ' + routine.name)
        audio = pydub.AudioSegment.from_file(
            sound_element_dict.get(routine.routine_id, ''), format='mp3')
        audio = audio + pydub.AudioSegment.silent(duration=2000)

        for e_index in range(len(routine.active_exercises())):
            exercise = routine.active_exercises()[e_index]
            for i in range(exercise.num_sets):
                if self.verbose:
                    print('  Speak exercise name: ' + exercise.name)
                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict.get(exercise.exercise_id, ''),
                    format='mp3')
                if self.verbose:
                    print('  Speak begin exercise: ' + \
                          user.get_prompt('begin_exercise'))
                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict.get('begin_exercise', ''), format='mp3')

                for _ in range(exercise.num_reps):
                    for move in exercise.moves:
                        if self.verbose:
                            print('    Speak move name: ' + move.name)
                        audio = audio + pydub.AudioSegment.from_file(
                            sound_element_dict.get(move.move_id, ''),
                            format='mp3')

                if i < exercise.num_sets - 1:
                    if self.verbose:
                        print('  Speak prompt before next set: ' +
                              user.get_prompt('prompt_before_next_exercise'))
                    audio = audio + pydub.AudioSegment.from_file(
                        sound_element_dict.get(
                            'prompt_before_next_exercise', ''),
                        format='mp3')

            if e_index < len(routine.active_exercises()) - 1:
                if self.verbose:
                    print('  Speak prompt before next exercise: ' +
                          user.get_prompt('prompt_before_next_exercise'))
                audio = audio + pydub.AudioSegment.from_file(
                    sound_element_dict.get('prompt_before_next_exercise', ''),
                    format='mp3')

        if self.verbose:
            print('Speak end of routine: ' + user.get_prompt('end_of_routine'))
        audio = audio + pydub.AudioSegment.from_file(
            sound_element_dict.get('end_of_routine', ''), format='mp3')

        afh = audio.export(mp3_filename, format='mp3')
        afh.close()

        for element_id, sound_file in sound_element_dict.items():
            try:
                os.unlink(sound_file)
            except OSError as e:
                print('Could not delete file for element' + element_id)
                raise e

        routine.update_last_rendered()
        add_to_session_and_commit([routine])

        return mp3_filename

    def import_audio(self, phrase:str, mp3_filename:str) -> bool:
        audio = pydub.AudioSegment.from_mp3(mp3_filename)
        if len(audio) == 0:
            raise ValueError('No valid MP3 data found')
        with open(mp3_filename, 'rb') as mp3:
            mp3_data = mp3.read()
            mp3.close()
        try:
            rp = session.query(RenderedPhrase).\
                filter(RenderedPhrase.phrase == phrase,
                       RenderedPhrase.lang == self.lang,
                       RenderedPhrase.engine == self.engine).one()
            rp.mp3_data = mp3_data
        except exc.NoResultFound:
            rp = RenderedPhrase(phrase=phrase, mp3_data=mp3_data,
                                lang=self.lang, engine=self.engine)
        add_to_session_and_commit([rp])
        return True

    def get_stale_routines(self) -> list[dict]:
        """Return a list of dicts for stale routines.

        Returns:
            A list of dicts with the routine name and username for each
            stale routine.
        """
        return [{'routine_name': r.name,
                 'username': r.user.username} for r in Routine.stale_routines()]

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

    def set_password(self, username: str, password: str):
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

    def is_valid_password(self, username: str, password:str) -> bool:
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
        try:
            user = session.query(User).filter(User.username == username).one()
        except exc.NoResultFound:
            return False
        return self.ctx.verify(password, user.hashed_password)

app = Flask(__name__)
app.secret_key = c.config.get('flask', {}).get('secret_key', None)
if not app.secret_key:
    raise ValueError('No secret key given')

pagedown = PageDown(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.route('/')
def hello():
    """Return the index page.

    Returns the index page.
    """

    return '<B>Hello!</B>'

@login_manager.user_loader
def load_user(user_id:str):
    """Return the user with the guiven ID.

    Returns the user with the given ID.

    Args:
        user_id (str): The user ID to return,

    Returns:
        The user with that ID. Returns None if no such user ID
        is in the database.
    """

    try:
        user = session.query(User).filter(User.user_id == user_id).one()
    except exc.NoResultFound:
        return None
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Load and process the login page.

    Load the login page and process the credentials submitted.

    Redirects:
        * To the dashboard if the user is logged in.
        * To the login page if the user does not exist or
          the password is wrong.
        * To the dashboard if the username and password
          are valid.
    """

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        ac = AuthController()
        username = form.username.data
        if not ac.is_valid_password(username, form.password.data):
            flash('Username or password is not valid')
            return redirect('/login')
        user = session.query(User).filter(User.username == username).one()
        login_user(user, remember=form.remember_me.data)
        flash('Logged in successfully.')
        return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    """Load and process the dashboard.

    Load the dashboard page and process the user's choices.

    Redirects:
        * To the given routine, if selected.
        * To the logout page if selected.
    """

    form = PickRoutineForm()
    if form.validate_on_submit():
        return redirect(url_for('perform_routine',
                                routine_id=form.routine_choices.data))
    current_routines = [(r.routine_id, r.name) for r in current_user.routines]
    current_routines.sort(key=lambda x: x[1])
    form.routine_choices.choices = current_routines
    return render_template('dashboard.html', form=form)

@app.route('/perform_routine', methods=['GET', 'POST'])
@login_required
def perform_routine():
    """Load the page to serve routine audio and mark it done.

    Load the routine page, provides the means to play its
    associated audio and to mark the routine as done..

    Redirects:
        * To the dashboard, if the routine is unspecified,
          not found, or is not associated with the current user.
        * To the page for the given routine.
    """

    ac = AudioController()
    routine_id = request.args.get('routine_id', None)
    if not routine_id:
        flash('No routine specified')
        return redirect(url_for('dashboard'))
    try:
        routine = session.query(Routine).filter(
            Routine.routine_id == routine_id,
            Routine.user_id == current_user.user_id).one()
    except exc.NoResultFound:
        flash('That routine was not found for this user')
        return redirect(url_for('dashboard'))
    if not current_user.is_admin \
       and routine.user.user_id != current_user.user_id:
        flash('You are not the owner of this routine')
        return redirect(url_for('dashboard'))

    form = RecordRoutineForm()
    if form.validate_on_submit():
        rh = RoutineHistory(history_id=uuid.uuid4(),
                            user_id=current_user.user_id,
                            routine_id=routine.routine_id,
                            notes=form.notes.data)
        add_to_session_and_commit([rh])
        flash('History recorded')
        return redirect(url_for('dashboard'))
    return render_template('perform_routine.html', routine=routine,
                           mp3_path=ac.audio_output_path(
                               current_user.username, routine.name),
                           form=form)


@app.route('/play_routine/<routine_id>')
@login_required
def play_routine(routine_id):
    """Serve the audio for the given routine.

    Serves the MP3 audio for the given routine.

    Args:
        routine_id (str): The ID of the routine to serve.

    Redirects:
        * To the dashboard, if the routine is unspecified,
          not found, or is not associated with the current user.
    """
    try:
        routine = session.query(Routine).filter(
            Routine.routine_id == routine_id,
            Routine.user_id == current_user.user_id).one()
    except exc.NoResultFound:
        flash('That routine was not found for this user')
        return redirect(url_for('dashboard'))
    if not current_user.is_admin \
       and routine.user.user_id != current_user.user_id:
        flash('You are not the owner of this routine')
        return redirect(url_for('dashboard'))
    ac = AudioController()
    return send_file(ac.audio_output_path(current_user.username, routine.name),
                     mimetype='audio/mpeg')

@app.route('/routine_history', methods=['GET'])
@login_required
def routine_history():
    """List routine history items for the current user.

    Lists routine history items for the current user, arranged in
    descending date order. Contains links to view each history item.
    """

    num_rows = int(request.args.get('num_rows', 20))
    if num_rows < 1 or num_rows > 50:
        num_rows = 20
    page_num = int(request.args.get('page_num', 0))
    if page_num < 0:
        page_num = 0
    entries = session.query(RoutineHistory).filter(
        RoutineHistory.user_id == current_user.user_id).\
        order_by(RoutineHistory.exercise_dt.desc()).\
        offset(page_num * num_rows).limit(20).all()
    return render_template('routine_history.html', entries=entries)

@app.route('/history_detail', methods=['GET'])
@login_required
def history_detail():
    """Load the page to view a history item.
    """

    history_id = request.args.get('history_id', None)
    if not history_id:
        flash('No history specified')
        return redirect(url_for('dashboard'))
    try:
        history = session.query(RoutineHistory).filter(
            RoutineHistory.history_id == history_id).one()
    except exc.NoResultFound:
        flash('That history was not found')
        return redirect(url_for('dashboard'))
    if history.user_id != current_user.user_id:
        flash('You are not the owner of this history')
        return redirect(url_for('dashboard'))

    detail = history.routine_data
    detail['notes'] = history.notes
    return detail

@app.route('/routines', methods=['GET'])
@login_required
def routines():
    """Return a JSON list of objects to represent routines
    to be displayed in a menu for the current user.
    """
    return [ {r.routine_id: r.name} for r in current_user.routines ]

@app.route('/exercises/<routine_id>', methods=['GET'])
@login_required
def exercises(routine_id: str):
    """Return a JSON list of objects to represent exercises
    for the given routine to be displayed in a menu.
    """

    routine = session.query(Routine).\
        filter(Routine.routine_id == routine_id).one()
    if routine.user_id != current_user.user_id:
        return []
    return [ {e.exercise_id: e.name} for e in routine.exercises ]

@app.route('/moves/<exercise_id>', methods=['GET'])
@login_required
def moves(exercise_id: str):
    """Return a JSON list of objects to represent moved for
    the given exercise to be displayed in a menu.

    Either the current user must own the exercise
    or an admin user must own it.
    """

    exercise = session.query(Exercise).\
        filter(Exercise.exercise_id == exercise_id).one()
    if exercise.user_id != current_user.user_id:
        owner = session.query(User).\
            filter(User.user_id == exercise.user_id).one()
        if not owner.is_admin:
            return []
    return [ {m.move_id: m.name} for m in exercise.moves ]

@app.route('/logout')
@login_required
def logout():
    """Log out the current user.

    Logs out the current user.

    Redirects to the login page.
    """

    logout_user()
    return redirect(url_for('login'))

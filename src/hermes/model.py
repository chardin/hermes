# -*- coding: utf-8 -*-
"""model - Model objects for the Hermes system.

This module supplies model objects for use by the controllers.

Example:

.. code-block:: python3

    import model
    user = User(username = "syndisrupt",
                full_name = "Syntactical Disruptorize")

"""

from config import Config
import datetime
from sqlalchemy import create_engine, Column, Integer, String, \
    Float, LargeBinary, Table, ForeignKey, UniqueConstraint, \
    Boolean, DateTime, JSON, Index, Text, insert, func, select, \
    or_, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, \
    declarative_mixin


c = Config()

engine = create_engine(c.config['db']['engine'])
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
Base = declarative_base()


@declarative_mixin
class UpdateMixin(object):
    """A mixin to allow an object to know when it was last updated.

    This mixin gives its consumers the abiloity to know when an object
    was last updated.

    Attributes:
        last_updated_dt (DateTime): The time at which the object was
            last updated.
    """

    last_updated_dt = Column(DateTime, default=func.now(), onupdate=func.now())


@declarative_mixin
class DeletedMixin(object):
    """A mixin to allow an object to know if is deleted.

    This mixin gives its consumers the abiloity to know if an object
    is deleted.

    TODO: Propagate this through all relationships.

    Attributes:
        is_deleted (bool): True if the object is deleted.  Defaults to
            False.
    """

    is_deleted = Column(Boolean, nullable=False, default=False)


class User(Base, DeletedMixin):
    """A user in the Hermes system.

    This class holds and manages the details of a user.

    Attributes:
        user_id (str): The globally unique user ID.
        username (str): The unique username.
        full_name (str): The user's full name.
        hashed_password (str): The hashed password.
            A value of None means that the user requires no password.
        is_admin (bool): True if the current user is an admin,
            False otherwise.
    """

    __tablename__ = 'user'
    user_id = Column(String(36), primary_key=True, autoincrement=False)
    username = Column(String(16), unique=True, nullable=False)
    full_name = Column(String(64), nullable=False)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)

    routines = relationship('Routine', back_populates='user')
    routine_histories = relationship('RoutineHistory', back_populates='user')

    def to_dict(self) -> dict[str, str]:
        """Return a static dict of the data for the user.

        Returns a dict of the static daqta for the current user,
        suitable for rendering as JSON.
        """
        return {'username': self.username,
                'full_name': self.full_name}

    def available_exercises(self):
        """Return a list of exercises available to the current user.

        Returns a list of ``Exercise`` objects which are owned by
        either the current user or any admin user.
        """
        return session.query(Exercise).filter(
            or_(
                Exercise.user_id == self.user_id,
                Exercise.user_id.in_(u.user_id for u in User.admin_users())
            ), Exercise.is_deleted.is_(False)).all()

    @classmethod
    def admin_users(cls):
        """Return a list of admin users.

        Returns a list of ``User`` objects for which ``admin`` is true..
        """
        return session.query(cls).filter(bool(cls.is_admin)).all()


    """A relationship between an exercise and a routine in the Hermes system.

    This table holds and manages the details of the link between an
    exercise and a routine.

    Attributes:
        exercise_id (str): The ID for the exercise.
        routine_id (str): The ID for the routine.
        order (int): The order in which this exercise
            occurs within the routine.
        is_paused (bool): If True, this exercise is not
            included in the audio generated for this
            routine.  Defaults to False.
    """
exercise_to_routine_table = Table(
    'exercise_to_routine',
    Base.metadata,
    Column('exercise_id', ForeignKey('exercise.exercise_id'), nullable=False),
    Column('routine_id', ForeignKey('routine.routine_id'), primary_key=True),
    Column('order', Integer, primary_key=True,
           autoincrement=False),
    Column('is_paused', Boolean, default=False),
    Column('last_updated_dt', DateTime, default=datetime.datetime.now,
           onupdate=datetime.datetime.now),
    Column('is_deleted', Boolean, default=False)
)


class Routine(Base, UpdateMixin, DeletedMixin):
    """A routine in the Hermes system.

    This class holds and manages the details of a routine.

    Attributes:
        routine_id (str): The globally unique ID of the routine.
        user_id (str): The user ID of the user who owns the routine.
        name (str): The name for the routine which is unique to that user.
        last_rendered_dt (DateTime): The last time audio was rendered
            for the routine.
    """

    __tablename__ = 'routine'
    routine_id = Column(String(36), primary_key=True, autoincrement=False,)
    user_id = Column(ForeignKey('user.user_id'), nullable=False)
    name = Column(String(64), nullable=False)
    last_rendered_dt = Column(DateTime, nullable=True)

    user = relationship('User', back_populates='routines')
    UniqueConstraint('user_id', 'name', name='uq_user_id_name',)

    routine_histories = relationship('RoutineHistory', back_populates='routine')
    exercises = relationship('Exercise', secondary=exercise_to_routine_table,
                             order_by=exercise_to_routine_table.c.order)

    def active_exercises(self):
        """Return active exercises for the current routine,

        Returns a list of active exercises in order for the current routine.
        """
        return session.query(Exercise).join(exercise_to_routine_table).\
            filter(exercise_to_routine_table.c.routine_id == self.routine_id,
                   exercise_to_routine_table.c.is_paused.is_(False)
            ).order_by(exercise_to_routine_table.c.order).all()

    def update_last_rendered(self):
        """Mark the current routine as rendered at execution time.

        Sets ``last_rendered_dt`` to the current database date and time.
        """
        self.last_rendered_dt = engine.connect().execute(func.now()).scalar()

    def is_rendering_stale(self):
        last_rendered = self.last_rendered_dt
        if not last_rendered:
            return True
        if last_rendered < self.last_updated_dt:
            return True
        for exercise in self.active_exercises():
            if exercise.more_recently_updated_than(last_rendered):
                return True
        return False

    def add_exercise(self, exercise: 'Exercise', is_paused=False):
        """Add an exercise to the current routine.

        Adds an exwercise to the end of the current routine.
        """
        current_order = session.scalar(
            select(func.count()).select_from(exercise_to_routine_table).filter(
                exercise_to_routine_table.c.routine_id == self.routine_id)
            )
        stmt = insert(exercise_to_routine_table).values(
            exercise_id=exercise.exercise_id,
            routine_id=self.routine_id,
            order=current_order+1,
            is_paused=is_paused
            )
        engine.connect().execute(stmt)

    def to_dict(self) -> dict[str, str]:
        """Return a static dict of the data for the routine.

        Returns a dict of the static daqta for the current routine,
        suitable for rendering as JSON.
        """
        routine = {'name': self.name,
                   'user': self.user.to_dict(),
                   'exercises': [exercise.to_dict()
                                 for exercise in self.active_exercises()]
                   }
        return routine


class Exercise(Base, UpdateMixin, DeletedMixin):
    """An exercise in the Hermes system.

    This class holds and manages the details of an exercise.

    Attributes:
        exercise_id (str): The globally unique ID for the exercise.
        name (str): The name of the exercise.
        num_sets (int): The number of sets for the exercise.
        num_reps (int): The number of reps per set for the exercise.
        supplemental_desc (str): The supplemental description
            for the exercise.  Optional.
        reference_video_url (str): A link to the reference video
            for the exercise.  Optional.
        user_id (str): The user ID of the user who owns the routine.
    """

    __tablename__ = 'exercise'
    exercise_id = Column(String(36), primary_key=True, autoincrement=False)
    name = Column(String(128), nullable=False)
    num_sets = Column(Integer, nullable=False)
    num_reps = Column(Integer, nullable=False)
    supplemental_desc = Column(Text)
    reference_video_url = Column(String(2048))
    user_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)

    UniqueConstraint('user_id', 'name', name='uq_user_id_name',)

    properties = relationship('ExerciseProperty', back_populates='exercise')
    moves = relationship('Move', back_populates='exercise',
                         order_by='Move.order')

    def add_property(self, name: str, value: str) -> 'ExerciseProperty':
        """Add or alters a property of an exercise.

        Args:
            name (str): The name of the property.
            value (str): The value of the property.

        Returns:
            The new property.
        """
        return ExerciseProperty(exercise_id=self.exercise_id,
                                name=name, value=value)

    def more_recently_updated_than(self, last_rendered):
        if last_rendered < self.last_updated_dt:
            return True
        for prop in self.properties:
            if last_rendered < prop.last_updated_dt:
                return True
        for move in self.moves:
            if last_rendered < move.last_updated_dt:
                return True
        return False

    def to_dict(self) -> dict[str, str]:
        """Return a static dict of the data for the exercise.

        Returns a dict of the static daqta for the current exercise,
        suitable for rendering as JSON.
        """
        exercise = {'name': self.name,
                    'num_sets': self.num_sets,
                    'num_reps': self.num_reps,
                    'supplemental_desc': self.supplemental_desc,
                    'reference_video_url': self.reference_video_url,
                    'properties': {property.name: property.value
                                   for property in self.properties},
                    'moves': [move.to_dict() for move in self.moves],
                    }
        return exercise


class ExerciseProperty(Base, UpdateMixin, DeletedMixin):
    """A property of aN exercise in the Hermes system.

    This class holds and manages the properties of an exercise.

    Attributes:
        exercise_id (str): The ID of the exercise.
        name (str): The name of the property.
        value (str): The value of the property.
    """

    __tablename__ = 'exercise_property'
    exercise_id = Column(ForeignKey('exercise.exercise_id'),
                         primary_key=True, autoincrement=False)
    name = Column(String(64), primary_key=True, autoincrement=False)
    value = Column(String(255), nullable=False)
    exercise = relationship('Exercise', back_populates='properties')


class Move(Base, UpdateMixin, DeletedMixin):
    """A move in the Hermes system.

    This class holds and manages the details of a move within an exercise.

    Attributes:
        move_id (str): The globally unique ID of the exercise.
        exercise_id (str): The ID of the exercise.
        order (int): The sequence number of the move within the exercise.
        duration (float): The duration in secondw of the move.
        name (str): The name of the move, for use
            in generating an audio hint prompting the user.
    """

    __tablename__ = 'move'
    move_id = Column(String(36), primary_key=True)
    exercise_id = Column(ForeignKey('exercise.exercise_id'), nullable=False)
    order = Column(Integer, nullable=False)
    duration = Column(Float, nullable=False)
    name = Column(String(64), nullable=False)

    exercise = relationship('Exercise', back_populates='move')
    UniqueConstraint('exercise_id', 'order', name='uq_exercise_id_order',)

    exercise = relationship('Exercise', back_populates='moves')

    def to_dict(self) -> dict[str, str]:
        """Return a static dict of the data for the move.

        Returns a dict of the static daqta for the current move,
        suitable for rendering as JSON.
        """
        move = {'duration': self.duration,
                'name': self.name
                }
        return move


class RenderedPhrase(Base):
    """A phrase rendered as a sound in the Hermes system.

    This class holds and manages the details of a phrase rendered as
    sound in the Hermes system.

    Attributes:
        phrase (str): The name to be rendered as a sound.  Optional.
        lang (str): The IETF language tag to read the text in.
            Optional. Defaults to ``en``:
        engine (str): The name of the rendering engine.  Optional.
            Defaults to ``gtts``:
        mp3_data (LargeBinary): The MP3 audio data of the rendered sound.
    """

    __tablename__ = 'rendered_phrase'
    phrase = Column(String(255), primary_key=True)
    lang = Column(String(2), primary_key=True, default='en')
    engine = Column(String(16), primary_key=True, default='gtts')
    mp3_data = Column(LargeBinary, nullable=False)


class RoutineHistory(Base):
    """An instance of a performed routine in the Hermes system.

    This class holds and manages the recorded history of the
    performance of routines in the Hermes system.  It is intended
    to record the routine as it was performed at the time.

    Attributes:
        history_id (str): The globally unique ID of the history item.
        user_id (str): The ID of the user who performed the routine,
        routine_id (str): The ID of the performed routine.
        exercise_dt (datetime): The date and time at which the
            routine was performed.
        routine_data (JSON): The static routine data recording what
            was performed.
    """

    def _get_routine_data(context):
        ro_id = context.get_current_parameters()['routine_id']
        if not ro_id:
            return None
        try:
            ro = session.query(Routine).filter(
                Routine.routine_id == ro_id).one()
        except exc.NoResultFound:
            return None
        return ro.to_dict()

    __tablename__ = 'routine_history'
    history_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('user.user_id'), nullable=False)
    routine_id = Column(String(36), ForeignKey('routine.routine_id'),
                        nullable=False)
    exercise_dt = Column(DateTime, server_default=func.now())
    routine_data = Column(JSON, nullable=False, default=_get_routine_data)

    user = relationship('User', back_populates='routine_histories')
    routine = relationship('Routine', back_populates='routine_histories')


Index('idx_eh_user_id', RoutineHistory.user_id)
Index('idx_eh_user_id_routine_id', RoutineHistory.user_id,
      RoutineHistory.routine_id)

def create_database():
    """Create all database tables within the schema.

    Creates all of the database tables in the model.
    """
    Base.metadata.create_all(engine)


def add_to_session_and_commit(items):
    """Add items to be stored and commit.

    Adds the given items to the current session and commits.
    """
    for item in items:
        session.add(item)

    session.commit()

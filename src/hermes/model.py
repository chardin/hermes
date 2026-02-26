# -*- coding: utf-8 -*-
"""
model - Model objects for the Hermes system.

This module supplies model objects for use by the controllers.

Example:
    import model

    user = User(username = "syndisrupt",
        full_name = "Syntactical Disruptorize")
    user.commit()

"""

from config import Config
from sqlalchemy import create_engine, Column, Integer, String, \
    Float, Table, ForeignKey, UniqueConstraint, insert, func, \
    select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

config = Config()

# Create engine
engine = create_engine(config['db']['engine'])

# Create a session
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
Base = declarative_base()


class User(Base):
    """A user in the Hermes system.

    This class holds and manages the details of a user.

    Attributes:
        user_id (str): The gliobally unique user ID.
        username (str): The globally unique username.
        full_name (str): The user's full name.
        hashed_password (str): The hashed password.
    """

    __tablename__ = 'user'
    user_id = Column(String, primary_key=True, autoincrement=False,
                     nullable=False)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String)
    routines = relationship('Routine', back_populates='user')


"""A relationship between an exercise and a routine in the Hermes system.

This table holds and manages the details of the link between an
exercise and a routine.

Attributes:
    exercise_id (int): The ID for the exercise.
    routine_id (int): The ID for the routine.
    order (int): The order in which this exercise
        occurs within the routine.
"""
exercise_to_routine_table = Table(
    'exercise_to_routine',
    Base.metadata,
    Column('exercise_id', ForeignKey('exercise.exercise_id')),
    Column('routine_id', ForeignKey('routine.routine_id'),
           primary_key=True),
    Column('order', Integer, primary_key=True,
           autoincrement=False, nullable=False),
)


class Routine(Base):
    """A routine in the Hermes system.

    This class holds and manages the details of a routine.

    Attributes:
        routine_id (str): The globally unique ID of the routine
        user_id (str): The user ID of the user who owns the routine.
        name (str): The name for the routine which is unique to that user.
    """

    __tablename__ = 'routine'
    routine_id = Column(String, primary_key=True, autoincrement=False,
                        nullable=False)
    user_id = Column(ForeignKey('user.user_id'), nullable=False)
    name = Column(String, nullable=False)
    user = relationship('User', back_populates='routines')
    UniqueConstraint('user_id', 'name', name='uq_user_id_name',)

    exercises = relationship('Exercise', secondary=exercise_to_routine_table)

    def add_exercise(self, exercise):
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
            order=current_order+1
            )
        engine.connect().execute(stmt)

    def to_dict(self):
        """Return a static dict of the data for the routine.

        Returns a dict of the static daqta for the current routine,
        suitable for rendering as JSON.
        """
        routine = {'name': self.name,
                   'user': {'full_name': self.user.full_name,
                            'username': self.user.username},
                   'exercises': map(
                       lambda exercise: exercise.to_dict(), self.exercises())
                   }
        return routine


class Exercise(Base):
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
        user_id (int): The user ID of the user who owns the routine.
            A value of 0 means the exercise is generic and has no owner.
    """

    __tablename__ = 'exercise'
    exercise_id = Column(String, primary_key=True, autoincrement=False,
                         nullable=False)
    name = Column(String, nullable=False)
    num_sets = Column(Integer, nullable=False)
    num_reps = Column(Integer, nullable=False)
    supplemental_desc = Column(String)
    reference_video_url = Column(String)
    user_id = Column(Integer, ForeignKey('user.user_id'))
    UniqueConstraint('user_id', 'name', name='uq_user_id_name',)

    properties = relationship('ExerciseProperty', back_populates='exercise')
    # moves: Mapped[List['Move']] = relationship(
    #    back_populates='exercise',
    #    order_by='order')

    def to_dict(self):
        """Return a static dict of the data for the exercise.

        Returns a dict of the static daqta for the current exercise,
        suitable for rendering as JSON.
        """
        exercise = {'name': self.name,
                    'num_sets': self.num_sets,
                    'num_reps': self.num_reps,
                    'supplemental_desc': self.supplemental_desc,
                    'reference_video_url': self.reference_video_url,
                    'properties': map(
                        lambda property: prop.to_dict(), self.properties()),
                    # 'moves': map(
                    #    lambda move: move.to_dict(), self.moves()),
                    }
        return exercise


class ExerciseProperty(Base):
    """A property of aN exercise in the Hermes system.

    This class holds and manages the properties of an exercise.

    Attributes:
        exercise_id (str): The ID of the exercise.
        name (str): The name of the property.
        value (str): The value of the property.
    """

    __tablename__ = 'exercise_property'
    exercise_id = Column(ForeignKey('exercise.exercise_id'), primary_key=True, autoincrement=False)
    name = Column(String, nullable=False, primary_key=True, autoincrement=False)
    value = Column(String, nullable=False)
    exercise = relationship('Exercise', back_populates='properties')

    def to_dict(self):
        """Return a static dict of the data for the property.

        Returns a dict of the static daqta for the current property,
        suitable for rendering as JSON.
        """
        property = {'name': self.name(),
                    'value': self.value()
                    }
        return property


def create_database():
    """Create all database tables within the schema.

    Creates all of the database tables.
    """
    Base.metadata.create_all(engine)


def add_to_session_and_commit(items):
    """Add items to be stored and commit.

    Adds the given items to the current session and commits.
    """
    for item in items:
        session.add(item)

    session.commit()

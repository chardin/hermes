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

from hermes.config import Config

from sqlalchemy import create_engine, Column, Integer, String, \
    Float, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship

config = Config()

# Create engine and base class
engine = create_engine(config.db.engine)
Base = declarative_base()

# Create a session
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()


class User(Base):
    """A user in the Hermes system.

    This class holds and manages the details of a user.

    Attributes:
        user_id (int): The gliobally unique user ID.
        username (str): The globally unique username.
        full_name (str): The user's full name.
        hashed_password (str): The hashed password.
    """

    __tablename__ = 'user'
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=False)
    hashed_password: Mapped[str] = mapped_column()
    routines: Mapped[List['Routine']] = relationship(back_populates='user')


class ExerciseToRoutine(Base):
    """A relationship between an exercise and a routine in the Hermes system.

    This class holds and manages the details of the link
    between an exercise and a routine.

    Attributes:
        exercise_id (int): The ID for the exercise.
        routine_id (int): The ID for the routine.
        order (int): The order in which this exercise
            occurs within the routine.
    """

    __tablename__ = 'exercise_to_routine'
    __table_args__ = (
        UniqueConstraint('routine_id', 'order',
                         name='uq_routine_id_order')
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey('exercise.exercise_id',
                                                        ondelete='CASCADE'),
                                             nullable=False)
    routine_id: Mapped[int] = mapped_column(ForeignKey('routine.routine_id',
                                                       ondelete='CASCADE'),
                                            nullable=False)
    order: Mapped[int] = mapped_column(nullable=False)
    exercise: Mapped['Exercise'] = relationship(
        back_populates='exercise_to_routine')
    routine: Mapped['Routine'] = relationship(
        back_populates='exercise_to_routine')


class Routine(Base):
    """A routine in the Hermes system.

    This class holds and manages the details of a routine.

    Attributes:
        user_id (int): The user ID of the user who owns the routine.
        name (str): The name for the routine which is unique to that user.
    """

    __tablename__ = 'routine'
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_id_name')
    )
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id',
                                                    ondelete='CASCADE'),
                                         nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    user: Mapped['User'] = relationship(back_populates='routine')
    exercises: Mapped[List['Exercise']] = relationship(
        secondary='exercise_to_routine',
        order_by='ExerciseToRoutine.sequence')

    def to_dict(self):
        """Return a static dict of the data for the routine.

        Returns a dict of the static daqta for the current routine,
        suitable for rendering as JSON.
        """
        routine = {'name': self.name(),
                   'user': {'full_name': self.user.full_name(),
                            'username': self.user.username()},
                   'exercises': map(
                       lambda exercise: exercise.to_dict(), self.exercises())
                   }
        return routine


class Exercise(Base):
    """An exercise in the Hermes system.

    This class holds and manages the details of an exercise.

    Attributes:
        exercise_id (int): The globally unique ID for the exercise.
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
    __table_args__ = (
        UniqueConstraint('user_id', 'name', 'version',
                         name='uq_user_id_name_version')
    )
    exercise_id: Mapped[int] = mapped_column(primary_key=True,
                                             autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    num_sets: Mapped[int] = mapped_column(nullable=False)
    num_reps: Mapped[int] = mapped_column(nullable=False)
    supplemental_desc: Mapped[str] = mapped_column()
    reference_video_url: Mapped[str] = mapped_column()
    user_id: Mapped[int] = mapped_column(ForeignKey('user.user_id',
                                                    ondelete='CASCADE'))
    properties: Mapped[List['ExerciseProperty']] = relationship(
        back_populates='exercise')
    moves: Mapped[List['Move']] = relationship(
        back_populates='exercise',
        order_by='order')

    def to_dict(self):
        """Return a static dict of the data for the exercise.

        Returns a dict of the static daqta for the current exercise,
        suitable for rendering as JSON.
        """
        exercise = {'name': self.name(),
                    'num_sets': self.num_sets(),
                    'num_reps': self.num_reps(),
                    'supplemental_desc': self.supplemental_desc(),
                    'reference_video_url': self.reference_video_url(),
                    'properties': map(
                        lambda property: prop.to_dict(), self.properties()),
                    'moves': map(
                        lambda move: move.to_dict(), self.moves()),
                    }
        return exercise


class ExerciseProperty(Base):
    """A property of aN exercise in the Hermes system.

    This class holds and manages the properties of an exercise.

    Attributes:
        exercise_id (int): The ID of the exercise.
        name (str): The name of the property.
        value (str): The value of the property.
    """

    __tablename__ = 'exercise_property'
    __table_args__ = (
        UniqueConstraint('exercise_id', 'name',
                         name='uq_exercise_id_name')
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey('exercise.exercise_id',
                                                        ondelete='CASCADE'))
    name: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[str] = mapped_column(nullable=False)
    exercise: Mapped['Exercise'] = relationship(
        back_populates='exercise_property')

    def to_dict(self):
        """Return a static dict of the data for the property.

        Returns a dict of the static daqta for the current property,
        suitable for rendering as JSON.
        """
        property = {'name': self.name(),
                    'value': self.value()
                    }
        return property


class Move(Base):
    """A move in the Hermes system.

    This class holds and manages the details of a move within an exercise.

    Attributes:
        exercise_id (int): The ID of the exercise.
        order (int): The sequence number of the move within the exercise.
        duration (float): The duration in secondw of the move.
        description (str): The description of the move, for use
            in generating an audio hint prompting the user.  Optional.
    """

    __tablename__ = 'move'
    __table_args__ = (
        UniqueConstraint('exercise_id', 'order',
                         name='uq_exercise_id_order')
    )
    exercise_id: Mapped[str] = mapped_column(ForeignKey('exercise.exercise_id',
                                                        ondelete='CASCADE'))
    order: Mapped[int] = mapped_column(nullable=False)
    duration: Mapped[float] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column()
    exercise: Mapped['Exercise'] = relationship(back_populates='move')

    def to_dict(self):
        """Return a static dict of the data for the move.

        Returns a dict of the static daqta for the current move,
        suitable for rendering as JSON.
        """
        move = {'duration': self.duration(),
                'description': self.description()
                }
        return move

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
    Float, Table, ForeignKey, UniqueConstraint
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
        user_id (int): The gliobally unique user ID.
        username (str): The globally unique username.
        full_name (str): The user's full name.
        hashed_password (str): The hashed password.
    """

    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String)
#    routines = relationship('Routine', back_populates='user')


def create_test_database():
    Base.metadata.create_all(engine)

    u0 = User(username='admin', full_name='Admin')
    u1 = User(username='chardin', full_name='Chuck Hardin', hashed_password='dummy')
    session.add(u0)
    session.add(u1)
    session.commit()

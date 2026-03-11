#!/usr/bin/env python3

import os
import sys

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))

import uuid
import yaml
from config import Config
from model import User, Routine, Exercise, \
    Move, create_database, session, \
    add_to_session_and_commit

config = Config()

create_database()

db_filename = sys.argv[1]
if not db_filename:
   print('Must supply a database filename!')
   exit(2)

with open(db_filename, 'r') as db_file:
   db_data = yaml.safe_load(db_file)
db_file.close()

user_by_username = {}
for user_datum in db_data.get('users', {}):
   u = User(user_id=str(uuid.uuid4()),
            username=user_datum['username'],
            full_name=user_datum['full_name'])
   user_by_username[user_datum['username']] = u
add_to_session_and_commit(user_by_username[username] for username in user_by_username)

routine_by_username_and_name = {}
for username in db_data.get('routines', {}):
   routine_by_username_and_name[username] = {}
   u = user_by_username[username]
   for routine_datum in db_data['routines'].get(username, {}):
      r = Routine(routine_id=str(uuid.uuid4()),
                  user_id=u.user_id,
                  name=routine_datum['name'])
      routine_by_username_and_name[username][routine_datum['name']] = r

for username in routine_by_username_and_name:
   add_to_session_and_commit(routine_by_username_and_name[username][name] for name in routine_by_username_and_name[username])

exercise_by_username_and_name = {}
moves = []
properties = []
for username in db_data.get('exercises', {}):
   u = user_by_username[username]
   exercise_by_username_and_name[username] = {}
   for exercise_datum in db_data['exercises'].get(username, {}):
      e = Exercise(exercise_id=str(uuid.uuid4()),
                   user_id=u.user_id,
                   name=exercise_datum['name'],
                   num_sets=exercise_datum['num_sets'],
                   num_reps=exercise_datum['num_reps'])
      exercise_by_username_and_name[username][exercise_datum['name']] = e
      add_to_session_and_commit([e])
      for property in exercise_datum.get('properties', []):
         ep = e.add_property(property['name'], property['value'])
         properties.append(ep)
      move_seq = 0
      for move_datum in exercise_datum.get('moves', []):
         m = Move(move_id=uuid.uuid4(),
                  exercise_id=e.exercise_id,
                  order=move_seq,
                  duration=move_datum['duration'],
                  name=move_datum.get('name', None))
         move_seq = move_seq + 1
         moves.append(m)

add_to_session_and_commit(properties)
add_to_session_and_commit(moves)

for username in db_data.get('routine_exercises', {}):
   for routine_name in db_data['routine_exercises'].get(username, {}):
      routine = routine_by_username_and_name[username][routine_name]
      for exercise_datum in db_data['routine_exercises'][username][routine_name]:
         exercise_name = exercise_datum['exercise']
         exercise = exercise_by_username_and_name[username][exercise_name]
         is_paused = exercise_datum.get('is_paused', False)
         routine.add_exercise(exercise, is_paused)

exit(0)

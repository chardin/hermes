#!/usr/bin/env python3

import os
import sys

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))

import uuid
import yaml
from config import Config
from model import User, Routine, Exercise, \
    Move, UserPrompt, create_database, session, \
    add_to_session_and_commit, RenderedPhrase
from sqlalchemy import exc

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
            username=user_datum.get('username', None),
            full_name=user_datum.get('full_name', None))
   user_by_username[user_datum['username']] = u
add_to_session_and_commit(user_by_username[username] for username in user_by_username)

routine_by_username_and_name = {}
for username in db_data.get('routines', {}):
   routine_by_username_and_name[username] = {}
   u = user_by_username[username]
   for routine_datum in db_data['routines'].get(username, {}):
      r = Routine(routine_id=str(uuid.uuid4()),
                  user_id=u.user_id,
                  name=routine_datum.get('name', None))
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
                   name=exercise_datum.get('name', None),
                   num_sets=exercise_datum.get('num_sets', None),
                   num_reps=exercise_datum.get('num_reps', None),
                   supplemental_desc=exercise_datum.get('supplemental_desc', None),
                   reference_video_url=exercise_datum.get('reference_video_url', None))
      exercise_by_username_and_name[username][exercise_datum['name']] = e
      add_to_session_and_commit([e])
      for property in exercise_datum.get('properties', []):
         ep = e.add_property(property.get('name', None), property.get('value', None))
         properties.append(ep)
      move_seq = 0
      for move_datum in exercise_datum.get('moves', []):
         m = Move(move_id=uuid.uuid4(),
                  exercise_id=e.exercise_id,
                  order=move_seq,
                  duration=move_datum.get('duration', None),
                  name=move_datum.get('name', None))
         move_seq = move_seq + 1
         moves.append(m)

add_to_session_and_commit(properties)
add_to_session_and_commit(moves)

for username in db_data.get('routine_exercises', {}):
   for routine_name in db_data['routine_exercises'].get(username, {}):
      routine = routine_by_username_and_name[username][routine_name]
      for exercise_datum in db_data['routine_exercises'][username][routine_name]:
         exercise_name = exercise_datum.get('exercise', None)
         exercise = exercise_by_username_and_name[username][exercise_name]
         is_paused = exercise_datum.get('is_paused', False)
         routine.add_exercise(exercise, is_paused)

rps = []
for rp_data in db_data.get('rendered_phrases', []):
   phrase = rp_data.get('phrase', None)
   if phrase:
      path_to_mp3 = rp_data.get('mp3_filename', None)
      if path_to_mp3:
         with open(path_to_mp3, 'rb') as mp3:
            mp3_data = mp3.read()
            mp3.close()
         try:
            rp = session.query(RenderedPhrase).\
               filter(RenderedPhrase.phrase == phrase).one()
            rp.mp3_data(mp3_data)
         except exc.NoResultFound as e:
            rp = RenderedPhrase(phrase=phrase, mp3_data=mp3_data)
         rps.append(rp)

add_to_session_and_commit(rps)

ups = []
for updatum in db_data.get('user_prompts', []):
   username = updatum.get('username', None)
   if username:
      u = user_by_username[username]
      tag = updatum.get('tag', None)
      prompt = updatum.get('prompt', None)
      if tag and prompt:
         up = UserPrompt(user_id=u.user_id, tag=tag, prompt=prompt)
         ups.append(up)
         
add_to_session_and_commit(ups)

exit(0)

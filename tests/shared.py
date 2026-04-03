import os
import tempfile
import uuid

def set_up_sqlite_database():
    sqlite_config_file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    engine = """
db:
  engine: 'sqlite:///:memory:'
prompt_defaults:
  pause_before_next_exercise: 5
  baz: 'wibble'
flask:
  secret_key: 'wibble'
"""
    sqlite_config_file.write(engine)
    sqlite_config_file.flush()

    os.environ['HERMES_CONFIG_FILE'] = sqlite_config_file.name
    return sqlite_config_file

def create_test_db():
    from model import User, Routine, Exercise, RenderedPhrase, \
        Move, RoutineHistory, UserPrompt, create_database, \
        add_to_session_and_commit

    create_database()

    u0 = User(user_id=str(uuid.uuid4()), username='admin',
              full_name='Admin', is_admin=True,
              timezone='Europe/London')
    u1 = User(user_id=str(uuid.uuid4()), username='chardin',
              full_name='Chuck Hardin', hashed_password='dummy',
              timezone='America/Denver')

    r0 = Routine(routine_id=str(uuid.uuid4()), user_id=u1.user_id,
                 name='Evening Routine')

    e0 = Exercise(exercise_id=str(uuid.uuid4()), name='Cat-Camel',
                  num_sets=2, num_reps=10, user_id=u0.user_id)
    e1 = Exercise(exercise_id=str(uuid.uuid4()), name='Supine Bridge',
                  num_sets=3, num_reps=10, user_id=u1.user_id)
    e2 = Exercise(exercise_id=str(uuid.uuid4()), name='Cat-Camel',
                  num_sets=2, num_reps=10, user_id=u1.user_id)

    add_to_session_and_commit([u0, u1, r0, e0, e1, e2])

    r0.add_exercise(e0)
    r0.add_exercise(e1)
    r0.add_exercise(e2, is_paused=True)

    ep00 = e0.add_property(name='Resistance Band', value='Black')
    ep10 = e1.add_property(name='Added Weight', value='0')

    m00 = Move(move_id=str(uuid.uuid4()), exercise_id=e0.exercise_id,
               order=0, duration=2, name='')
    m01 = Move(move_id=str(uuid.uuid4()), exercise_id=e0.exercise_id,
               order=1, duration=4, name='Arch')
    m02 = Move(move_id=str(uuid.uuid4()), exercise_id=e0.exercise_id,
               order=2, duration=5, name='Relax')
    m03 = Move(move_id=str(uuid.uuid4()), exercise_id=e0.exercise_id,
               order=3, duration=1, name='')
    m10 = Move(move_id=str(uuid.uuid4()), exercise_id=e1.exercise_id,
               order=0, duration=3, name='Up')
    m11 = Move(move_id=str(uuid.uuid4()), exercise_id=e1.exercise_id,
               order=1, duration=10, name='Hold')
    m12 = Move(move_id=str(uuid.uuid4()), exercise_id=e1.exercise_id,
               order=2, duration=3, name='Down')

    rp0 = RenderedPhrase(phrase='Nertz', mp3_data=b'aa')
    up0 = UserPrompt(user_id=u1.user_id, tag='foo', prompt='bar')
    add_to_session_and_commit([ep00, ep10, m00, m01, m02, m03, \
                               m10, m11, m12, rp0, up0])

    rh0 = RoutineHistory(history_id=str(uuid.uuid4()),
                         user_id=u1.user_id,
                         routine_id=r0.routine_id)
    add_to_session_and_commit([rh0])

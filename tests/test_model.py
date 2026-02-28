import unittest
import sys
import os
import tempfile
import uuid


def set_up_sqlite_database():
    temp_config_file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    engine = "db:\n  engine: \'sqlite:///:memory:\'"
    temp_config_file.write(engine)
    temp_config_file.flush()

    os.environ['HERMES_CONFIG_FILE'] = temp_config_file.name
    return temp_config_file


def create_test_db():
    create_database()

    u0 = User(user_id=str(uuid.uuid4()), username='admin',
              full_name='Admin')
    u1 = User(user_id=str(uuid.uuid4()), username='chardin',
              full_name='Chuck Hardin', hashed_password='dummy')
    r0 = Routine(routine_id=str(uuid.uuid4()), user_id=u1.user_id,
                 name='Evening Routine')
    e0 = Exercise(exercise_id=str(uuid.uuid4()), name='Cat-Camel',
                  num_sets=2, num_reps=10, user_id=None)
    e1 = Exercise(exercise_id=str(uuid.uuid4()), name='Supine Bridge',
                  num_sets=3, num_reps=10, user_id=u1.user_id)
    e2 = Exercise(exercise_id=str(uuid.uuid4()), name='Cat-Camel',
                  num_sets=2, num_reps=10, user_id=u1.user_id)
    r0.add_exercise(e2)
    r0.add_exercise(e1)
    ep00 = e0.add_property(name='Resistance Band', value='Black')
    ep10 = e1.add_property(name='Added Weight', value='0')
    m10 = Move(move_id=str(uuid.uuid4()), exercise_id=e1.exercise_id,
               order=0, duration=3, name='Up')
    m11 = Move(move_id=str(uuid.uuid4()), exercise_id=e1.exercise_id,
               order=1, duration=10, name='Hold')
    m12 = Move(move_id=str(uuid.uuid4()), exercise_id=e1.exercise_id,
               order=2, duration=3, name='Down')
    rp0 = RenderedPhrase(phrase_id=str(uuid.uuid4()), name='Up',
                         filename='/tmp/dummy.mp3') 
    add_to_session_and_commit([u0, u1, r0, e0, e1, e2, ep00,
                               ep10, m10, m11, m12, rp0])


sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))
temp_config_file = set_up_sqlite_database()

from config import Config
from model import User, Routine, Exercise, ExerciseProperty, \
    RenderedPhrase, Move, create_database, session, \
    add_to_session_and_commit

create_test_db()


class TestModel(unittest.TestCase):

    def test_user(self):
        user = session.query(User).filter(User.username == 'chardin').one()
        self.assertEqual(user.full_name, 'Chuck Hardin')

    def test_routine(self):
        routine = session.query(Routine).\
            filter(Routine.name == 'Evening Routine').one()
        self.assertEqual(len(routine.exercises), 2)

    def test_exercise(self):
        user = session.query(User).filter(User.username == 'chardin').one()
        exercise = session.query(Exercise).\
            filter(Exercise.name == 'Supine Bridge',
                   Exercise.user_id == user.user_id).one()
        self.assertEqual(exercise.num_sets, 3)
        self.assertEqual(exercise.num_reps, 10)
        self.assertEqual(exercise.to_dict(),
                         {'name': 'Supine Bridge',
                          'num_sets': 3,
                          'num_reps': 10,
                          'supplemental_desc': None,
                          'reference_video_url': None,
                          'properties': {'Added Weight': '0'},
                          'moves': [{'duration': 3,
                                     'name': 'Up'},
                                    {'duration': 10,
                                     'name': 'Hold'},
                                    {'duration': 3,
                                     'name': 'Down'}]
                          })

    def test_rendered_phrase(self):
        phrase = session.query(RenderedPhrase).filter(RenderedPhrase.name=='Up').one()
        self.assertEqual(phrase.filename, '/tmp/dummy.mp3')


os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

import time
import unittest
import os
from config import Config
from shared import set_up_sqlite_database, create_test_db

temp_config_file = set_up_sqlite_database()

from model import User, Routine, Exercise, RenderedPhrase, \
    RoutineHistory, session, add_to_session_and_commit

config = Config()
create_test_db()


class TestModel(unittest.TestCase):

    def test_user(self):
        user = session.query(User).filter(User.username == 'chardin').one()
        self.assertEqual(user.full_name, 'Chuck Hardin')
        self.assertTrue(not user.is_admin)
        user = session.query(User).filter(User.username == 'admin').one()
        self.assertTrue(user.is_admin)
        self.assertTrue(len(User.admin_users()), 1)
        self.assertEqual(len(user.available_exercises()), 3)
        self.assertTrue(user.is_authenticated)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_anonymous)
        self.assertEqual(user.get_id(), user.user_id)

    def test_routine(self):
        routine = session.query(Routine).\
            filter(Routine.name == 'Evening Routine').one()
        self.assertEqual(len(routine.exercises), 3)
        self.assertEqual(len(routine.active_exercises()), 2)
        before_update_dt = routine.last_updated_dt
        self.assertFalse(before_update_dt is None)
        self.assertTrue(routine.last_rendered_dt is None)
        self.assertEqual(len(Routine.stale_routines()), 1)
        routine.update_last_rendered()
        self.assertFalse(routine.last_rendered_dt is None)
        self.assertEqual(len(Routine.stale_routines()), 0)
        time.sleep(1)
        routine.name = 'foo'
        add_to_session_and_commit([routine])
        routine = session.query(Routine).\
            filter(Routine.name == 'foo').one()
        self.assertTrue(before_update_dt < routine.last_updated_dt)
        self.assertTrue(routine.is_rendering_stale())
        self.assertEqual(len(Routine.stale_routines()), 1)
        routine.name = 'Evening Routine'
        add_to_session_and_commit([routine])

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
        rp = session.query(RenderedPhrase).filter(
            RenderedPhrase.phrase=='Nertz').one()
        self.assertEqual(rp.mp3_data, b'aa')
        self.assertEqual(rp.lang, 'en')
        self.assertEqual(rp.engine, 'gtts')

    def test_routine_history(self):
        rhs = session.query(RoutineHistory).all()
        self.assertEqual(len(rhs), 1)
        self.assertEqual(rhs[0].routine_data['name'], 'Evening Routine')
        self.assertEqual(len(rhs[0].routine_data['exercises']), 2)

    def test_user_prompt(self):
        user = session.query(User).filter(User.username == 'chardin').one()
        self.assertEqual(user.get_prompt('foo'), 'bar')
        self.assertEqual(user.get_prompt('baz'), 'wibble')
        self.assertEqual(user.get_prompt('nada'), 'nada not specified')

os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

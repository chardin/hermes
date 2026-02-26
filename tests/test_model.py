import unittest
import sys
import os
import tempfile

def set_up_sqlite_database():
    temp_config_file=tempfile.NamedTemporaryFile(mode='w+t',delete=False)
    engine="db:\n  engine: \'sqlite:///:memory:\'"
    temp_config_file.write(engine)
    temp_config_file.flush()

    os.environ['HERMES_CONFIG_FILE']=temp_config_file.name
    return temp_config_file

def create_test_db():
    create_database()

    u0 = User(username='admin', full_name='Admin')
    u1 = User(username='chardin', full_name='Chuck Hardin',
              hashed_password='dummy')
    add_to_session_and_commit([u0, u1])

    r0 = Routine(user_id=u1.user_id, name='Evening Routine')
    e0 = Exercise(name='Supine Bridge', num_sets=3, num_reps=10,
                  user_id=u1.user_id)
    add_to_session_and_commit([r0, e0])

    r0.add_exercise(e0)
    add_to_session_and_commit([])

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))

temp_config_file=set_up_sqlite_database()

from config import Config

from model import User, Routine, Exercise, create_database,\
    session, add_to_session_and_commit

create_test_db()


class TestModel(unittest.TestCase):
    
    def test_user(self):
        user = session.query(User).filter(User.user_id == 1).one()
        self.assertEqual(user.username, 'admin')

    def test_routine(self):
        routine = session.query(Routine).filter(Routine.routine_id == 1).one()
        self.assertEqual(routine.user_id, 2)
        self.assertEqual(routine.name, 'Evening Routine')
        self.assertEqual(len(routine.exercises), 1)

os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

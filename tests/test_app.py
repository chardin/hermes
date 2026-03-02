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


sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))
temp_config_file = set_up_sqlite_database()

from app import AudioController
from config import Config
from model import RenderedPhrase, create_database, add_to_session_and_commit, session


c = Config()
create_test_db()

ac = AudioController()


class TestApp(unittest.TestCase):

    def test_vocalize_move(self):
        rp = ac.get_rendered_phrase('Up')
        self.assertEqual(rp.duration, 0.624)


temp_config_file.close()
os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

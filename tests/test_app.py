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

    rp0 = RenderedPhrase(phrase_id=str(uuid.uuid4()),
                         name='Up')
    rp1 = RenderedPhrase(phrase_id=str(uuid.uuid4()),
                         name='Down', filename='/tmp/dummy.mp3')
    add_to_session_and_commit([rp0, rp1])

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))
temp_config_file = set_up_sqlite_database()

import app
from config import Config
from model import RenderedPhrase, create_database, add_to_session_and_commit, session

c = Config()
create_test_db()

class TestApp(unittest.TestCase):

    def test_vocalize_move(self):
        rp = session.query(RenderedPhrase).filter(RenderedPhrase.name == 'Up').one()

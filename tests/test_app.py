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

ac = AudioController(lang='en')


class TestApp(unittest.TestCase):

    def test__rendered_phrase_audio(self):
        up_mp3_path = ac._rendered_phrase_audio('Up')
        rp = session.query(RenderedPhrase).filter(RenderedPhrase.phrase == 'Up', RenderedPhrase.lang == 'en').one()
        self.assertEqual(os.path.exists(up_mp3_path), True)
        self.assertEqual(rp.duration, 0.624)
        foo_mp3_path = ac._rendered_phrase_audio('Foo')
        rp = session.query(RenderedPhrase).filter(RenderedPhrase.phrase == 'Foo', RenderedPhrase.lang == 'en').one()
        self.assertEqual(rp.duration, 0.792)
        self.assertEqual(os.path.exists(foo_mp3_path), True)
        foo_mp3_path = ac._rendered_phrase_audio('Foo', force_regen=True)
        self.assertEqual(os.path.exists(foo_mp3_path), True)
        bar_mp3_path = ac._rendered_phrase_audio('Bar', force_regen=True)
        self.assertEqual(os.path.exists(bar_mp3_path), True)
        os.unlink(up_mp3_path)
        os.unlink(foo_mp3_path)
        os.unlink(bar_mp3_path)

temp_config_file.close()
os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

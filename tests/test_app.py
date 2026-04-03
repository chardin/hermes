import unittest
import os
import pydub
from config import Config
from shared import set_up_sqlite_database, create_test_db

temp_config_file = set_up_sqlite_database()

from app import app, AudioController, AuthController
from model import Routine, session

c = Config()
create_test_db()

ac = AudioController(audio_output_dir='/tmp')
auc = AuthController()

class TestApp(unittest.TestCase):

    def test__000_rendered_phrase_audio_path(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        up_mp3_path = ac._rendered_phrase_audio_path('Up')
        audio = pydub.AudioSegment.from_file(up_mp3_path)
        self.assertTrue(abs(audio.duration_seconds - 0.624) < 0.01)
        os.unlink(up_mp3_path)
        foo_mp3_path = ac._rendered_phrase_audio_path('Foo')
        audio = pydub.AudioSegment.from_file(foo_mp3_path)
        self.assertTrue(abs(audio.duration_seconds - 0.792) < 0.01)
        os.unlink(foo_mp3_path)

    def test__padded_phrase(self):
        up_rp_path = ac._rendered_phrase_audio_path('Up')
        padded_up_mp3_path = ac._padded_phrase(up_rp_path, 5)
        audio = pydub.AudioSegment.from_file(padded_up_mp3_path)
        self.assertTrue((abs(audio.duration_seconds) - 5) < 0.01)
        os.unlink(padded_up_mp3_path)

    def test__build_sound_element_dict(self):
        routine = session.query(Routine).filter(
            Routine.name == 'Evening Routine').one()
        se_dict = ac._build_sound_element_dict(routine)
        self.assertTrue('begin_set' in se_dict)
        # pylint: disable=unused-variable
        for element_id, se_dict_file in se_dict.items():
            os.unlink(se_dict_file)

    def test_password(self):
        self.assertTrue(auc.set_password('chardin', 'foo'))
        self.assertTrue(auc.is_valid_password('chardin', 'foo'))
        self.assertFalse(auc.is_valid_password('chardin', 'bar'))

    def test_build_audio_for_routine(self):
        routine = session.query(Routine).filter(
            Routine.name == 'Evening Routine').one()
        self.assertTrue(routine.is_rendering_stale())
        stale_routine_data = ac.get_stale_routines()
        self.assertEqual(stale_routine_data, [{'routine_name': 'Evening Routine', 'username': 'chardin'}])
        mp3_path = ac.build_audio_for_routine('chardin', 'Evening Routine')
        audio = pydub.AudioSegment.from_file(mp3_path)
        self.assertTrue((abs(audio.duration_seconds) - 792) < 5)
        routine = session.query(Routine).filter(
            Routine.name == 'Evening Routine').one()
        self.assertFalse(routine.is_rendering_stale())
        stale_routine_data = ac.get_stale_routines()
        self.assertEqual(stale_routine_data, [])
        os.unlink(mp3_path)

    def test_import_audio(self):
        with self.assertRaises(TypeError):
            ac.import_audio()
        datadir = os.path.join(os.getenv('HERMES_ROOT_DIR'), 'tests', 'data')
        self.assertTrue(ac.import_audio('test', os.path.join(datadir, 'valid.mp3')))
        self.assertTrue(ac.import_audio('test', os.path.join(datadir, 'othervalid.mp3')))
        with self.assertRaises(pydub.exceptions.CouldntDecodeError):
            ac.import_audio('test', os.path.join(datadir, 'invalid.mp3'))
        with self.assertRaises(FileNotFoundError):
            ac.import_audio('test', os.path.join(datadir, 'notfound.mp3'))

    def test_home(self):
        response = app.test_client().get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hello!', response.data)

temp_config_file.close()
os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

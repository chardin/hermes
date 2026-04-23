import unittest
import json
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

    def __init__(self, methodName='runTest'):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        super().__init__(methodName)

    def login(self, username='test', password='test'):
        return self.client.post('/login', data={
            'username': username,
            'password': password,
        }, follow_redirects=True)

    def test__rendered_phrase_audio_path(self):
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
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hello!', response.data)

    def test_login(self):
        self.assertTrue(auc.set_password('chardin', 'baz'))
        self.assertTrue(auc.is_valid_password('chardin', 'baz'))
        response = self.login(username='chardin', password='foo')
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn('Please log in to access this page', response.text)
        self.login(username='chardin', password='baz')
        response = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn('Dashboard', response.text)

    def test_react_login(self):
        self.assertTrue(auc.set_password('chardin', 'baz'))
        response = self.client.post('/token', json={'username': 'chardin', 'password': 'foo'})
        response_dict = json.loads(response.data)
        self.assertEqual(response_dict, {'msg': 'Wrong username or password'})
        self.assertEqual(response.status_code, 401)
        response = self.client.post('/profile', content_type='application/json')
        self.assertEqual(response.status_code, 401)
        response = self.client.post('/token', json={'username': 'chardin', 'password': 'baz'})
        response_dict = json.loads(response.data)
        token = response_dict.get('access_token', None)
        self.assertTrue(token)
        auth_header = 'Bearer ' + token
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/profile', content_type='application/json', headers={'Authorization': auth_header})
        response_dict = json.loads(response.data)
        self.assertEqual(response_dict['user'],
                         {'username': 'chardin',
                          'full_name': 'Chuck Hardin'})
        response = self.client.post('/invalidate')
        response_dict = json.loads(response.data)
        self.assertEqual(response_dict, {'msg': 'Logout successful'})
        self.assertEqual(response.status_code, 200)

    def test_perform_routine(self):
        self.assertTrue(auc.set_password('chardin', 'baz'))
        self.login(username='chardin', password='baz')
        routine = session.query(Routine).filter(Routine.name == 'Evening Routine').one()
        response = self.client.get('/perform_routine?routine_id=' + routine.routine_id,
                                   follow_redirects=True)
        self.assertIn('Perform routine: Evening Routine', response.text)


temp_config_file.close()
os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

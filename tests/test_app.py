import unittest
import sys
import os
import tempfile
import uuid
import pydub


def set_up_sqlite_database():
    temp_config_file = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    engine = "db:\n  engine: \'sqlite:///:memory:\'"
    temp_config_file.write(engine)
    temp_config_file.flush()

    os.environ['HERMES_CONFIG_FILE'] = temp_config_file.name
    return temp_config_file


def create_test_db():
    create_database()

    u0 = User(user_id=str(uuid.uuid4()), username='chardin',
              full_name='Chuck Hardin', hashed_password='dummy')
    
    r0 = Routine(routine_id=str(uuid.uuid4()), user_id=u0.user_id,
                 name='Evening Routine')
    
    e0 = Exercise(exercise_id=str(uuid.uuid4()), name='Cat-Camel',
                  num_sets=2, num_reps=10, user_id=None)
    e1 = Exercise(exercise_id=str(uuid.uuid4()), name='Supine Bridge',
                  num_sets=3, num_reps=10, user_id=u0.user_id)    
    e2 = Exercise(exercise_id=str(uuid.uuid4()), name='Squat',
                  num_sets=3, num_reps=10, user_id=u0.user_id)
    
    r0.add_exercise(e0)
    r0.add_exercise(e1)
    r0.add_exercise(e2, is_paused=True)
    
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
    add_to_session_and_commit([u0, r0, e0, e1,
                               m00, m01, m02, m03,
                               m10, m11, m12])


sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))
temp_config_file = set_up_sqlite_database()

from app import AudioController
from config import Config
from model import RenderedPhrase, User, Routine, Exercise, Move, \
    create_database, add_to_session_and_commit, session


c = Config()
create_test_db()

ac = AudioController(verbose=True)


class TestApp(unittest.TestCase):

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
        routine = session.query(Routine).filter(Routine.name == 'Evening Routine').one()
        se_dict = ac._build_sound_element_dict(routine)
        self.assertTrue('begin_set' in se_dict)
        for element_id in se_dict:
            os.unlink(se_dict[element_id])

    def test_build_audio_for_routine(self):
        mp3_path = ac.build_audio_for_routine('chardin', 'Evening Routine')
        audio = pydub.AudioSegment.from_file(mp3_path)
        self.assertTrue((abs(audio.duration_seconds) - 781) < 0.5)
        os.unlink(mp3_path)

temp_config_file.close()
os.unlink(temp_config_file.name)
if __name__ == '__main__':
    unittest.main()

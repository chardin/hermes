import unittest
import sys
import os

sys.path.append('/home/chardin/pg/hermes/src/hermes')

class TestConfig(unittest.TestCase):
    def test_tempfile_config(self):
        import tempfile
        from config import Config

        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b'db:\n  engine: \'foo\'')
            temp.flush()
            
            c=Config(temp.name)
            self.assertEqual(c['db']['engine'], 'foo')


if __name__ == '__main__':
    unittest.main()        

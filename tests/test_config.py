import unittest
import sys
import os


class TestConfig(unittest.TestCase):
    def test_specified_config_file(self):
        import tempfile
        from config import Config

        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b'db:\n  engine: \'foo\'')
            temp.flush()

            c = Config(temp.name)
            self.assertEqual(c.config['db']['engine'], 'foo')

    def test_env_config_file(self):
        import tempfile
        from config import Config

        with tempfile.NamedTemporaryFile() as temp:
            temp.write(b'db:\n  engine: \'mahoogana\'')
            temp.flush()
            os.environ['HERMES_CONFIG_FILE'] = temp.name

            c = Config()
            self.assertEqual(c.config['db']['engine'], 'mahoogana')


if __name__ == '__main__':
    unittest.main()

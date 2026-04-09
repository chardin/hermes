#!/usr/bin/env python3
"""
Usage: ``generate_audio.py <options>``

This script generates an MP3 audio guide to performing an
exercise routine for a given user and routine.

Required arguments:
    -u <username>         The user for whom to generate the audio,
    -r <routine_name>     The routine for which to generate the audio,

Options:
    -s <begin_set_text>   The text to announce the beginning of a set.
    -p <prompt_before_next_exercise_text>
                          The text to speak before beginning the next exercise.
    -a <pause_before_next_exercise_secs>
                          The minimum delay in seconds before beginning
                          the next exercise.
    -e <end_of_routine_text>
                          The text to speak at the end of the routine.
    -v                    Enable verbose output
    -o <output_file>      The filename to which to save the audio output.
                          Defaults to ``AudioController.audio_output_dir``,
                          subdirectory ``<username>``,
                          filename ``<routine>.mp3``.

Examples:
    ``generate_audio.py -u chardin -r 'Evening Routine' -o /tmp/sample.mp3v``
"""
import getopt
import sys
import shutil
from filelock import FileLock, Timeout

from config import Config
import app

c = Config()

def gen_audio(argv):
    """Save MP3 audio to the given file for the given user and routine.

    Generates audio for the given args.
    """
    opts, _ = getopt.getopt(argv, 'o:u:r:v',
                            ['output-file=', 'username=', 'routine=',
                             'verbose'])

    output_file = None
    username = None
    routine = None
    verbose = False

    for opt, arg in opts:
        if opt in ('-o', '--output-file'):
            output_file = arg
        elif opt in ('-u', '--username'):
            username = arg
        elif opt in ('-r', '--routine'):
            routine = arg
        elif opt in ('-v', '--verbose'):
            verbose = True

    if not username:
        print('No username specified!')
        sys.exit(2)
    if not routine:
        print('No routine name specified!')
        sys.exit(2)

    ac = app.AudioController(verbose=verbose, engine='gtts', lang='en')

    lock = FileLock(ac.lockfile_path())
    lock_timeout = 10 * 60

    try:
        with lock.acquire(timeout=lock_timeout):
            generated_mp3_path = ac.build_audio_for_routine(username, routine)
            if output_file:
                shutil.move(generated_mp3_path, output_file)
    except Timeout:
        print(f'Failed to acquire the lock within {lock_timeout} seconds.')

if __name__ == '__main__':
    gen_audio(sys.argv[1:])

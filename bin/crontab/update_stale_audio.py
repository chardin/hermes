#!/usr/bin/env python3
"""
Usage: ``update_stale_audio.py``


This script scans the database to find routines which have changed
since the last time audio has been generated for them.  It generates
audio for all such routines.
"""

from datetime import datetime
import sys
from filelock import FileLock, Timeout
from config import Config
import app

c = Config()
ac = app.AudioController()

lock = FileLock(ac.lockfile_path())

lock_timeout = 60 * 60
print('Running at:', datetime.now())

try:
    with lock.acquire(timeout=lock_timeout):
        print('Updating stale audio...')
        for gendatum in ac.get_stale_routines():
            routine_name = gendatum['routine_name']
            username = gendatum['username']
            print(f'  Generating audio for routine {routine_name}, ',
                  f'username {username}...')
            outfilename = ac.build_audio_for_routine(
                username, routine_name)
            print(f'  Generated {outfilename}!')

        print('Done!')
except Timeout:
    print(f'Failed to acquire the lock within {lock_timeout} seconds.')
except Exception as e:
    print('Error at:', datetime.now())
    print('Error while generating audio files: ' + str(e), file=sys.stderr)
    exit(1)

exit(0)

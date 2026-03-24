#!/usr/bin/env python3
"""
Usage: ``update_stale_audio.py``


This script scans the database to find routines which have changed
since the last time audio has been generated for them.  It generates
audio for all such routines.
"""

from datetime import datetime
import sys
from config import Config
import app

try:
    c = Config()
    ac = app.AudioController()

    print('Running at:', datetime.now()) 
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
except Exception as e:
    print('Error at:', datetime.now())
    print('Error while generating audio files: ' + str(e), file=sys.stderr)
    exit(1)

exit(0)

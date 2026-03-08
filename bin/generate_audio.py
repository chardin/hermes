#!/usr/bin/env python3

import os
import getopt
import sys
import shutil

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))

from config import Config
import app

c = Config()

try:
    opts, args = getopt.getopt(sys.argv[1:], 'o:u:r:s:e:p:a:x:',
                               ['output-file=', 'username=', 'routine=',
                                'begin-set=?', 'begin-exercise=?',
                                'prompt-before-next-exercise=?',
                                'pause-before-next-exercise=?',
                                'end-of-routine=?'])

except getopt.GetoptError as err:
    print(err)
    sys.exit(2)

output_file = None
username = None
routine = None
begin_set = None
begin_exercise = None
prompt_before_next_exercise = None
pause_before_next_exercise = None
end_of_routine = None

for opt, arg in opts:
    if opt in ('-o', '--output-file'):
        output_file = arg
    elif opt in ('-u', '--username'):
        username = arg
    elif opt in ('-r', '--routine'):
        routine = arg
    elif opt in ('-s', '--begin-set'):
        begin_set = arg
    elif opt in ('-e', '--begin-exercise'):
        begin_exercise = arg
    elif opt in ('-p', '--prompt-before-next-exercise'):
        prompt_before_next_exercise = arg
    elif opt in ('-a', '--pause-before-next-exercise'):
        pause_before_next_exercise = arg
    elif opt in ('-x', '--end-of-routine'):
        end_of_routine = arg

if not output_file:
    print('No output file specified!')
    sys.exit(2)
if not username:
    print('No username specified!')
    sys.exit(2)
if not routine:
    print('No routine name specified!')
    sys.exit(2)
if not begin_set:
    begin_set = c.config['prompts']['begin_set']
if not begin_exercise:
    begin_exercise = c.config['prompts']['begin_exercise']
if not prompt_before_next_exercise:
    prompt_before_next_exercise = c.config['prompts']['prompt_before_next_exercise']
if not pause_before_next_exercise:
    pause_before_next_exercise = c.config['prompts']['pause_before_next_exercise']
if not end_of_routine:
    end_of_routine = c.config['prompts']['end_of_routine']

ac = app.AudioController(engine='gtts', lang='en', begin_set=begin_set,
                         begin_exercise=begin_exercise,
                         prompt_before_next_exercise=prompt_before_next_exercise,
                         pause_before_next_exercise=pause_before_next_exercise,
                         end_of_routine=end_of_routine)

generated_mp3_path = ac.build_audio_for_routine(username, routine)
shutil.move(generated_mp3_path, output_file)


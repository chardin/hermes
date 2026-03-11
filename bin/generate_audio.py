#!/usr/bin/env python3
"""
Usage: ``generate_audio.py <options>``

This script generates an MP3 audio guide to performing an
exercise routine for a given user and routine.

Required arguments:
    -u <username>         The user for whom to generate the audio,
    -r <routine_name>     The routine for which to generate the audio,
    -o <output_file>      The filename to which to save the audio output.

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

Environment Variables:
    ``HERMES_SRC_DIR``    Directory where Hermes Python modules live.

Examples:
    ``generate_audio.py -u chardin -r 'Evening Routine' -o /tmp/sample.mp3v``
"""
import os
import getopt
import sys
import shutil

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))

from config import Config
import app

c = Config()

def gen_audio(argv):
    """Save MP3 audio to the given file for the given user and routine.

    Generates audio for the given args.
    """
    opts, args = getopt.getopt(argv, 'o:u:r:s:e:p:a:x:v',
                               ['output-file=', 'username=', 'routine=',
                                'begin-set=?', 'begin-exercise=?',
                                'prompt-before-next-exercise=?',
                                'pause-before-next-exercise=?',
                                'end-of-routine=?', 'verbose'])

    output_file = None
    username = None
    routine = None
    begin_set = None
    begin_exercise = None
    prompt_before_next_exercise = None
    pause_before_next_exercise = None
    end_of_routine = None
    verbose = False

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
        elif opt in ('-v', '--verbose'):
            verbose = True

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
        prompt_before_next_exercise = \
            c.config['prompts']['prompt_before_next_exercise']
    if not pause_before_next_exercise:
        pause_before_next_exercise = \
            c.config['prompts']['pause_before_next_exercise']
    if not end_of_routine:
        end_of_routine = c.config['prompts']['end_of_routine']

    ac = app.AudioController(verbose=verbose, engine='gtts', lang='en',
                             begin_set=begin_set, begin_exercise=begin_exercise,
                             prompt_before_next_exercise=prompt_before_next_exercise,
                             pause_before_next_exercise=pause_before_next_exercise,
                             end_of_routine=end_of_routine)

    generated_mp3_path = ac.build_audio_for_routine(username, routine)
    shutil.move(generated_mp3_path, output_file)

if __name__ == "__main__":
    gen_audio(sys.argv[1:])

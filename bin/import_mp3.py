#!/usr/bin/env python3
"""
Usage: ``import.py <phrase> <mp3_filename>``

This script sets the audio for the given phrase to the MP3 data
in the given filename.  It will create a phrase entry in the
database if one does not exist, and overwrite the audio data
it it does.
"""
import sys
from config import Config
from app import AudioController

c = Config()

def import_audio(argv):
    """Import audio data intio a phrase.

    Imports the audio data from the given filename into the given
    phrase.
    """
    ac = AudioController()
    if not ac.import_audio(argv[1], argv[2]):
        raise ValueError('This should not happen')

if __name__ == "__main__":
    import_audio(sys.argv)

#!/usr/bin/env python3
"""
Usage: ``import.py <phrase> <mp3_filename>``

This script sets the audio for the given phrase to the MP3 data
in the given filename.  It will create a phrase entry in the
database if one does not exist, and overwrite the audio data
it it does.
"""
from config import Config
from app import AudioController

c = Config()

def set_password(argv):


if __name__ == "__main__":
    import_audio(sys.argv)

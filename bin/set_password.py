#!/usr/bin/env python3
"""
Usage: ``set_password.py <username> <password>``

This script sets the password for the given user in the Hermes system.

The script will raise an error if either argument is unspecified or if the user is not found.
"""
from passlib.context import CryptContext
import sys
from config import Config
from app import WebController

c = Config()

def set_password(argv):
    """Set the password for the given user.

    Sets the password for the given user to the given password.
    """
    wc = WebController()
    if not wc.set_password(argv[1], argv[2]):
        raise ValueError('This should not happen')

if __name__ == "__main__":
    set_password(sys.argv)

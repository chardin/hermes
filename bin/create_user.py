#!/usr/bin/env python3
"""
Usage: ``create_user.py -u <username> -p <password> -f <full_name> -t <timezone>``

This script creates a new user with the given parameters.

The script will raise an error if any argument is unspecified or if the user =already exists.
"""
import sys
import uuid
import getopt
from config import Config
from model import User, add_to_session_and_commit
from app import AuthController

c = Config()

def create_user(argv):
    """Create a new user.

    Creates a new user with the given parameters.
    """

    opts, _ = getopt.getopt(argv, 'u:p:f:t:',
                            ['username=', 'password=', 'full-name=',
                             'timezone='])

    username = None
    password = None
    full_name = None
    timezone = None

    for opt, arg in opts:
        if opt in ('-u', '--username'):
            username = arg
        elif opt in ('-p', '--password'):
            password = arg
        elif opt in ('-f', '--full-name'):
            full_name = arg
        elif opt in ('-t', '--timezone'):
            timezone = arg

    if not username:
        print('No username specified!')
        sys.exit(2)
    if not password:
        print('No password specified!')
        sys.exit(2)
    if not full_name:
        print('No full name specified!')
        sys.exit(2)
    if not timezone:
        print('No timezone specified!')
        sys.exit(2)

    user = User(user_id=str(uuid.uuid4()),
                username=username,
                full_name=full_name,
                timezone=timezone)
    add_to_session_and_commit([user])
    ac = AuthController()
    if not ac.set_password(username, password):
        raise ValueError('This should not happen')

if __name__ == "__main__":
    create_user(sys.argv[1:])

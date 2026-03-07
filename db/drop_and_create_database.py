#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, MetaData

sys.path.append(os.getenv("HERMES_SRC_DIR", os.getcwd()))
from config import Config
from model import create_database

c = Config()

engine = create_engine(c.config['db']['engine'])
metadata = MetaData()
metadata.reflect(bind=engine)
metadata.drop_all(engine)

create_database()

exit(0)

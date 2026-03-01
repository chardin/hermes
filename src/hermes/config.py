# -*- coding: utf-8 -*-
"""
config - Get Hermes config.

This module returns the Hermes configuration for use by a
command-line utility, a web app, or other invoking context.

Example:
    import config

    hermes_config = Config()

"""
import os
from pathlib import Path
import yaml
from typing import Optional

class Config:
    """The configuration for the Hermes system.

    This class gets configuration data for the Hermes system in one of
    three ways:
        * From the filename given on instantiation.
        * If that is not given, the value of the environment variable ``HERMES_CONFIG_FILE``.
        * If that is not given, ``$HOME/.hermes_config.yaml``.
    """

    def __init__(self, filename: Optional[str] = None):
        filename = filename or os.getenv('HERMES_CONFIG_FILE') \
            or Path.home() / '.hermes_config.yaml'

        with open(filename, 'r') as file:
            data = yaml.safe_load(file)

        self.config = data

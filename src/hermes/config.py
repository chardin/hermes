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


def Config(filename: Optional[str] = None) -> object:
    """
    Return configuration data for the Hermes system.

    Args:
        filename (str): The filename for the configuration.
        If not specified, it defaults to the value of the environment
        variable ``HERMES_CONFIG_FILE``, or if that is not specified,
        ``$HOME/.hermes_config.yaml``.

    Returns:
        object: An object specified by the YAML data in the configuration file.

    """
    filename = filename or os.getenv('HERMES_CONFIG_FILE') \
        or Path.home() / '.hermes_config.yaml'

    with open(filename, 'r') as file:
        data = yaml.safe_load(file)

    return data

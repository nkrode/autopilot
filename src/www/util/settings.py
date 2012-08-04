"""
Settings functions to load and save settings to a YAML file.
"""

import logging
from yaml import load, dump


_SETTINGS_FILE = "settings.conf"
_SYNC_SETTINGS_FILE = "_store/sync.conf"


def load_settings():
    """Load application settings."""
    return _read_settings(_SETTINGS_FILE)


def load_sync_settings():
    """Load cloud synchronization settings."""
    return _read_settings(_SYNC_SETTINGS_FILE)


def save_sync_settings(setting):
    """Save cloud synchronization settings."""
    try:
        stream = open(_SYNC_SETTINGS_FILE, 'w')
        dump(setting, stream)
    except Exception as e:
        error_text = "Saving sync settings to the file: %s %s"
        error_text = error_text % (_SYNC_SETTINGS_FILE, e)
        logging.error(error_text)


def _read_settings(file_name):
    """Read settings from YAML file.

    Args:
        file_name: The full path to the YAML file.
    """
    try:
        stream = open(file_name, 'r')
        return load(stream)
    except Exception as e:
        error_text = "Loading settings from the file: %s %s"
        error_text = error_text % (file_name, e)
        logging.error(error_text)

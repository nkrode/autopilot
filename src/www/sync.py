#! /usr/bin/env python

import argparse
import logging
import time

import util.settings
from setup.dropbox_client import DropboxClient
from setup.googledrive_client import GoogleDriveClient


def main(frequency):

    log_settings = util.settings.load_settings()
    settings = util.settings.load_sync_settings()
    if settings is None:
        logging.fatal("No cloud service setup.")
        return

    log_level = getattr(logging, log_settings['logging']['level'].upper())
    if log_settings['logging']['mode'] == "FILE":
        logging.basicConfig(filename=log_settings['logging']['file_name'],
            level=log_level, format='%(asctime)s %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')
    else:
        logging.basicConfig(level=log_level,
            format='%(asctime)s %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')

    if settings["cloud_service"] == "dropbox":
        client = DropboxClient()
    elif settings["cloud_service"] == "googledrive":
        client = GoogleDriveClient()
    else:
        logging.fatal("No cloud service setup.")
        return

    try:
        while True:
            status = client.sync()
            if status == -1:
                break
            if frequency is None:
                break
            else:
                time.sleep(frequency)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='blog sync.')
    parser.add_argument('--f', type=int,
        help="frequency with which to synchronize (in seconds)",
        required=False)
    args = parser.parse_args()
    frequency = args.f
    main(frequency)

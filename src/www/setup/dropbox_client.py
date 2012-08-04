import logging
import os.path
import shutil
import time

from dropbox import client, session
from yaml import load, dump

from base_client import BaseClient
import util.settings


class DropboxClient(BaseClient):
    """Dropbox Sync Client.

    Dropbox api documentation:
    https://www.dropbox.com/static/developers/dropbox-python-sdk-1.4.1-docs/
    """

    TOKEN_FILE_NAME = '_store/dropbox.access'
    DELTA_FILE_NAME = '_store/dropbox.delta'
    TOKEN_STORE = {}

    def __init__(self):
        self.settings = util.settings.load_settings()
        self.LOCAL_SYNC_FOLDER = self.settings['articles_folder']

    def get_auth_url(self, callback_url):
        """Get url for OAuth authorization.

        Args:
            callback_url: URL to redirect to after authentication.

        Returns:
            URL to redirect to for OAuth authentication.
        """
        sess = self._get_session()
        request_token = sess.obtain_request_token()
        DropboxClient.TOKEN_STORE[request_token.key] = request_token
        url = sess.build_authorize_url(request_token,
                                       oauth_callback=callback_url)
        return url

    def save_access_token(self, request_token_key):
        """Save OAuth access token to file.

        Args:
            request_token_key: Token key used for OAuth authentication.
        """
        try:
            sess = self._get_session()
            if request_token_key in DropboxClient.TOKEN_STORE:
                request_token = DropboxClient.TOKEN_STORE[request_token_key]
                access_token = sess.obtain_access_token(request_token)
                serialize_token = {'key': access_token.key,
                                   'secret': access_token.secret}
                stream = open(self.TOKEN_FILE_NAME, 'w')
                dump(serialize_token, stream)

                # delete delta file
                if os.path.exists(self.DELTA_FILE_NAME):
                    os.remove(self.DELTA_FILE_NAME)
            else:
                error_text = ('dropbox request token: %s in invalid' %
                                request_token_key)
                logging.error(error_text)
                return -1

        except Exception:
            self._log_error()
            return -1

    def sync(self):
        """Syncronize data from dropbox to local folder."""
        return self._sync()

    def _get_session(self):
        """Get a dropbox session."""
        return session.DropboxSession(self.settings['dropbox_app_key'],
                                      self.settings['dropbox_app_secret'],
                                      self.settings['dropbox_access_type'])

    def _load_access_token(self):
        """Load access token from file."""
        try:
            stream = open(self.TOKEN_FILE_NAME, 'r')
            token = load(stream)
            return token
        except:
            return None

    def _clear_folder(self, path):
        """Delete all files and folder."""
        for root, dirs, files in os.walk(path):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

    def _sync(self):
        token = self._load_access_token()

        if token is None:
            logging.critical('dropbox access token not available, run setup.')
            return -1

        try:
            logging.info("dropbox: synchronizing")
            retries = 1
            error_occured = False

            # check if previous sync state is saved
            prev_cursor = None
            if os.path.exists(self.DELTA_FILE_NAME):
                counter = 0
                while counter < retries:
                    try:
                        prev_cursor = open(self.DELTA_FILE_NAME).read()
                        break
                    except Exception:
                        text = ('dropbox: error reading delta file: %s' %
                                 self.DELTA_FILE_NAME)
                        logging.warning(text)
                        counter += 1
                        time.sleep(1)
            try:
                sess = self._get_session()
                sess.set_token(token['key'], token['secret'])
                dropbox_client = client.DropboxClient(sess)
                delta = dropbox_client.delta(prev_cursor)

                reset = delta['reset']
                entries = delta['entries']
                cursor = delta['cursor']
                #has_more = delta['has_more']

                # if reset returned by dropbox, then remove all local files
                if reset:
                    self._clear_folder(self.LOCAL_SYNC_FOLDER)

                # process each file/folder entry
                for entry in entries:
                    name = entry[0]
                    meta = entry[1]

                    # if entry has been deleted
                    if meta is None:
                        path_to_delete = "".join([self.LOCAL_SYNC_FOLDER,
                                                  name])
                        if os.path.exists(path_to_delete):
                            if os.path.isdir(path_to_delete):
                                shutil.rmtree(path_to_delete)
                            else:
                                os.remove(path_to_delete)
                    else:
                        local_path = "".join([self.LOCAL_SYNC_FOLDER,
                                              meta['path']])
                        remote_path = meta['path']
                        if meta['is_dir']:
                            try:
                                os.makedirs(local_path)
                            except Exception:
                                self._log_error()
                                error_occured = True
                        else:
                            try:
                                out = open(local_path, 'w')
                                f = dropbox_client.get_file(remote_path).read()
                                out.write(f)
                            except Exception:
                                self._log_error()
                                error_occured = True

                # if anything changed
                if entries:

                    # update delta file only if no errors occured
                    if not error_occured:
                        counter = 0
                        while counter < retries:
                            try:
                                f = open(self.DELTA_FILE_NAME, 'w')
                                f.write(cursor)
                                logging.info('dropbox updated delta file')
                                break
                            except Exception:
                                self._log_error()
                                counter += 1
                                time.sleep(1)

                    #send reboot command to the engine
                    try:
                        self._reboot_engine()
                    except Exception:
                        self._log_error()

            except Exception:
                self._log_error()
                return

        except Exception:
            self._log_error()

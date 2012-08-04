import httplib2
import logging
import os.path
import shutil

from apiclient import errors
from apiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

from base_client import BaseClient
import util.settings


class GoogleDriveClient(BaseClient):
    """Google Drive sync client."""

    APP_SCOPE = 'https://www.googleapis.com/auth/drive'
    USER_AGENT = 'blog-sync/1.0'
    REMOTE_SYNC_FOLDER = None
    TOKEN_FILE_NAME = '_store/googledrive.access'
    DELTA_FILE_NAME = '_store/googledrive.delta'
    TOKEN_STORE = {}

    def __init__(self):
        self.settings = util.settings.load_settings()
        articles_folder = self.settings["articles_folder"].rstrip('/')
        self.LOCAL_SYNC_FOLDER = "".join([articles_folder, '/'])
        self.REMOTE_SYNC_FOLDER = self.settings['google_drive_folder']

    def get_auth_url(self, callback_url):
        """Get url for OAuth authorization.

        Args:
            callback_url: URL to redirect to after authentication.

        Returns:
            URL to redirect to for OAuth authentication.
        """
        flow = OAuth2WebServerFlow(client_id=self.settings['google_app_key'],
            client_secret=self.settings['google_app_secret'],
            scope=self.APP_SCOPE,
            user_agent=self.USER_AGENT)

        authorize_url = flow.step1_get_authorize_url(callback_url)
        GoogleDriveClient.TOKEN_STORE['google_drive'] = flow
        return authorize_url

    def save_access_token(self, request_token_key):
        """Save OAuth access token to file.

        Args:
            request_token_key: Token key used for OAuth authentication.
        """
        try:
            storage = Storage(self.TOKEN_FILE_NAME)
            flow = GoogleDriveClient.TOKEN_STORE['google_drive']
            if flow:
                credentials = flow.step2_exchange(request_token_key)
                storage.put(credentials)
                return
            else:
                logging.error('googledrive: authentication token not found')
                return -1
        except Exception:
            self._log_error()
            return -1

    def sync(self):
        """Syncronize data from google drive to local folder."""
        return self._sync()

    def _sync(self):
        try:
            logging.info("googledrive: synchronizing")
            storage = Storage(self.TOKEN_FILE_NAME)
            credentials = storage.get()

            if credentials is None:
                logging.critical(
                    'googledrive access token not available, run setup.')
                return -1

            service = self._build_service(credentials)
            folder_id = self._get_folder_id(service, self.REMOTE_SYNC_FOLDER)

            if folder_id is None:
                logging.critical('google drive: sync folder not found.')
                return -1

            #check if previous sync state is saved
            prev_cursor = None
            #retries = 3
            # if os.path.exists(self.DELTA_FILE_NAME):
            #   counter = 0
            #   while counter<retries:
            #       try:
            #           prev_cursor = open(self.DELTA_FILE_NAME).read()
            #           break
            #       except Exception, e:
            #           logging.warning("googledrive: error reading delta file: " + self.DELTA_FILE_NAME)
            #           counter+=1
            #           time.sleep(1)

            if prev_cursor is None:
                self._clear_folder(self.LOCAL_SYNC_FOLDER)

            # changes = self._retrieve_all_changes(service, prev_cursor)

            self._sync_folder(service, folder_id, self.LOCAL_SYNC_FOLDER)

            # send reboot command to blog engine
            try:
                self._reboot_engine()
            except Exception:
                self._log_error()

        except Exception:
            self._log_error()

    def _sync_folder(self, service, folder_id, local_path):
        """Syncronize files and folders to local folder."""

        # scan for files in the current folder
        files = self._scan_files_in_folder(service, folder_id)
        for file_id in files:
            file_info = self._get_file_info(service, file_id)
            self._download_file(service, file_info, local_path)

        # scan for folders in the current folder
        folders = self._scan_files_in_folder(service, folder_id,
                                             foldersOnly=True)
        for folder_id in folders:
            folder_info = self._get_file_info(service, folder_id)
            folder_name = "".join([local_path, folder_info['title'], '/'])
            labels = folder_info['labels']
            trashed = labels['trashed']
            if not trashed:
                if not os.path.exists(folder_name):
                    os.makedirs(folder_name)
                self._sync_folder(service, folder_id, folder_name)

    def _download_file(self, service, file_info, local_path):
        """Download file to local path."""
        if file_info is None:
            return
        labels = file_info['labels']
        trashed = labels['trashed']
        if not trashed and 'downloadUrl' in file_info:
            download_url = file_info['downloadUrl']
            if download_url:
                original_name = file_info['title']
                local_file_name = local_path + original_name
                resp, content = service._http.request(download_url)
                if resp.status == 200:
                    f = open(local_file_name, 'w')
                    f.write(content)
                else:
                    logging.error('googledrive: an error occurred %s' % resp)

    def _build_service(self, credentials):
        http = httplib2.Http()
        http = credentials.authorize(http)
        return build('drive', 'v2', http=http)

    def _get_folder_id(self, service, folder_name):
        folder_id = None
        query = "mimeType = 'application/vnd.google-apps.folder' and title = '{name}'".format(name=folder_name)
        files = service.files().list(q=query).execute()
        if files and 'items' in files and files['items']:
            folder = files['items'][0]
            folder_id = folder['id']
        return folder_id

    def _scan_files_in_folder(self, service, folder_id, foldersOnly=False):
        files = []
        page_token = None
        while True:
            try:
                param = {}
                if page_token:
                    param['pageToken'] = page_token
                query = "mimeType = 'application/vnd.google-apps.folder' "

                if foldersOnly:
                    children = service.children().list(q=query,
                        folderId=folder_id, **param).execute()
                else:
                    children = service.children().list(folderId=folder_id,
                        **param).execute()

                for child in children.get('items', []):
                    files.append(child['id'])

                page_token = children.get('nextPageToken')
                if not page_token:
                    break

            except errors.HttpError, error:
                logging.error('googledrive: %s' % error)
                return None

        return files

    def _get_file_info(self, service, file_id):
        file_info = service.files().get(fileId=file_id).execute()
        return file_info

    def _retrieve_all_changes(self, service, start_change_id=None):
        result = []
        page_token = None
        while True:
            try:
                param = {}
                if start_change_id:
                    param['startChangeId'] = start_change_id
                if page_token:
                    param['pageToken'] = page_token
                changes = service.changes().list(**param).execute()

                result.extend(changes['items'])
                page_token = changes.get('nextPageToken')
                if not page_token:
                    break
            except errors.HttpError, error:
                logging.error('googledrive: %s' % error)
                return None
        return result

    def _clear_folder(self, path):
        for root, dirs, files in os.walk(path):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

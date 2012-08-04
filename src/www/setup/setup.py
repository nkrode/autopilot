import logging

# import tornado.web
from pystache.loader import Loader
from pystache.renderer import Renderer

import util.settings
from controller.base import BaseController
from dropbox_client import DropboxClient
from googledrive_client import GoogleDriveClient


class CloudSetupController(BaseController):

    def check_setup(self):
        settings = util.settings.load_sync_settings()
        print settings

        if settings:
            return False
        else:
            return True

    def get(self):
        pass_phrase = self.authenticate_request()
        if pass_phrase:
            if self.check_setup():
                loader = Loader(extension='html', search_dirs=['view', 'view/setup'])
                renderer = Renderer(file_extension='html',
                    search_dirs=['view/partials', 'view/setup'])
                template = loader.load_name('setup')
                html = renderer.render(template, {"pass": pass_phrase})
                self.write(html)
            else:
                self.write("setup already completed.")

    def post(self):

        if self.authenticate_request():
            if self.check_setup():

                provider = self.get_argument("provider", None)
                if provider is None:
                    self.redirect("/setup")

                client = None
                if provider == "dropbox":
                    client = DropboxClient()
                    BaseController.settings["cloud_service"] = "dropbox"
                elif provider == "googledrive":
                    client = GoogleDriveClient()
                    BaseController.settings["cloud_service"] = "googledrive"
                else:
                    logging.fatal("No cloud service setup.")
                    self.write("sorry, any error occured.")
                    return

                return_url = "".join([self.request.protocol, '://',
                                      self.request.host, '/oauthcallback'])

                redirect_url = client.get_auth_url(return_url)
                self.redirect(redirect_url)
            else:
                self.write("setup already completed.")


class CloudCallbackController(BaseController):

    def get(self):
        provider = BaseController.settings["cloud_service"]
        if provider == "dropbox":
            client = DropboxClient()
            request_token_key = self.get_argument("oauth_token")

        elif provider == "googledrive":
            client = GoogleDriveClient()
            request_token_key = self.get_argument("code")
        else:
            logging.fatal("No cloud service setup.")
            self.write("sorry, any error occured.")
            return

        result = client.save_access_token(request_token_key)

        if result == -1:
            self.write("sorry, any error occured.")
            return

        # save preference for sync utility
        sync_setting = {"cloud_service": provider}
        util.settings.save_sync_settings(sync_setting)

        self.redirect("/success")


class CloudSuccessController(BaseController):

    def get(self):
        loader = Loader(extension='html', search_dirs=['view', 'view/setup'])
        template = loader.load_name('success')
        renderer = Renderer(file_extension='html',
                            search_dirs=['view/partials', 'view/setup'])
        self.write(renderer.render(template, ""))

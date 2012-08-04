import tornado

from base import BaseController


class RebootController(BaseController):
    """Reboots the application by resetting initialization"""

    def get(self):
        pass_phrase = self.get_argument("pass", None)

        if (pass_phrase is not None and
                pass_phrase == BaseController.settings["pass_phrase"]):
            BaseController.initialized = False
            self.write("reboot complete.")
        else:
            raise tornado.web.HTTPError(404)

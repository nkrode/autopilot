import logging
import traceback
import urllib


class BaseClient(object):
    """Base class for online storage clients."""

    def _log_error(self):
        tb = traceback.format_exc()
        logging.error(tb)

    def _reboot_engine(self):
        """Send reboot command to the webapp"""

        if "site_proxies" in self.settings:
            proxies = self.settings["site_proxies"]
            for proxy in proxies:
                self._reboot_server(proxy)
        else:
            url = self.settings["site_url"]
            self._reboot_server(url)

    def _reboot_server(self, root_url):
        """Send reboot command to the webserver"""

        pass_phrase = self.settings["pass_phrase"]
        url = "".join([root_url.rstrip('/'), '/reboot?pass=', pass_phrase])
        f = urllib.urlopen(url)
        s = f.read()
        logging.info('reboot sent to %s.\n %s' % (url, s))

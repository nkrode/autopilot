#!/usr/bin/env python

import logging

import tornado.ioloop
from tornado.options import define, options

import util.settings
from controller.static import BaseStaticFileHandler
from controller.home import HomeController
from controller.reboot import RebootController
from controller.article import ArticleController
from controller.list import ListController, DraftController
from setup.setup import CloudSetupController
from setup.setup import CloudCallbackController, CloudSuccessController

if __name__ == "__main__":

    define("port", default=8888, help="run on the given port", type=int)
    define("debug", default=0, help="debug mode", type=int)
    tornado.options.parse_command_line()
    settings = util.settings.load_settings()

    log_level = getattr(logging, settings['logging']['level'].upper())
    if settings['logging']['mode'] == "FILE":
        logging.basicConfig(filename=settings['logging']['file_name'],
            level=log_level, format='%(asctime)s %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')
    else:
        logging.basicConfig(level=log_level,
            format='%(asctime)s %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')

    article_url_pattern = "".join([settings['articles_url_root'], '(.+)'])
    handlers = [
        (r"/img/(.*)", BaseStaticFileHandler, {"path":"img"}),
        (r"/css/(.*)", BaseStaticFileHandler, {"path":"css"}),
        (r"/js/(.*)", BaseStaticFileHandler, {"path":"js"}),
        (r"/images/(.*)", BaseStaticFileHandler, {"path":"_articles/images"}),
        (r"/static/(.*)", BaseStaticFileHandler, {"path":"view/static"}),
        (r"/reboot", RebootController),
        (r"/", HomeController),
        (article_url_pattern, ArticleController),
        (r"/list", ListController),
        (r"/draft", DraftController),
        (r"/success", CloudSuccessController),
        (r"/setup", CloudSetupController),
        (r"/oauthcallback", CloudCallbackController)
        ]
    server_settings = {'debug': options.debug}
    application = tornado.web.Application(handlers, **server_settings)
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

from pystache.loader import Loader
from pystache.renderer import Renderer
import tornado

from base import BaseController


class ArticleController(BaseController):

    def get(self, article_name):

        article_name = article_name.lower()

        if article_name in BaseController.articles:

            article = BaseController.articles[article_name]

            # if content has not modified since last request
            # send a 304 not modified status
            modified_header_key = "If-Modified-Since"
            if modified_header_key in self.request.headers:
                if (self.request.headers["If-Modified-Since"] ==
                    article['modified_date']):
                    self.set_status(304)
                    return

            if (BaseController.settings['enable_caching'] and
                article_name in BaseController.cached_articles):
                html = BaseController.cached_articles[article_name]
            else:
                view_model = {
                "article": article,
                "site_name": BaseController.settings['site_name']
                }
                self.attach_meta_data(view_model)

                loader = Loader(file_encoding='utf8',
                                extension='html',
                                search_dirs=['view', ])
                renderer = Renderer(file_encoding='utf8',
                                    file_extension='html',
                                    search_dirs=['view/partials'])
                template = loader.load_name('article')
                html = renderer.render(template, view_model)

                # cache the html
                BaseController.cached_articles[article_name] = html

            # set http caching headers
            if "http_caching_max_age" in BaseController.settings:
                max_age = BaseController.settings["http_caching_max_age"]
            else:
                max_age = 60
            self.set_header("Cache-control", "max-age=%s" % max_age)
            self.set_header("Last-Modified", article['modified_date'])
            self.write(html)

        else:
            raise tornado.web.HTTPError(404)

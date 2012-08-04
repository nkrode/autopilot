import operator

from pystache.loader import Loader
from pystache.renderer import Renderer

from base import BaseController


class HomeController(BaseController):

    def get(self):

        if (BaseController.settings['enable_caching'] and
            BaseController.cached_home):
            html = BaseController.cached_home
            self.write(html)
        else:
            published_articles = []
            for article in BaseController.articles.values():
                if article['date'] is not None:
                    published_articles.append(article)

            articles = sorted(published_articles,
                              key=operator.itemgetter("date"),
                              reverse=True)

            max_articles_count = BaseController.settings["homepage_max_articles"]
            show_archive = False
            if len(articles) > max_articles_count:
                show_archive = True
                articles = articles[0:max_articles_count]

            view_model = {
                        "articles": articles,
                        "showArchive": show_archive,
                        "site_name": BaseController.settings["site_name"]
                        }
            self.attach_meta_data(view_model)
            loader = Loader(file_encoding='utf8', extension='html',
                        search_dirs=['view', ])
            renderer = Renderer(file_encoding='utf8', file_extension='html',
                            search_dirs=['view/partials'])
            template = loader.load_name('home')
            html = renderer.render(template, view_model)

            # cache the home page
            BaseController.cached_home = html

            self.write(html)

import operator

from pystache.loader import Loader
from pystache.renderer import Renderer
import tornado

from base import BaseController


class ListController(BaseController):

    def get(self):

        if (BaseController.settings['enable_caching'] and
            BaseController.cached_list):
                html = BaseController.cached_list
                self.write(html)
        else:
            articles = self._get_articles()
            html = self.generate_page(articles)

            # cache the page
            BaseController.cached_list = html

            self.write(html)

    def generate_page(self, articles):
        view_model = {
                    "articles": articles,
                    "site_name": BaseController.settings["site_name"]
                    }
        self.attach_meta_data(view_model)

        loader = Loader(file_encoding='utf8', extension='html',
                        search_dirs=['view', ])
        renderer = Renderer(file_encoding='utf8', file_extension='html',
                            search_dirs=['view/partials'])
        template = loader.load_name('list')
        html = renderer.render(template, view_model)
        return html

    def _get_articles(self, draft=False):
        article_list = []
        if draft:
            for article in BaseController.articles.values():
                if article['date'] is None:
                    article_list.append(article)
        else:
            for article in BaseController.articles.values():
                if article['date'] is not None:
                    article_list.append(article)

        articles = []
        for article in article_list:
            articles.append({
                "date": article["date"],
                "dateString": article["dateString"],
                "title": article["title"],
                "url": article["url"]})

        articles = sorted(articles,
                          key=operator.itemgetter("date"),
                          reverse=True)
        return articles


class DraftController(ListController):

    def get(self):
        pass_phrase = self.get_argument("pass", None)

        if (pass_phrase is not None and
                pass_phrase == BaseController.settings["pass_phrase"]):
            articles = self._get_articles(draft=True)
            html = self.generate_page(articles)
            self.write(html)
        else:
            raise tornado.web.HTTPError(404)
































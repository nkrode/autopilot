from datetime import datetime
import glob
import logging
import operator
import os
import re
import time
import traceback

import tornado.web
import markdown2

import util.settings


class BaseController(tornado.web.RequestHandler):
    """Base class for all controllers in the application."""

    settings = {}
    articles = []
    cached_home = None
    cached_list = None
    cached_articles = {}
    initialized = False

    def prepare(self):
        """Called at the beginning of a request before `get`/`post`/etc.

        Perform common initialization in this method.
        """
        if not BaseController.initialized:
            self._boot()
            BaseController.initialized = True

    def write_error(self, status_code, exc_info=None, **kwargs):
        """Write error message.

        This method handles errors on the website.
        """
        if status_code == 404:
            logging.error("404: Not found %s" % self.request.uri)
            self.write("404: Not found")
        else:
            tb = traceback.format_exc()
            logging.error("%s\n\n" % tb)
            self.redirect("/static/error.html")

    def log_error(self):
        tb = traceback.format_exc()
        logging.error(tb)

    def _boot(self):
        """Boot the application, load settings and articles."""
        BaseController.settings = util.settings.load_settings()
        self._validate_settings()
        self._load_articles()

    def _validate_settings(self):
        """Validates settings from settings.conf"""
        if not BaseController.settings['pass_phrase']:
            self.redirect("/static/configure.html")

    def _load_articles(self):
        """Load all articles."""

        if not BaseController.settings:
            return

        settings = BaseController.settings

        live_articles = []
        draft_articles = []

        root_folder = "".join([settings['articles_folder'].rstrip('/'), '/'])
        path = "".join([root_folder, settings['articles_file_extension']])
        files = glob.glob(path)

        for file_name in files:
            try:
                stream = open(file_name, 'r')
                lines = stream.readlines()

                # atleast 3 lines should be in the article file
                # 1st line = title
                # 2nd line = ------
                # 3rd line = content
                if len(lines) >= 3:

                    title = lines[0]

                    match = re.search('\[([0-9]{4}-[0-9]{1,2}-[0-9]{1,2})\]', title)

                    if match:
                        published_date_string = match.group(1)
                        date_parts = published_date_string.split('/')

                        published_date = datetime.strptime(
                            published_date_string, '%Y-%m-%d')

                        published_date_string = self._custom_strftime(
                                                '%B {S}, %Y',
                                                published_date)

                        title = title[match.end():].strip()

                    else:
                        title = title.strip()
                        published_date_string = ''
                        published_date = None

                    summary_lines = settings['homepage_summary_lines']

                    if len(lines) > summary_lines + 3:
                        summary = ''.join(lines[2:summary_lines]).strip()
                    else:
                        summary = ''.join(lines[2:]).strip()

                    # convert summary markdown to html
                    summary = markdown2.markdown(summary)

                    # convert content markdown to html
                    content = ''.join(lines[2:])
                    content = markdown2.markdown(content)

                    # get modified date
                    modified_date = time.ctime(os.path.getmtime(file_name))

                    article = {
                                'url': '',
                                'date': published_date,
                                'dateString': published_date_string,
                                'title': title,
                                'summary': summary,
                                'content': content,
                                'modified_date': modified_date
                              }

                    if article['date'] is None:
                        draft_articles.append(article)
                    else:
                        live_articles.append(article)

            except Exception:
                self.log_error()

        articles_store = {}

        # live articles
        sorted_articles = sorted(live_articles,
                                key=operator.itemgetter('date'),
                                reverse=False)
        for article in sorted_articles:
            self._add_article(article, articles_store)

        # draft articles
        for article in draft_articles:
            self._add_article(article, articles_store)

        # publish the articles
        BaseController.articles = articles_store

        # clear cached articles
        BaseController.cached_articles = {}
        BaseController.cached_home = None
        BaseController.cached_list = None

    def _add_article(self, article, articles_store):
        """Add and generate unique URL for the article."""

        settings = BaseController.settings

        # check if we have any url maps defined in settings
        if 'url_map' in settings:
            url_map = settings['url_map']
        else:
            url_map = None

        # generate url based on the title
        title = article['title']
        ignore_pattern = '[^\w\s]'
        original_url = re.sub(ignore_pattern, '', title)
        original_url = original_url.replace(' ', '-').lower()

        # swap url generated from title with the one from url map
        if url_map and original_url in url_map:
            original_url = url_map[original_url]
        url = original_url

        counter = 1
        while True:
            if url in articles_store:
                url = "".join([original_url, '-', str(counter)])
                counter += 1
            else:
                break

        article['url'] = "".join([settings['articles_url_root'], url])
        articles_store[url] = article

    def _custom_strftime(self, format, t):
        """Generate date string with st, nd, rd, th suffix"""
        return t.strftime(format).replace('{S}', str(t.day) + self._date_suffix(t.day))

    def _date_suffix(self, d):
        if 11 <= d <= 13:
            return 'th'
        else:
            return {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

    def compute_etag(self):
        return None

    def authenticate_request(self):
        pass_phrase = self.get_argument("pass", None)
        if (pass_phrase is not None and
                pass_phrase == BaseController.settings["pass_phrase"]):
            return pass_phrase
        else:
            raise tornado.web.HTTPError(403)

    def attach_meta_data(self, obj):
        """Adds misc. properties from configuration."""

        if "email" in BaseController.settings:
            obj["email"] = BaseController.settings["email"]

        if "twitter_username" in BaseController.settings:
            obj["twitter"] = BaseController.settings["twitter_username"]

        if "github_username" in BaseController.settings:
            obj["github"] = BaseController.settings["github_username"]

        if "coderwall_username" in BaseController.settings:
            obj["coderwall"] = BaseController.settings["coderwall_username"]

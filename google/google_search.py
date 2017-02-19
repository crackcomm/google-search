# -*- coding: utf-8 -*-

# Python bindings to the Google search engine
# Copyright (c) 2009-2016, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__all__ = ['search', 'search_images', 'search_news', 'search_videos',
           'search_shop', 'search_books', 'search_apps', 'lucky']

import os
import random
import sys
import time

if sys.version_info[0] > 2:
    from urllib.parse import quote_plus, urlparse, parse_qs
else:
    from urllib import quote_plus
    from urlparse import urlparse, parse_qs

from bs4 import BeautifulSoup
import requests

# URL templates to make Google searches.
URL_HOME = "https://www.google.%(tld)s/"
URL_SEARCH = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&btnG=Google+Search&tbs=%(tbs)s&safe=%(safe)s&tbm=%(tpe)s"
URL_NEXT_PAGE = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&start=%(start)d&tbs=%(tbs)s&safe=%(safe)s&tbm=%(tpe)s"
URL_SEARCH_NUM = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&num=%(num)d&btnG=Google+Search&tbs=%(tbs)s&safe=%(safe)s&tbm=%(tpe)s"
URL_NEXT_PAGE_NUM = "https://www.google.%(tld)s/search?hl=%(lang)s&q=%(query)s&num=%(num)d&start=%(start)d&tbs=%(tbs)s&safe=%(safe)s&tbm=%(tpe)s"

# # Cookie jar. Stored at the user's home folder.
# home_folder = os.getenv('HOME')
# if not home_folder:
#     home_folder = os.getenv('USERHOME')
#     if not home_folder:
#         home_folder = '.'  # Use the current folder on error.
# cookie_jar = LWPCookieJar(os.path.join(home_folder, '.google-cookie'))
#
# try:
#     cookie_jar.load()
# except Exception:
#     pass

# Default user agent, unless instructed by the user to change it.
USER_AGENT = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0)'

# Load the list of valid user agents from the install folder.
install_folder = os.path.abspath(os.path.split(__file__)[0])
user_agents_file = os.path.join(install_folder, 'user_agents.txt')
try:
    with open('user_agents.txt') as fp:
        user_agents_list = [_.strip() for _ in fp.readlines()]
except Exception:
    user_agents_list = [USER_AGENT]


class GoogleSearch(object):
    def __init__(self, user_agent=USER_AGENT, proxies=None, cookies=None):
        self.headers = {'User-Agent': user_agent}
        self.proxies = proxies
        self.cookies = cookies

    def get_random_user_agent(self):
        """
        Get a random user agent string.

        @rtype:  str
        @return: Random user agent string.
        """
        return random.choice(user_agents_list)

    def get_page(self, url):
        """
        Request the given URL and return the response page, using the cookie jar.

        @type  url: str
        @param url: URL to retrieve.

        @rtype:  str
        @return: Web page retrieved for the given URL.

        @raise IOError: An exception is raised on error.
        @raise urllib2.URLError: An exception is raised on error.
        @raise urllib2.HTTPError: An exception is raised on error.
        """

        s = requests.session()

        # s.cookies = cookie_jar
        if self.cookies:
            s.cookies = self.cookies
        s.headers = self.headers
        s.proxies = self.proxies

        response = s.get(url)
        # s.cookies.save(ignore_discard=True)
        self.cookies = s.cookies

        html = response.content
        return html

    def filter_result(self, link):
        """
        Filter links found in the Google result pages HTML code.

        :return: None if the link doesn't yield a valid result.
        """
        try:

            # Valid results are absolute URLs not pointing to a Google domain
            # like images.google.com or googleusercontent.com
            o = urlparse(link, 'http')
            if o.netloc and 'google' not in o.netloc:
                return link

            # Decode hidden URLs.
            if link.startswith('/url?'):
                link = parse_qs(o.query)['q'][0]

                # Valid results are absolute URLs not pointing to a Google domain
                # like images.google.com or googleusercontent.com
                o = urlparse(link, 'http')
                if o.netloc and 'google' not in o.netloc:
                    return link

        # Otherwise, or on error, return None.
        except Exception:
            pass
        return None

    def search(self, query, tld='com', lang='en', tbs='0', safe='off', num=10,
               start=0, stop=None, pause=2.0, only_standard=False,
               extra_params={}, tpe=''):
        """
        Search the given query string using Google.

        @type  query: str
        @param query: Query string. Must NOT be url-encoded.

        @type  tld: str
        @param tld: Top level domain.

        @type  lang: str
        @param lang: Languaje.

        @type  tbs: str
        @param tbs: Time limits (i.e "qdr:h" => last hour, "qdr:d" => last 24 hours, "qdr:m" => last month).

        @type  safe: str
        @param safe: Safe search.

        @type  num: int
        @param num: Number of results per page.

        @type  start: int
        @param start: First result to retrieve.

        @type  stop: int
        @param stop: Last result to retrieve.
            Use C{None} to keep searching forever.

        @type  pause: float
        @param pause: Lapse to wait between HTTP requests.
            A lapse too long will make the search slow, but a lapse too short may
            cause Google to block your IP. Your mileage may vary!

        @type  only_standard: bool
        @param only_standard: If C{True}, only returns the standard results from
            each page. If C{False}, it returns every possible link from each page,
            except for those that point back to Google itself. Defaults to C{False}
            for backwards compatibility with older versions of this module.

        @type  extra_params: dict
        @param extra_params: A dictionary of extra HTTP GET parameters, which must be URL encoded.
            For example if you don't want google to filter similar results you can set the extra_params to
            {'filter': '0'} which will append '&filter=0' to every query.

        @type  tpe: str
        @param tpe: Search type (images, videos, news, shopping, books, apps)
                Use the following values {videos: 'vid', images: 'isch', news: 'nws',
                                          shopping: 'shop', books: 'bks', applications: 'app'}

        @rtype:  generator
        @return: Generator (iterator) that yields found URLs. If the C{stop}
            parameter is C{None} the iterator will loop forever.
        """
        # Set of hashes for the results found.
        # This is used to avoid repeated results.
        hashes = set()

        # Prepare the search string.
        query = quote_plus(query)

        # Check extra_params for overlapping
        for builtin_param in ('hl', 'q', 'btnG', 'tbs', 'safe', 'tbm'):
            if builtin_param in extra_params.keys():
                raise ValueError(
                    'GET parameter "%s" is overlapping with \
                    the built-in GET parameter',
                    builtin_param
                )

        # Grab the cookie from the home page.
        self.get_page(URL_HOME % vars())

        # Prepare the URL of the first request.
        if start:
            if num == 10:
                url = URL_NEXT_PAGE % vars()
            else:
                url = URL_NEXT_PAGE_NUM % vars()
        else:
            if num == 10:
                url = URL_SEARCH % vars()
            else:
                url = URL_SEARCH_NUM % vars()

        # Loop until we reach the maximum result, if any (otherwise, loop forever).
        while not stop or start < stop:
            try:  # Is it python<3?
                iter_extra_params = extra_params.iteritems()
            except AttributeError:  # Or python>3?
                iter_extra_params = extra_params.items()
            # Append extra GET_parameters to URL
            for k, v in iter_extra_params:
                url += url + ('&%s=%s' % (k, v))

            # Sleep between requests.
            time.sleep(pause)

            # Request the Google Search results page.
            html = self.get_page(url)

            # Parse the response and process every anchored URL.
            soup = BeautifulSoup(html, 'html.parser')
            anchors = soup.find(id='search').findAll('a')
            for a in anchors:

                # Leave only the "standard" results if requested.
                # Otherwise grab all possible links.
                if only_standard and (
                            not a.parent or a.parent.name.lower() != "h3"):
                    continue

                # Get the URL from the anchor tag.
                try:
                    link = a['href']
                except KeyError:
                    continue

                # Filter invalid links and links pointing to Google itself.
                link = self.filter_result(link)
                if not link:
                    continue

                # Discard repeated results.
                h = hash(link)
                if h in hashes:
                    continue
                hashes.add(h)

                # Yield the result.
                yield link

            # End if there are no more results.
            if not soup.find(id='nav'):
                break

            # Prepare the URL for the next request.
            start += num
            if num == 10:
                url = URL_NEXT_PAGE % vars()
            else:
                url = URL_NEXT_PAGE_NUM % vars()

    def search_images(self, query, **kwargs):
        """
        Shortcut to search images
        Beware, this does not return the image link.

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='isch', **kwargs)

    def search_news(self, query, **kwargs):
        """
        Shortcut to search news

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='nws', **kwargs)

    def search_videos(self, query, **kwargs):
        """
        Shortcut to search videos

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='vid', **kwargs)

    def search_shop(self, query, **kwargs):
        """
        Shortcut to search shop

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='shop', **kwargs)

    def search_books(self, query, **kwargs):
        """
        Shortcut to search books

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='bks', **kwargs)

    def search_apps(self, query, **kwargs):
        """
        Shortcut to search apps

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='app', **kwargs)

    def search_books(self, query, **kwargs):
        """
        Shortcut to search books

        :param query:
        :param kwargs:
        :return:
        """
        return self.search(query, tpe='bks', **kwargs)

    def lucky(self, query, tld='com', lang='en', tbs='0', safe='off',
              only_standard=False, extra_params={}, tpe=''):
        """
        Shortcut to single-item search. Evaluates the iterator to return the single
        URL as a string.
        :param tld:
        :param lang:
        :param tbs:
        :param safe:
        :param only_standard:
        :param extra_params:
        :param tpe:
        :return:
        """
        gen = self.search(query, tld, lang, tbs, safe, 1, 0, 1, 0.,
                          only_standard,
                          extra_params, tpe)
        return next(gen)


def main():
    """
    Example Search with Google

    :return:
    """
    q = 'Viet Nam'

    # proxies = {'http': 'http://5.230.133.118:3245'}
    # proxies = {'http': 'http://5.230.133.19:3146'}
    proxies = {'http': 'http://94.249.224.38:1165'}

    gs = GoogleSearch(proxies=proxies)

    for url in gs.search(q, stop=10):
        print(url)

        #     '{} Australia'.format(company), stop=10,
        #                      user_agent=google.get_random_user_agent(), tld=self._get_random_google_tld()):
        # # urlparsed = urllib.parse.urlparse(url)


if __name__ == '__main__':
    main()

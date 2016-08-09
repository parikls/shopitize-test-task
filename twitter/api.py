import base64
import logging
from urllib.parse import urlencode

import requests

from twitter.exceptions import TwitterException
from twitter.models import TwitterResponse

logger = logging.getLogger(__name__)


class Api:
    """
    API for twitter search. Currently implemented search and parsing of
    media from extended entities
    Basic usage:
        >>> api = Api(consumer_key="KEY", consumer_secret="SECRET")
        >>> response = api.search(params={"q": "#hashtag filter:images", "count": 100})
        >>> metadata = response.metadata
        >>> statues = response.statuses

    """

    #  for more information about bad codes refer to:
    #  https://dev.twitter.com/overview/api/response-codes
    BAD_CODES = (400, 403, 404, 406, 410, 420, 422, 429, 500, 502, 503, 504)
    TOKEN_REQUEST_MAX_ATTEMPTS = 10

    def __init__(self,
                 consumer_key: str = None,
                 consumer_secret: str = None,
                 proxies: dict = None):
        """
        Creates new Twitter Api instance
        :param consumer_key: Twitter application consumer key
        :param consumer_secret: Twitter application consumer secret
        :param proxies: Use this if your network connection is behind proxy. Example:
                        proxies = {'http': 'http://user@password:host:port}
        """

        logger.debug("Start API initialization. Consumer key=%s. Consumer secret=%s" % (consumer_key, consumer_secret))
        if not (consumer_key and consumer_secret):
            raise TwitterException("Could not instantiate Twitter Api. Consumer key and secret must not be blank")

        self._oauth_token = None
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret

        self._search_url = "https://api.twitter.com/1.1/search/tweets.json"
        self._oauth_url = "https://api.twitter.com/oauth2/token"
        self._proxies = proxies

        # obtain OAuth token on initialization
        self._get_oauth_token()

    def search(self, query: str = None, params: dict = None) -> TwitterResponse:
        """
        Search Api method.
        Accepts either raw query as string, or params as dictionary.
        Example usages:
            >>> api.search(query="?max_id=1&q=%23hashtag")
            >>> api.search(params={'max_id': 1, 'q': '#hashtag'})
        :param query: use query to pass urls, which twitter api returns (see example)
        :param params: dict with request parameters
        :return: parsed instance of TwitterResponse
        """
        logger.debug("Start search request with query=%s and params=%s" % (query, params))

        if query is not None:
            return self._twitter_request(self._search_url + query)

        if params is not None:
            return self._twitter_request(self._search_url + "?" + urlencode(params))

        # neither query or params where provided - return empty response
        logger.warning("Query and params are None. Returning empty response")
        return TwitterResponse({})

    def _twitter_request(self, url: str, recur_level: int = 0) -> TwitterResponse:
        """
        Recursive method to perform requests to twitter API.
        If token is expired - tries to obtain new token and re-call self
        :param url: full url to Twitter Api
        :param recur_level: current attempt to make a call
        :return: parsed instance of TwitterResponse
        """
        if recur_level == self.TOKEN_REQUEST_MAX_ATTEMPTS:
            raise TwitterException("Could not obtain Twitter Api token")

        response = requests.get(
            url=url,
            headers={"Authorization": "Bearer %s" % self._oauth_token},
            proxies=self._proxies
        )

        if response.status_code == 401:
            # expired token, trying to re-obtain
            logger.warning("Trying to re-obtain Twitter Api token. %d attempt" % recur_level)
            self._get_oauth_token()
            return self._twitter_request(url, recur_level + 1)

        if response.status_code in self.BAD_CODES:
            raise TwitterException("Twitter returned bad response: %s" % response.json())

        return TwitterResponse(response.json())

    def _get_oauth_token(self):
        """
        Method obtains OAuth token
        """

        request_token_key = base64.b64encode(bytes(
            self._consumer_key + ":" + self._consumer_secret, encoding="utf-8")).decode("utf-8")

        logger.debug("Request token key=%s" % request_token_key)
        headers = {"Authorization": "Basic %s" % request_token_key,
                   "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}

        data = {"grant_type": "client_credentials"}
        response = requests.post(url=self._oauth_url, data=data, headers=headers, proxies=self._proxies)

        if response.status_code != 200:
            raise TwitterException("Could perform OAuth authorization. status_code=%d. message=%s" %
                                   (response.status_code, response.json()))

        self._oauth_token = response.json().get("access_token")
        logger.debug("OAuth token=%s" % self._oauth_token)

        if not self._oauth_token:
            raise TwitterException("Could not perform OAuth authorization. No OAuth token in response. message=%s" %
                                   response.json())

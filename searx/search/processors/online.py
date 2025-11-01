# SPDX-License-Identifier: AGPL-3.0-or-later
"""Processor used for ``online`` engines."""

__all__ = ["OnlineProcessor", "OnlineParams"]

import typing as t

from timeit import default_timer
import asyncio
import ssl
import httpx
import re

import searx.network
from searx.utils import gen_useragent
from searx.exceptions import (
    SearxEngineAccessDeniedException,
    SearxEngineCaptchaException,
    SearxEngineTooManyRequestsException,
)
from searx.metrics.error_recorder import count_error
from searx import settings
from .abstract import EngineProcessor, RequestParams
from ...result_types import LegacyResult

if t.TYPE_CHECKING:
    from searx.search.models import SearchQuery
    from searx.results import ResultContainer
    from searx.result_types import EngineResults


class HTTPParams(t.TypedDict):
    """HTTP request parameters"""

    method: t.Literal["GET", "POST"]
    """HTTP request method."""

    headers: dict[str, str]
    """HTTP header information."""

    data: dict[str, str]
    """Sending `form encoded data`_.

    .. _form encoded data:
       https://www.python-httpx.org/quickstart/#sending-form-encoded-data
    """

    json: dict[str, t.Any]
    """`Sending `JSON encoded data`_.

    .. _JSON encoded data:
       https://www.python-httpx.org/quickstart/#sending-json-encoded-data
    """

    content: bytes
    """`Sending `binary request data`_.

    .. _binary request data:
       https://www.python-httpx.org/quickstart/#sending-json-encoded-data
    """

    url: str
    """Requested url."""

    cookies: dict[str, str]
    """HTTP cookies."""

    allow_redirects: bool
    """Follow redirects"""

    max_redirects: int
    """Maximum redirects, hard limit."""

    soft_max_redirects: int
    """Maximum redirects, soft limit. Record an error but don't stop the engine."""

    verify: None | t.Literal[False] | str  # not sure str really works
    """If not ``None``, it overrides the verify value defined in the network.  Use
    ``False`` to accept any server certificate and use a path to file to specify a
    server certificate"""

    auth: str | None
    """An authentication to use when sending requests."""

    raise_for_httperror: bool
    """Raise an exception if the `HTTP response status code`_ is ``>= 300``.

    .. _HTTP response status code:
        https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status
    """


class OnlineParams(HTTPParams, RequestParams):
    """Request parameters of a ``online`` engine."""


def default_request_params() -> HTTPParams:
    """Default request parameters for ``online`` engines."""
    return {
        "method": "GET",
        "headers": {},
        "data": {},
        "json": {},
        "content": b"",
        "url": "",
        "cookies": {},
        "allow_redirects": False,
        "max_redirects": 0,
        "soft_max_redirects": 0,
        "auth": None,
        "verify": None,
        "raise_for_httperror": True,
    }


class OnlineProcessor(EngineProcessor):
    """Processor class for ``online`` engines."""

    engine_type: str = "online"

    def init_engine(self) -> bool:
        """This method is called in a thread, and before the base method is
        called, the network must be set up for the ``online`` engines."""
        self.init_network_in_thread(start_time=default_timer(), timeout_limit=self.engine.timeout)
        return super().init_engine()

    def init_network_in_thread(self, start_time: float, timeout_limit: float):
        # set timeout for all HTTP requests
        searx.network.set_timeout_for_thread(timeout_limit, start_time=start_time)
        # reset the HTTP total time
        searx.network.reset_time_for_thread()
        # set the network
        searx.network.set_context_network_name(self.engine.name)

    def get_params(self, search_query: "SearchQuery", engine_category: str) -> OnlineParams | None:
        """Returns a dictionary with the :ref:`request params <engine request
        online>` (:py:obj:`OnlineParams`), if the search condition is not
        supported by the engine, ``None`` is returned."""

        base_params: RequestParams | None = super().get_params(search_query, engine_category)
        if base_params is None:
            return base_params

        params: OnlineParams = {**default_request_params(), **base_params}

        headers = params["headers"]

        # add an user agent
        headers["User-Agent"] = gen_useragent()

        # add Accept-Language header
        if self.engine.send_accept_language_header and search_query.locale:
            ac_lang = search_query.locale.language
            if search_query.locale.territory:
                ac_lang = "%s-%s,%s;q=0.9,*;q=0.5" % (
                    search_query.locale.language,
                    search_query.locale.territory,
                    search_query.locale.language,
                )
            headers["Accept-Language"] = ac_lang

        self.logger.debug("HTTP Accept-Language: %s", headers.get("Accept-Language", ""))
        return params

    def _send_http_request(self, params: OnlineParams):

        # create dictionary which contain all information about the request
        request_args: dict[str, t.Any] = {
            "headers": params["headers"],
            "cookies": params["cookies"],
            "auth": params["auth"],
        }

        verify = params.get("verify")
        if verify is not None:
            request_args["verify"] = verify

        # max_redirects
        max_redirects = params.get("max_redirects")
        if max_redirects:
            request_args["max_redirects"] = max_redirects

        # allow_redirects
        if "allow_redirects" in params:
            request_args["allow_redirects"] = params["allow_redirects"]

        # soft_max_redirects
        soft_max_redirects: int = params.get("soft_max_redirects", max_redirects or 0)

        # raise_for_status
        request_args["raise_for_httperror"] = params.get("raise_for_httperror", True)

        # specific type of request (GET or POST)
        if params["method"] == "GET":
            req = searx.network.get
        else:
            req = searx.network.post
            if params["data"]:
                request_args["data"] = params["data"]
            if params["json"]:
                request_args["json"] = params["json"]
            if params["content"]:
                request_args["content"] = params["content"]

        # send the request
        response = req(params["url"], **request_args)

        # check soft limit of the redirect count
        if len(response.history) > soft_max_redirects:
            # unexpected redirect : record an error
            # but the engine might still return valid results.
            status_code = str(response.status_code or "")
            reason = response.reason_phrase or ""
            hostname = response.url.host
            count_error(
                self.engine.name,
                "{} redirects, maximum: {}".format(len(response.history), soft_max_redirects),
                (status_code, reason, hostname),
                secondary=True,
            )

        return response

    def _search_basic(self, query: str, params: OnlineParams) -> "EngineResults|None":
        # update request parameters dependent on
        # search-engine (contained in engines folder)
        self.engine.request(query, params)

        # ignoring empty urls
        if not params["url"]:
            return None

        # send request
        response = self._send_http_request(params)

        # parse the response
        response.search_params = params
        return self.engine.response(response)

    def search(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        query: str,
        params: OnlineParams,
        result_container: "ResultContainer",
        start_time: float,
        timeout_limit: float,
    ):
        self.init_network_in_thread(start_time, timeout_limit)

        try:
            # send requests and parse the results
            search_results = self._search_basic(query, params)

            # if force sitelinks option is enabled, add sitelinks to the search result
            if (len(settings['search'].get('force_sitelinks_categories', [])) > 0 and
                len(settings['search'].get('force_sitelink_websites', [])) > 0):
                search_results = self._add_forced_sitelinks(search_results, params)

            self.extend_container(result_container, start_time, search_results)
        except ssl.SSLError as e:
            # requests timeout (connect or read)
            self.handle_exception(result_container, e, suspend=True)
            self.logger.error("SSLError {}, verify={}".format(e, searx.network.get_network(self.engine.name).verify))
        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            # requests timeout (connect or read)
            self.handle_exception(result_container, e, suspend=True)
            self.logger.error(
                "HTTP requests timeout (search duration : {0} s, timeout: {1} s) : {2}".format(
                    default_timer() - start_time, timeout_limit, e.__class__.__name__
                )
            )
        except (httpx.HTTPError, httpx.StreamError) as e:
            # other requests exception
            self.handle_exception(result_container, e, suspend=True)
            self.logger.exception(
                "requests exception (search duration : {0} s, timeout: {1} s) : {2}".format(
                    default_timer() - start_time, timeout_limit, e
                )
            )
        except (
            SearxEngineCaptchaException,
            SearxEngineTooManyRequestsException,
            SearxEngineAccessDeniedException,
        ) as e:
            self.handle_exception(result_container, e, suspend=True)
            self.logger.exception(e.message)
        except Exception as e:  # pylint: disable=broad-except
            self.handle_exception(result_container, e)
            self.logger.exception("exception : {0}".format(e))

    def _add_forced_sitelinks(self, search_results: list, params: dict) -> list:
        """
        Forces the retrival of the sitelinks for the configured websites and adds them to the search results.
        """
        # for each website where the force_sitelink is required
        for site in settings['search']['force_sitelink_websites']:
            # skip if the query was not fired on an enabled category (or it's a sitelinks query)
            if params["category"] not in settings['search']['force_sitelinks_categories']:
                continue
            # skip if the query already contains one of the search terms
            if any(term in params["query"] for term in site['website_search_terms']):
                continue

            expression = "(" + site['website_url_expression'] + ")"

            # check each result
            for result in search_results:
                # if the result has an url matching the site where the force_sitelink is required
                if re.match(expression, self._get_property(result,"url", "")):
                    # add sitelinks_results as sitelinks for the current base result
                    result["sitelinks"] = self._get_sitelinks(params, site['website_search_terms'][0])
                    # do not repeat search for other matching links
                    break
        return search_results

    def _get_sitelinks(self, params, search_term):
        """
        Gets a list of sitelinks by performing another search with the same query + search_term and the same parameters
        """
        sitelink_params = params.copy()

        # update search query and params
        sitelink_query = sitelink_params["query"] + " " + search_term
        sitelink_params["query"] = sitelink_query
        sitelink_params["category"] = "sitelinks"

        # do another engine search
        sitelink_results = self._search_basic(sitelink_query, sitelink_params)
        self.logger.error(f"query: {sitelink_query}")
        self.logger.error(f"risultati: {len(sitelink_results)}")

        # remove first sitelinks result (same url as the current base result)
        if len(sitelink_results) > 0:
            del sitelink_results[0]

        # remove sitelinks without an url (such as suggestions)
        sitelink_results = list(filter(lambda result: self._get_property(result, "url") is not None, sitelink_results))

        return sitelink_results

    def _get_property(self, thing, key, default=None):
        if thing is None:
            return default
        elif isinstance(thing, dict):
            return thing.get(key, default)
        else:
            return getattr(thing, key, default)

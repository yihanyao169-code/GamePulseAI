"""Project-local fix for google-play-scraper's broken top-result appId.

``google-play-scraper==1.2.7`` parses Google Play's search-results page by
indexing into a JSON blob pulled out of a ``<script>`` tag. The "top result"
card (the exact/official match Google Play highlights above the plain list)
uses ``ElementSpecs.SearchResultOnTop["appId"] = ElementSpec(None, [11, 0, 0])``
(see ``google_play_scraper/constants/element.py``), and that index path no
longer resolves to anything -- it silently returns ``None`` while every other
field on the same entry (title, developer, icon, installs, score) still
parses correctly. Regular list results are unaffected; they use a different,
still-working spec (``ElementSpecs.SearchResult``, path ``[0, 0, 0]``).

This is a known, reported issue: JoMingyu/google-play-scraper PR #239
(https://github.com/JoMingyu/google-play-scraper/pull/239/files, unmerged as
of 2026-08) fixes it by trying a new path, ``[3, "12", 0, 0]``, and falling
back to the old ``[11, 0, 0]`` path only if the new one fails.

We cannot depend on that PR (it isn't merged/released) and must not patch the
installed package under site-packages or pull in an unpinned fork. Instead
this module re-implements the small slice of ``google_play_scraper.features
.search.search()`` that builds the top-result dict, swapping in the reviewed
fix as static local code, and otherwise reuses the installed library's own
(unaffected) building blocks unchanged. ``ElementSpec`` already supports
exactly the "try new path, fall back to old path, else None" chain we need
via its ``fallback_value`` mechanism (a bare ``except`` in
``ElementSpec.extract_content`` catches any failure and defers to
``fallback_value``, which may itself be another ``ElementSpec``), so no new
extraction logic has to be invented -- only the spec for this one field.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote

from google_play_scraper.constants.element import ElementSpec, ElementSpecs
from google_play_scraper.constants.regex import Regex
from google_play_scraper.constants.request import Formats
from google_play_scraper.exceptions import NotFoundError
from google_play_scraper.utils.request import get

logger = logging.getLogger(__name__)

# Upstream fix: JoMingyu/google-play-scraper PR #239 (unmerged).
# New path first, old (currently broken) path as the documented fallback.
_TOP_RESULT_APP_ID_SPEC = ElementSpec(
    None,
    [3, "12", 0, 0],
    fallback_value=ElementSpec(None, [11, 0, 0]),
)

_SEARCH_RESULT_ON_TOP_SPECS = dict(ElementSpecs.SearchResultOnTop)
_SEARCH_RESULT_ON_TOP_SPECS["appId"] = _TOP_RESULT_APP_ID_SPEC


def search_with_appid_fix(
    query: str, n_hits: int = 30, lang: str = "en", country: str = "us"
) -> list[dict[str, Any]]:
    """Same contract as ``google_play_scraper.search``, with the top-result
    appId fix applied. Result order is Google Play's own ranking order
    (top result, if any, followed by the plain list) -- callers can use each
    item's position in the returned list as its original search rank.
    """
    if n_hits <= 0:
        return []

    encoded_query = quote(query)
    url = Formats.Searchresults.build(query=encoded_query, lang=lang, country=country)
    try:
        dom = get(url)
    except NotFoundError:
        url = Formats.Searchresults.fallback_build(query=encoded_query, lang=lang)
        dom = get(url)

    matches = Regex.SCRIPT.findall(dom)
    dataset: dict[str, Any] = {}
    for match in matches:
        key_match = Regex.KEY.findall(match)
        value_match = Regex.VALUE.findall(match)
        if key_match and value_match:
            dataset[key_match[0]] = json.loads(value_match[0])

    try:
        top_result = dataset["ds:4"][0][1][0][23][16]
    except IndexError:
        top_result = None

    success = False
    list_dataset = dataset
    for idx in range(len(dataset["ds:4"][0][1])):
        try:
            list_dataset = dataset["ds:4"][0][1][idx][22][0]
            success = True
        except Exception:
            pass
    if not success:
        return []

    n_apps = min(len(list_dataset), n_hits)

    search_results: list[dict[str, Any]] = []
    if top_result:
        top_app = {
            key: spec.extract_content(top_result)
            for key, spec in _SEARCH_RESULT_ON_TOP_SPECS.items()
        }
        if not top_app.get("appId"):
            logger.warning(
                "search_with_appid_fix(): top result %r for query %r "
                "(lang=%s, country=%s) has no resolvable appId via either "
                "the new ([3,'12',0,0]) or legacy ([11,0,0]) path; it will "
                "be excluded from selectable candidates.",
                top_app.get("title"), query, lang, country,
            )
        search_results.append(top_app)

    for app_idx in range(n_apps - len(search_results)):
        app_item = {
            key: spec.extract_content(list_dataset[app_idx])
            for key, spec in ElementSpecs.SearchResult.items()
        }
        search_results.append(app_item)

    return search_results

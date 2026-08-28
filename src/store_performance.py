from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from google_play_scraper import app as gp_app
from google_play_scraper.exceptions import GooglePlayScraperException, NotFoundError

from src.gp_search_compat import search_with_appid_fix as gp_search
from src.market_config import default_language
from src.models import (
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
    GameSearchResult,
    MarketListingOutcome,
    StoreListing,
)

logger = logging.getLogger(__name__)

# Bumped from store_search_v2: the top-result appId fix (see src/gp_search_compat.py)
# and the tiered relevance scoring below both change search_games()'s behavior, so
# any cached results computed under the old logic must not be served to callers.
SEARCH_CACHE_VERSION = "store_search_v3_rank_appid_fix"
LISTING_CACHE_VERSION = "store_listing_v1"
DEFAULT_SEARCH_HITS = 10
MAX_SEARCH_CANDIDATES = 8

# Rank-dominant per the product requirement: Google Play's own search ranking is the
# primary signal, and title-tier is an adjustment on top of it -- not a replacement.
RANK_WEIGHT = 0.6
TITLE_WEIGHT = 0.4

# A fuzzy-only (no exact/prefix/containment relationship) title match must clear this
# raw similarity ratio to be considered at all for a non-top-ranked result, so a
# coincidentally similar but unrelated title (e.g. "Punishing: Gray Raven" for a
# query about "Arknights: Endfield") can't sneak past the score threshold.
FUZZY_ONLY_MIN_RATIO = 0.6

_CJK_PATTERN = re.compile(r"[一-鿿㐀-䶿豈-﫿]")


def _search_langs(query: str, preferred_lang: str) -> list[str]:
    """Pick which Google Play search locales to try, based on the query's script.

    A CJK query searched only under an en-us locale often surfaces an
    unrelated-but-popular app instead of the correctly-titled one, so CJK
    queries additionally try zh/zh-TW locales. This is script detection, not
    a per-title special case — it applies identically to every query.
    """
    if _CJK_PATTERN.search(query):
        langs = ["zh", "zh-TW"]
        if preferred_lang not in langs:
            langs.append(preferred_lang)
        return langs
    return [preferred_lang]


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _title_tier(query: str, title: str) -> tuple[str, float]:
    """Score how a title relates to the query, in strictly ordered tiers.

    exact > prefix > containment (proportional to how much of the longer
    string the shorter one covers) > fuzzy (generic character similarity,
    auxiliary only). A title that merely *contains* the query is deliberately
    kept below a prefix/exact match, so a substring hit like a fan-made
    materials-note app can never outscore the real title it happens to
    mention.
    """
    q = _normalize_title(query)
    t = _normalize_title(title)
    if not q or not t:
        return "none", 0.0
    if q == t:
        return "exact", 1.0
    if t.startswith(q) or q.startswith(t):
        shorter, longer = (q, t) if len(q) <= len(t) else (t, q)
        ratio = len(shorter) / len(longer)
        # Prefix strength scales with how much of the longer string the shorter
        # one covers, so a 2-character query merely prefixing an unrelated
        # 7-character title (e.g. "原神" vs "原神素材ノート") scores well
        # below a near-complete prefix match (e.g. "Genshin Impact" vs
        # "Genshin Impact · Cloud").
        return "prefix", 0.6 + 0.3 * ratio
    if q in t or t in q:
        shorter, longer = (q, t) if len(q) <= len(t) else (t, q)
        ratio = len(shorter) / len(longer)
        return "containment", 0.3 + 0.25 * ratio
    ratio = SequenceMatcher(None, q, t).ratio()
    return "fuzzy", 0.35 * ratio


def _rank_score(rank: int, n_hits: int) -> float:
    return max(0.0, 1.0 - (rank / max(n_hits, 1)))


def _score_result(query: str, title: str, rank: int, n_hits: int) -> tuple[float, str, float]:
    tier, tier_score = _title_tier(query, title)
    final_score = RANK_WEIGHT * _rank_score(rank, n_hits) + TITLE_WEIGHT * tier_score
    return final_score, tier, tier_score


def _should_keep(rank: int, tier: str, tier_score: float) -> bool:
    if rank == 0:
        # Google Play's own top pick is never dropped for a title mismatch -- it may
        # legitimately be the official app under a title/script the query doesn't
        # literally share characters with.
        return True
    if tier in ("exact", "prefix", "containment"):
        return True
    if tier == "fuzzy":
        raw_ratio = tier_score / 0.35 if tier_score else 0.0
        return raw_ratio >= FUZZY_ONLY_MIN_RATIO
    return False


def search_games(
    query: str,
    country: str = DEFAULT_COUNTRY,
    lang: str = DEFAULT_LANGUAGE,
    n_hits: int = DEFAULT_SEARCH_HITS,
) -> list[GameSearchResult]:
    value = query.strip()
    if not value:
        raise ValueError("请输入游戏名称。")

    langs = _search_langs(value, lang)
    # app_id -> (mapped_result, final_score, best_rank_seen)
    merged: dict[str, tuple[GameSearchResult, float, int]] = {}
    errors: list[Exception] = []

    for candidate_lang in langs:
        try:
            raw_results = gp_search(value, n_hits=n_hits, lang=candidate_lang, country=country)
        except Exception as exc:  # a single locale's failure must not abort the others
            errors.append(exc)
            continue

        for rank, item in enumerate(raw_results):
            app_id = item.get("appId")
            title = str(item.get("title", ""))
            final_score, tier, tier_score = _score_result(value, title, rank, n_hits)

            if not app_id:
                if rank == 0:
                    logger.warning(
                        "search_games(): Google Play's top result %r for query %r "
                        "(lang=%s, country=%s) has no resolvable appId; it cannot be "
                        "offered as a candidate, and no lower-ranked result is being "
                        "promoted to replace it.",
                        title, value, candidate_lang, country,
                    )
                continue

            if not _should_keep(rank, tier, tier_score):
                continue

            existing = merged.get(app_id)
            if existing is None or rank < existing[2]:
                mapped = _map_search_result(item)
                merged[app_id] = (mapped, final_score, rank)

    if not merged and errors:
        raise errors[0]

    ranked = sorted(merged.values(), key=lambda entry: entry[1], reverse=True)
    return [entry[0] for entry in ranked[:MAX_SEARCH_CANDIDATES]]


def fetch_store_listing(
    app_id: str,
    country: str = DEFAULT_COUNTRY,
    lang: str | None = None,
) -> StoreListing:
    value = app_id.strip()
    if not value:
        raise ValueError("请输入游戏包名。")

    resolved_lang = lang or default_language(country, fallback=DEFAULT_LANGUAGE)
    raw = gp_app(value, lang=resolved_lang, country=country)
    return _map_listing(raw, country=country)


def fetch_multi_market_listings(app_id: str, countries: list[str]) -> list[MarketListingOutcome]:
    outcomes: list[MarketListingOutcome] = []
    for country in countries:
        try:
            listing = fetch_store_listing(app_id, country=country)
        except NotFoundError:
            outcomes.append(MarketListingOutcome(country=country, status="unavailable"))
        except GooglePlayScraperException as exc:
            outcomes.append(MarketListingOutcome(country=country, status="error", error=str(exc)))
        except Exception as exc:
            # A single market's failure (network/parsing/rate limit) must never abort the batch.
            outcomes.append(MarketListingOutcome(country=country, status="error", error=str(exc)))
        else:
            outcomes.append(MarketListingOutcome(country=country, status="ok", listing=listing))
    return outcomes


def _map_search_result(item: dict) -> GameSearchResult:
    return GameSearchResult(
        app_id=str(item.get("appId", "")),
        title=str(item.get("title", "")),
        developer=str(item.get("developer", "")),
        icon=str(item.get("icon", "")),
        score=_to_float(item.get("score")),
    )


def _map_listing(raw: dict, country: str) -> StoreListing:
    return StoreListing(
        title=str(raw.get("title", "")),
        app_id=str(raw.get("appId", "")),
        developer=str(raw.get("developer", "")),
        genre=str(raw.get("genre", "")),
        score=_to_float(raw.get("score")),
        ratings=_to_int(raw.get("ratings")),
        reviews=_to_int(raw.get("reviews")),
        installs=str(raw.get("installs") or ""),
        min_installs=_to_int(raw.get("minInstalls")),
        real_installs=_to_int(raw.get("realInstalls")),
        offers_iap=bool(raw.get("offersIAP", False)),
        contains_ads=bool(raw.get("containsAds", False)),
        released=str(raw.get("released") or ""),
        last_updated_on=str(raw.get("lastUpdatedOn") or ""),
        version=str(raw.get("version") or ""),
        icon=str(raw.get("icon") or ""),
        country=country,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

from __future__ import annotations

from google_play_scraper.exceptions import ExtraHTTPError, NotFoundError

from src import store_performance


def _raw_search_item(**overrides) -> dict:
    base = {
        "appId": "com.example.game",
        "icon": "https://example.com/icon.png",
        "title": "Example Game",
        "developer": "Example Studio",
        "score": 4.3,
    }
    base.update(overrides)
    return base


def _raw_app_detail(**overrides) -> dict:
    base = {
        "title": "Example Game",
        "appId": "com.example.game",
        "developer": "Example Studio",
        "genre": "Role Playing",
        "score": 4.3,
        "ratings": 12345,
        "reviews": 6789,
        "installs": "10,000,000+",
        "minInstalls": 10000000,
        "realInstalls": 15234567,
        "offersIAP": True,
        "containsAds": False,
        "released": "Jan 1, 2024",
        "lastUpdatedOn": "Aug 1, 2026",
        "version": "2.3.1",
        "icon": "https://example.com/icon.png",
    }
    base.update(overrides)
    return base


def test_search_games_maps_fields(monkeypatch) -> None:
    def fake_search(*args, **kwargs):
        return [_raw_search_item()]

    monkeypatch.setattr(store_performance, "gp_search", fake_search)

    results = store_performance.search_games("example")

    assert len(results) == 1
    result = results[0]
    assert result.app_id == "com.example.game"
    assert result.title == "Example Game"
    assert result.developer == "Example Studio"
    assert result.icon == "https://example.com/icon.png"
    assert result.score == 4.3


def test_search_games_handles_missing_optional_fields(monkeypatch) -> None:
    def fake_search(*args, **kwargs):
        return [_raw_search_item(score=None, icon="")]

    monkeypatch.setattr(store_performance, "gp_search", fake_search)

    results = store_performance.search_games("example")

    assert len(results) == 1
    assert results[0].score is None
    assert results[0].icon == ""


def test_search_games_empty_query_raises() -> None:
    try:
        store_performance.search_games("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty query")


def test_fetch_store_listing_maps_all_required_fields(monkeypatch) -> None:
    def fake_app(*args, **kwargs):
        return _raw_app_detail()

    monkeypatch.setattr(store_performance, "gp_app", fake_app)

    listing = store_performance.fetch_store_listing("com.example.game", country="jp")

    assert listing.title == "Example Game"
    assert listing.app_id == "com.example.game"
    assert listing.developer == "Example Studio"
    assert listing.genre == "Role Playing"
    assert listing.score == 4.3
    assert listing.ratings == 12345
    assert listing.reviews == 6789
    assert listing.installs == "10,000,000+"
    assert listing.min_installs == 10000000
    assert listing.real_installs == 15234567
    assert listing.offers_iap is True
    assert listing.contains_ads is False
    assert listing.released == "Jan 1, 2024"
    assert listing.last_updated_on == "Aug 1, 2026"
    assert listing.version == "2.3.1"
    assert listing.icon == "https://example.com/icon.png"
    assert listing.country == "jp"
    assert listing.fetched_at


def test_fetch_store_listing_uses_market_default_language(monkeypatch) -> None:
    seen_lang = {}

    def fake_app(app_id, lang, country):
        seen_lang["lang"] = lang
        return _raw_app_detail()

    monkeypatch.setattr(store_performance, "gp_app", fake_app)

    store_performance.fetch_store_listing("com.example.game", country="jp")
    assert seen_lang["lang"] == "ja"

    store_performance.fetch_store_listing("com.example.game", country="kr")
    assert seen_lang["lang"] == "ko"

    store_performance.fetch_store_listing("com.example.game", country="us")
    assert seen_lang["lang"] == "en"


def test_fetch_store_listing_propagates_not_found(monkeypatch) -> None:
    def fake_app(*args, **kwargs):
        raise NotFoundError("App not found(404).")

    monkeypatch.setattr(store_performance, "gp_app", fake_app)

    try:
        store_performance.fetch_store_listing("com.example.game", country="us")
    except NotFoundError:
        pass
    else:
        raise AssertionError("Expected NotFoundError to propagate")


def test_multi_market_marks_unavailable_without_failing_others(monkeypatch) -> None:
    def fake_app(app_id, lang, country):
        if country == "vn":
            raise NotFoundError("App not found(404).")
        return _raw_app_detail()

    monkeypatch.setattr(store_performance, "gp_app", fake_app)

    outcomes = store_performance.fetch_multi_market_listings("com.example.game", ["us", "vn", "jp"])

    by_country = {outcome.country: outcome for outcome in outcomes}
    assert len(outcomes) == 3
    assert by_country["vn"].status == "unavailable"
    assert by_country["vn"].listing is None
    assert by_country["us"].status == "ok"
    assert by_country["us"].listing is not None
    assert by_country["jp"].status == "ok"


def test_multi_market_marks_error_without_failing_others(monkeypatch) -> None:
    def fake_app(app_id, lang, country):
        if country == "de":
            raise ExtraHTTPError("Status code 503 returned.")
        if country == "fr":
            raise RuntimeError("unexpected parsing failure")
        return _raw_app_detail()

    monkeypatch.setattr(store_performance, "gp_app", fake_app)

    outcomes = store_performance.fetch_multi_market_listings("com.example.game", ["us", "de", "fr"])

    by_country = {outcome.country: outcome for outcome in outcomes}
    assert by_country["de"].status == "error"
    assert by_country["de"].error
    assert by_country["fr"].status == "error"
    assert by_country["fr"].error
    assert by_country["us"].status == "ok"


def test_multi_market_all_fail_still_returns_list(monkeypatch) -> None:
    def fake_app(*args, **kwargs):
        raise NotFoundError("App not found(404).")

    monkeypatch.setattr(store_performance, "gp_app", fake_app)

    outcomes = store_performance.fetch_multi_market_listings("com.example.game", ["us", "jp", "kr"])

    assert len(outcomes) == 3
    assert all(outcome.status == "unavailable" for outcome in outcomes)

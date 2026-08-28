from __future__ import annotations

import app
from src import store_performance
from src.google_play import extract_package_name


def test_extract_package_name_passthrough_for_bare_package() -> None:
    assert extract_package_name("com.example.game") == "com.example.game"


def test_search_langs_tries_chinese_locales_for_cjk_query() -> None:
    langs = store_performance._search_langs("终末地", "en")
    assert langs[:2] == ["zh", "zh-TW"]
    assert "en" in langs


def test_search_langs_keeps_single_locale_for_ascii_query() -> None:
    assert store_performance._search_langs("Genshin Impact", "en") == ["en"]


def test_search_games_ranks_exact_title_match_above_unrelated_relative(monkeypatch) -> None:
    # "明日方舟" (plain Arknights) is Google Play's own rank-0 result and shares zero
    # characters with the query "终末地" -- per the fix, a rank-0 result must never be
    # dropped just for that, so it still appears, but the containment-tier match
    # ("明日方舟：终末地" literally contains "终末地") must outrank it.
    fake_results = [
        {"appId": "com.hypergryph.arknights", "title": "明日方舟", "developer": "Hypergryph", "icon": "", "score": 4.5},
        {"appId": "com.hypergryph.endfield", "title": "明日方舟：终末地", "developer": "Hypergryph", "icon": "", "score": 4.7},
    ]

    def fake_gp_search(value, n_hits, lang, country):
        return fake_results

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("终末地", country="us", lang="en")

    result_ids = [result.app_id for result in results]
    assert result_ids[0] == "com.hypergryph.endfield"
    assert "com.hypergryph.arknights" in result_ids


def test_search_games_merges_and_dedupes_across_locales(monkeypatch) -> None:
    seen_langs = []

    def fake_gp_search(value, n_hits, lang, country):
        seen_langs.append(lang)
        return [
            {"appId": "com.example.game", "title": "终末地", "developer": "Studio", "icon": "", "score": 4.0},
        ]

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("终末地", country="us", lang="en")

    assert len(results) == 1
    assert seen_langs == ["zh", "zh-TW", "en"]


def test_search_games_raises_only_when_every_locale_fails(monkeypatch) -> None:
    def fake_gp_search(value, n_hits, lang, country):
        raise RuntimeError("network down")

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    try:
        store_performance.search_games("终末地", country="us", lang="en")
    except RuntimeError as exc:
        assert str(exc) == "network down"
    else:
        raise AssertionError("expected RuntimeError to propagate when all locales fail")


def test_search_games_genshin_official_outranks_materials_note_app(monkeypatch) -> None:
    fake_results = [
        {"appId": "com.miHoYo.GenshinImpact", "title": "原神", "developer": "COGNOSPHERE", "icon": "", "score": 3.2},
        {"appId": "net.chikach.genshinmaterial", "title": "原神素材ノート", "developer": "C2K Studio", "icon": "", "score": None},
    ]

    def fake_gp_search(value, n_hits, lang, country):
        return fake_results

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("原神", country="us", lang="en")

    assert results[0].app_id == "com.miHoYo.GenshinImpact"


def test_search_games_genshin_official_outranks_cloud_variant(monkeypatch) -> None:
    fake_results = [
        {"appId": "com.miHoYo.GenshinImpact", "title": "Genshin Impact", "developer": "COGNOSPHERE", "icon": "", "score": 3.2},
        {"appId": "com.hoyoverse.cloudgames.GenshinImpact", "title": "Genshin Impact · Cloud", "developer": "COGNOSPHERE", "icon": "", "score": 3.1},
    ]

    def fake_gp_search(value, n_hits, lang, country):
        return fake_results

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("Genshin Impact", country="us", lang="en")

    assert results[0].app_id == "com.miHoYo.GenshinImpact"


def test_search_games_endfield_query_returns_endfield(monkeypatch) -> None:
    fake_results = [
        {"appId": "com.gryphline.endfield.gp", "title": "明日方舟：终末地", "developer": "GRYPHLINE", "icon": "", "score": 4.6},
    ]

    def fake_gp_search(value, n_hits, lang, country):
        return fake_results

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("终末地", country="us", lang="en")

    assert any(result.app_id == "com.gryphline.endfield.gp" for result in results)


def test_search_games_endfield_english_query_outranks_plain_arknights(monkeypatch) -> None:
    fake_results = [
        {"appId": "com.gryphline.endfield.gp", "title": "Arknights: Endfield", "developer": "GRYPHLINE", "icon": "", "score": 4.6},
        {"appId": "com.YoStarEN.Arknights", "title": "Arknights", "developer": "Yostar Limited.", "icon": "", "score": 4.3},
    ]

    def fake_gp_search(value, n_hits, lang, country):
        return fake_results

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("Arknights: Endfield", country="us", lang="en")

    assert results[0].app_id == "com.gryphline.endfield.gp"


def test_search_games_low_relevance_fuzzy_match_does_not_sneak_past_threshold(monkeypatch) -> None:
    fake_results = [
        {"appId": "com.gryphline.endfield.gp", "title": "Arknights: Endfield", "developer": "GRYPHLINE", "icon": "", "score": 4.6},
        {"appId": "com.YoStarEN.Arknights", "title": "Arknights", "developer": "Yostar Limited.", "icon": "", "score": 4.3},
        {"appId": "com.kurogame.punishing", "title": "Punishing: Gray Raven", "developer": "Kuro Games", "icon": "", "score": 4.4},
    ]

    def fake_gp_search(value, n_hits, lang, country):
        return fake_results

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("Arknights: Endfield", country="us", lang="en")

    assert all(result.app_id != "com.kurogame.punishing" for result in results)


def test_search_games_keeps_best_rank_when_same_appid_seen_across_locales(monkeypatch) -> None:
    def fake_gp_search(value, n_hits, lang, country):
        if lang == "zh":
            return [
                {"appId": "com.unrelated.filler", "title": "filler", "developer": "X", "icon": "", "score": 1.0},
                {"appId": "com.gryphline.endfield.gp", "title": "明日方舟：终末地", "developer": "GRYPHLINE", "icon": "", "score": 4.6},
            ]
        # In this locale it is the rank-0 (best) result.
        return [
            {"appId": "com.gryphline.endfield.gp", "title": "Arknights: Endfield", "developer": "GRYPHLINE", "icon": "", "score": 4.6},
        ]

    monkeypatch.setattr(store_performance, "gp_search", fake_gp_search)

    results = store_performance.search_games("终末地", country="us", lang="en")

    matches = [result for result in results if result.app_id == "com.gryphline.endfield.gp"]
    assert len(matches) == 1
    # The best-rank locale's title ("Arknights: Endfield") must win the merge, not
    # the rank-1 "明日方舟：终末地" record.
    assert matches[0].title == "Arknights: Endfield"


def test_sync_picker_query_state_clears_candidates_on_new_query() -> None:
    session_state = {
        "single_picker_last_query": "原神",
        "single_picker_candidates_v2": ["stale-candidate"],
    }

    app._sync_picker_query_state(session_state, "single", "终末地")

    assert "single_picker_candidates_v2" not in session_state
    assert session_state["single_picker_last_query"] == "终末地"


def test_sync_picker_query_state_keeps_candidates_when_query_unchanged() -> None:
    session_state = {
        "single_picker_last_query": "原神",
        "single_picker_candidates_v2": ["kept-candidate"],
    }

    app._sync_picker_query_state(session_state, "single", "原神")

    assert session_state["single_picker_candidates_v2"] == ["kept-candidate"]


def test_picker_choice_labels_default_option_is_always_the_placeholder() -> None:
    from src.models import GameSearchResult

    candidates = [
        GameSearchResult(app_id="com.example.a", title="Example A", developer="Dev", icon="", score=4.0),
        GameSearchResult(app_id="com.example.b", title="Example B", developer="Dev", icon="", score=4.1),
    ]

    labels = app._picker_choice_labels(candidates)

    assert labels[0] == app.PICKER_PLACEHOLDER
    assert labels[1] == "Example A · Dev · com.example.a"


def test_cached_fetch_store_listing_delegates_to_store_performance(monkeypatch) -> None:
    seen = {}

    def fake_fetch_store_listing(app_id, country=None):
        seen["app_id"] = app_id
        seen["country"] = country
        return app.StoreListing(
            title="Example Game",
            app_id=app_id,
            developer="Example Studio",
            genre="Role Playing",
            score=4.3,
            ratings=12345,
            reviews=6789,
            installs="10,000,000+",
            min_installs=10000000,
            real_installs=15234567,
            offers_iap=True,
            contains_ads=False,
            released="Jan 1, 2024",
            last_updated_on="Aug 1, 2026",
            version="2.3.1",
            icon="https://example.com/icon.png",
            country=country,
            fetched_at="2026-08-20T00:00:00+00:00",
        )

    monkeypatch.setattr(app, "fetch_store_listing", fake_fetch_store_listing)

    listing = app._cached_fetch_store_listing.__wrapped__("com.example.game", "us")

    assert seen == {"app_id": "com.example.game", "country": "us"}
    assert listing.app_id == "com.example.game"
    assert listing.title == "Example Game"

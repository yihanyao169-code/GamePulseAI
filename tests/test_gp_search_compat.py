from __future__ import annotations

from src.gp_search_compat import _TOP_RESULT_APP_ID_SPEC, _SEARCH_RESULT_ON_TOP_SPECS


def test_new_appid_path_resolves_when_present() -> None:
    # Upstream PR #239's new path: source[3]["12"][0][0]
    fake_top_result = {3: {"12": [["com.example.newpath"]]}, 11: [["com.example.oldpath"]]}

    assert _TOP_RESULT_APP_ID_SPEC.extract_content(fake_top_result) == "com.example.newpath"


def test_old_appid_path_resolves_when_new_path_key_absent() -> None:
    # Legacy path: source[11][0][0]. No key 3 at all -- the currently-broken
    # real-world case this compatibility layer exists to handle.
    fake_top_result = {11: [["com.example.oldpath"]]}

    assert _TOP_RESULT_APP_ID_SPEC.extract_content(fake_top_result) == "com.example.oldpath"


def test_new_path_failure_falls_back_to_old_path() -> None:
    # Key 3 present but shaped so the new path's traversal fails partway through
    # (e.g. missing the "12" sub-key), forcing the fallback chain to engage.
    fake_top_result = {3: {"not-12": []}, 11: [["com.example.oldpath"]]}

    assert _TOP_RESULT_APP_ID_SPEC.extract_content(fake_top_result) == "com.example.oldpath"


def test_both_paths_failing_resolves_to_none_safely() -> None:
    fake_top_result = {"unrelated": "data"}

    assert _TOP_RESULT_APP_ID_SPEC.extract_content(fake_top_result) is None


def test_top_result_specs_only_override_appid() -> None:
    # Every other field on the top-result spec must be untouched -- this fix is
    # scoped to the one broken field, not a wholesale replacement of the spec.
    from google_play_scraper.constants.element import ElementSpecs

    for key, spec in ElementSpecs.SearchResultOnTop.items():
        if key == "appId":
            continue
        assert _SEARCH_RESULT_ON_TOP_SPECS[key] is spec

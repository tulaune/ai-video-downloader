from backend.downloader import _safe_filename


def test_safe_filename_replaces_path_and_control_characters():
    assert _safe_filename('a/b:c*?"<x>|') == "a_b_c____x__"


def test_safe_filename_collapses_whitespace_and_has_fallback():
    assert _safe_filename("  hello   world  ") == "hello world"
    assert _safe_filename("   ") == "video"

from backend.crawler import _find_aweme_list, _get_download_url, _is_douyin_api, _parse_aweme


def _item():
    return {
        "aweme_id": "123",
        "desc": "  Một video thử nghiệm  ",
        "author": {"nickname": "Tác giả"},
        "video": {
            "play_addr": {
                "url_list": ["https://cdn.example/video.mp4?logo_name=x&quality=hd"]
            }
        },
    }


def test_parse_aweme_normalizes_metadata_and_removes_watermark_query():
    parsed = _parse_aweme(_item())

    assert parsed == {
        "aweme_id": "123",
        "title": "Một video thử nghiệm",
        "author": "Tác giả",
        "download_url": "https://cdn.example/video.mp4?quality=hd",
    }


def test_find_aweme_list_walks_nested_response():
    assert _find_aweme_list({"data": {"aweme_list": [_item()]}}) == [_item()]


def test_crawler_only_accepts_douyin_api_urls():
    assert _is_douyin_api("https://www.douyin.com/web/api/item")
    assert not _is_douyin_api("http://www.douyin.com/web/api/item")
    assert not _is_douyin_api("https://example.com/web/api/item")


def test_download_url_returns_none_when_no_stream_exists():
    assert _get_download_url({}) is None

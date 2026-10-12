import asyncio

from backend import store


def test_store_upserts_download_and_caption_without_losing_download_data(tmp_path):
    original_path = store.INDEX_PATH
    store.INDEX_PATH = tmp_path / "index.csv"
    try:
        asyncio.run(
            store.upsert_download(
                aweme_id="123",
                author="Author",
                title="Title",
                local_path="downloads/123/index.mp4",
                download_url="https://cdn.example/123.mp4",
                status="success",
            )
        )
        asyncio.run(store.upsert_caption("123", "Caption tiếng Việt"))

        row = store.get_row("123")
        assert row["status"] == "success"
        assert row["local_path"] == "downloads/123/index.mp4"
        assert row["whisper-caption"] == "Caption tiếng Việt"
        assert row["transcribed_at"]
    finally:
        store.INDEX_PATH = original_path


def test_get_aweme_id_from_folder_path():
    assert store.get_aweme_id_from_path("downloads/author__title__123/index.mp4") == "123"
    assert store.get_aweme_id_from_path("/tmp/video.mp4") is None

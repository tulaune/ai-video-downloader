from pathlib import Path

from backend.transcribe import _get_video_folder


def test_get_video_folder_supports_index_mp4_layout(tmp_path):
    folder = tmp_path / "video"
    path = folder / "index.mp4"
    assert _get_video_folder(path) == folder


def test_get_video_folder_rejects_flat_layout(tmp_path):
    assert _get_video_folder(tmp_path / "video.mp4") is None

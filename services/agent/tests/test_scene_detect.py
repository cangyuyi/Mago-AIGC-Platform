"""Regression tests for PySceneDetect integration."""

from __future__ import annotations

import pytest

from src.video_tools.scene_detect import SceneDetector


@pytest.mark.asyncio
async def test_scene_detector_converts_seconds_to_integer_frames(monkeypatch) -> None:
    import scenedetect
    import scenedetect.detectors

    class FakeTime:
        def __init__(self, seconds: float):
            self.seconds = seconds

        def get_seconds(self) -> float:
            return self.seconds

        def __sub__(self, other: FakeTime) -> FakeTime:
            return FakeTime(self.seconds - other.seconds)

    class FakeVideo:
        frame_rate = 25.0
        closed = False

        def close(self) -> None:
            self.closed = True

    class FakeSceneManager:
        detector = None

        def add_detector(self, detector) -> None:
            self.detector = detector

        def detect_scenes(self, video, show_progress: bool) -> None:
            assert video is fake_video
            assert show_progress is False

        def get_scene_list(self):
            return [(FakeTime(0.0), FakeTime(1.0))]

    class FakeContentDetector:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_video = FakeVideo()
    fake_manager = FakeSceneManager()
    monkeypatch.setattr(scenedetect, "open_video", lambda _: fake_video)
    monkeypatch.setattr(scenedetect, "SceneManager", lambda: fake_manager)
    monkeypatch.setattr(scenedetect.detectors, "ContentDetector", FakeContentDetector)

    shots = await SceneDetector(min_shot_len=0.8).detect("unused.mp4")

    assert fake_manager.detector.kwargs["min_scene_len"] == 20
    assert shots[0].duration == 1.0
    assert fake_video.closed is True

"""Decode once to upright timestamped frames and a silent, browser-safe MP4."""
from dataclasses import dataclass
from pathlib import Path
import av
import cv2
import numpy as np


@dataclass
class Frame:
    index: int
    time: float
    image: np.ndarray


def decode(path: Path):
    """Presentation timestamps, not nominal FPS, are the time source."""
    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise ValueError("The upload contains no video stream.")
            stream = container.streams.video[0]
            origin = None
            previous = -1.0
            for index, frame in enumerate(container.decode(stream)):
                if frame.time is None:
                    raise ValueError("Video has missing timestamps. Re-export it as MP4 and retry.")
                if origin is None:
                    origin = float(frame.time)
                time = float(frame.time) - origin
                if time <= previous:
                    raise ValueError("Video timestamps are not increasing. Re-export it as MP4.")
                previous = time
                image = frame.to_ndarray(format="bgr24")
                # PyAV exposes display-matrix rotation on decoded frames (CCW degrees).
                rotation = round(getattr(frame, "rotation", 0)) % 360
                if rotation == 90:
                    image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif rotation == 180:
                    image = cv2.rotate(image, cv2.ROTATE_180)
                elif rotation == 270:
                    image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                yield Frame(index, time, image)
    except (av.error.FFmpegError, OSError) as exc:
        raise ValueError("Cannot decode this video. Try a valid MOV or MP4 with H.264 video.") from exc


def metadata(path: Path):
    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise ValueError("The upload contains no video stream.")
            stream = container.streams.video[0]
            return {"expected_frames": stream.frames or 0,
                    "nominal_fps": float(stream.average_rate or 30)}
    except (av.error.FFmpegError, OSError) as exc:
        raise ValueError("Cannot open this video. Try a valid MOV or MP4.") from exc


class PlaybackWriter:
    """Preserve relative timestamps, with no dependency on a system ffmpeg executable."""
    def __init__(self, path: Path, width: int, height: int):
        from fractions import Fraction
        self.time_base = Fraction(1, 90000)
        self.container = av.open(str(path), "w", options={"movflags": "+faststart"})
        self.stream = self.container.add_stream("libx264", rate=30)
        self.stream.width = width + width % 2
        self.stream.height = height + height % 2
        self.stream.pix_fmt = "yuv420p"
        self.stream.time_base = self.time_base
        self.stream.codec_context.time_base = self.time_base
        self.stream.options = {"crf": "23", "preset": "veryfast", "bf": "0"}

    def write(self, frame: Frame):
        image = frame.image
        if image.shape[1] % 2 or image.shape[0] % 2:
            image = cv2.copyMakeBorder(image, 0, image.shape[0] % 2,
                                      0, image.shape[1] % 2, cv2.BORDER_REPLICATE)
        out = av.VideoFrame.from_ndarray(image, format="bgr24")
        out.pts = round(frame.time / self.time_base)
        out.time_base = self.time_base
        for packet in self.stream.encode(out):
            self.container.mux(packet)

    def close(self):
        try:
            for packet in self.stream.encode():
                self.container.mux(packet)
        finally:
            self.container.close()

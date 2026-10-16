"""Impact sounds ("thumps") from the clip's audio track, as separate touch evidence.

A ball touch makes a short broadband impact. Spectral flux measures how much the sound
spectrum suddenly *increases* between neighbouring 10 ms steps; impacts give sharp peaks.
Floor bounces, footsteps and other knocks also make thumps, so this module only reports
onsets. Deciding what an onset means is left to `counting.py`, using the video evidence.
"""
from pathlib import Path
import av
import numpy as np

WINDOW = 1024     # samples per analysis window (~23 ms at 44.1 kHz)
STEP_SECONDS = 0.01
MIN_SPACING = 0.2  # seconds between reported onsets; keeps the stronger one


def onset_strengths(samples, rate):
    """Normalised spectral-flux envelope and the time (s) at the centre of each step."""
    hop = max(1, int(rate * STEP_SECONDS))
    if len(samples) < WINDOW + hop:
        return np.zeros(0), np.zeros(0)
    frames = np.lib.stride_tricks.sliding_window_view(samples, WINDOW)[::hop] * np.hanning(WINDOW)
    magnitude = np.log1p(np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.maximum(np.diff(magnitude, axis=0), 0).sum(1)
    # Scale so typical background is ~0 and loud transients are well above 1 (clip-relative).
    median = np.median(flux)
    flux = (flux - median) / (np.percentile(flux, 95) - median + 1e-9)
    times = (np.arange(len(flux)) + 1) * hop / rate + WINDOW / 2 / rate
    return flux, times


def pick_peaks(flux, times, minimum=1.5):
    """Local maxima above `minimum`, strongest first, at least MIN_SPACING apart."""
    peaks = [i for i in range(1, len(flux) - 1)
             if flux[i] >= flux[i - 1] and flux[i] > flux[i + 1] and flux[i] > minimum]
    chosen = []
    for i in sorted(peaks, key=lambda i: -flux[i]):
        if all(abs(times[i] - times[j]) > MIN_SPACING for j in chosen):
            chosen.append(i)
    return sorted((float(times[i]), float(flux[i])) for i in chosen)


def onsets(path: Path):
    """[(time, strength)] relative to the first decoded video frame, or [] without audio."""
    with av.open(str(path)) as container:
        if not container.streams.audio or not container.streams.video:
            return []
        video = container.streams.video[0]
        first = next(container.decode(video))
        video_start = float(first.pts * video.time_base)
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        rate, chunks, audio_start = stream.rate, [], None
        for frame in container.decode(stream):
            if audio_start is None and frame.pts is not None:
                audio_start = float(frame.pts * frame.time_base)
            data = frame.to_ndarray().astype(np.float32)
            # Planar audio is (channels, n); packed audio is (1, n * channels). Mix to mono.
            channels = len(frame.layout.channels)
            data = data.reshape(channels, -1) if data.shape[0] == channels else data.reshape(-1, channels).T
            chunks.append(data.mean(0))
    if not chunks:
        return []
    flux, times = onset_strengths(np.concatenate(chunks), rate)
    offset = (audio_start or 0.0) - video_start
    return [(t + offset, s) for t, s in pick_peaks(flux, times)]

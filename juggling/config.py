from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Config:
    # All time thresholds are seconds; distances are relative to ball diameter.
    detector: str = "yolo11s.pt"
    pose_model: str = "yolo11n-pose.pt"
    # Heel/toe landmarks (RTMPose-x Halpe-26). Empty string disables them; the
    # ankle-based foot estimate below is then the only foot evidence.
    foot_model: str = "rtmpose-x-halpe26.onnx"
    image_size: int = 640
    pose_size: int = 640
    detection_threshold: float = 0.05
    landmark_threshold: float = 0.35
    prediction_seconds: float = 0.15
    minimum_size_ratio: float = 0.75  # Abrupt shrinkage often indicates a shoe switch.
    edge_outward_fraction: float = 0.2  # Normal component relative to total motion.
    edge_margin_diameters: float = 0.05
    edge_outward_diameters_per_second: float = 0.5
    association_diameters: float = 3.0
    contact_diameters: float = 1.15
    # Fallback when heel/toe points are missing: estimated foot half-length beside each
    # ankle, relative to knee-ankle length. Roughly anatomical; not fitted to clip totals.
    foot_length_shin_ratio: float = 0.6
    # Stop/catch markers: observed ball stays within this radius for at least stop_seconds.
    stop_seconds: float = 1.0
    stop_radius_diameters: float = 0.5
    stop_gap_seconds: float = 0.2
    # Impact sounds (thumps). Strength is clip-normalised spectral flux (see audio.py).
    # The strength gate was chosen on the seven development clips: heard touches there were
    # >= 8.8, rejected non-touch thumps <= 6.6. It is a thin, footage-specific margin.
    audio_enabled: bool = True
    audio_min_strength: float = 8.0
    audio_match_seconds: float = 0.12
    rhythm_min_beats: float = 0.6   # heard touch spacing, in multiples of the median touch interval
    rhythm_max_beats: float = 1.6
    audio_return_seconds: float = 1.0
    debounce_seconds: float = 0.22
    velocity_window_seconds: float = 0.14
    min_velocity_diameters: float = 0.7
    appearance_enabled: bool = True
    appearance_horizon_seconds: float = 0.25
    appearance_similarity: float = 0.60
    device: str = "cpu"  # CPU is predictable on macOS; MPS can be selected in CLI.

    def to_dict(self):
        return asdict(self)

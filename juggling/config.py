from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Config:
    # All time thresholds are seconds; distances are relative to ball diameter.
    detector: str = "yolo11s.pt"
    pose_model: str = "yolo11n-pose.pt"
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
    # Estimated foot half-length beside each ankle, relative to knee-ankle length.
    # Roughly anatomical (foot ~0.6 of shin); not fitted to the clip totals.
    foot_length_shin_ratio: float = 0.6
    # Stop/catch markers: observed ball stays within this radius for at least stop_seconds.
    stop_seconds: float = 1.0
    stop_radius_diameters: float = 0.5
    stop_gap_seconds: float = 0.2
    debounce_seconds: float = 0.22
    velocity_window_seconds: float = 0.14
    min_velocity_diameters: float = 0.7
    appearance_enabled: bool = True
    appearance_horizon_seconds: float = 0.25
    appearance_similarity: float = 0.60
    device: str = "cpu"  # CPU is predictable on macOS; MPS can be selected in CLI.

    def to_dict(self):
        return asdict(self)

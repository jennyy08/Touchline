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
    association_diameters: float = 3.0
    contact_diameters: float = 1.15
    debounce_seconds: float = 0.22
    velocity_window_seconds: float = 0.14
    min_velocity_diameters: float = 0.7
    appearance_enabled: bool = True
    appearance_horizon_seconds: float = 0.25
    appearance_similarity: float = 0.60
    device: str = "cpu"  # CPU is predictable on macOS; MPS can be selected in CLI.

    def to_dict(self):
        return asdict(self)

"""Small reproducibility record; no machine paths or environment secrets."""
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def file_sha256(path):
    digest = sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inference_provenance(models, config, include_pose=True):
    packages = {}
    for name in ('torch', 'ultralytics', 'onnxruntime', 'opencv-python', 'av', 'numpy'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    names = [config.detector]
    if include_pose:
        names.extend([config.pose_model, config.foot_model])
    weights = {name: file_sha256(models / name) for name in names if name}
    import torch
    return {'packages': packages, 'model_sha256': weights,
            'device_requested': config.device,
            'torch_threads': torch.get_num_threads(),
            'torch_deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'torch_float32_matmul_precision': torch.get_float32_matmul_precision()}


def compare_observations(before, after):
    """Compare inference separately from counting; never interpret agreement as accuracy."""
    if before['video']['sha256'] != after['video']['sha256']:
        raise ValueError('Results belong to different input videos.')
    a, b = before['samples'], after['samples']
    if len(a) != len(b) or any((x['frame'], x['time']) != (y['frame'], y['time'])
                             for x, y in zip(a, b)):
        raise ValueError('Decoded frame counts or timestamps differ; compare decoding first.')
    fields = ('status', 'box', 'center', 'diameter', 'segment', 'pose', 'detail_pose', 'motion_pose')
    changes = {field: [x['frame'] for x,y in zip(a,b) if x.get(field) != y.get(field)]
               for field in fields}
    return {'frames': len(a), 'changed_frames': changes,
            'observations_identical': not any(changes.values()),
            'events_identical': before['events'] == after['events'],
            'before_count': before['estimated_count'], 'after_count': after['estimated_count'],
            'config_identical': before.get('config') == after.get('config'),
            'provenance_available': bool(before.get('inference_provenance') and after.get('inference_provenance')),
            'provenance_identical': (before['inference_provenance'] == after['inference_provenance']
                                     if before.get('inference_provenance') and after.get('inference_provenance') else None)}

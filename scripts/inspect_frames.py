"""Save selected timestamp-aligned frames with tracker output for debugging."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from juggling.video import decode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('result', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--frames', type=int, nargs='+', required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    wanted = set(args.frames)
    tiles = []
    for frame in decode(args.video):
        if frame.index not in wanted:
            continue
        sample = result['samples'][frame.index]
        if abs(sample['time'] - frame.time) > .002:
            raise ValueError('Video timestamps do not match the saved analysis.')
        image = frame.image.copy()
        if sample['box']:
            x1, y1, x2, y2 = map(int, sample['box'])
            color = (40,220,80) if sample['source'] == 'detector' else (200,220,40)
            if sample['status'] == 'predicted': color = (0,170,255)
            cv2.rectangle(image, (x1,y1), (x2,y2), color, 4)
        image = cv2.resize(image, (540,360))
        label = f'{frame.index} | {frame.time:.3f}s | {sample["status"]} {sample["source"] or ""}'
        for color, thickness in [((0,0,0),3), ((255,255,255),1)]:
            cv2.putText(image,label,(10,25),cv2.FONT_HERSHEY_SIMPLEX,.5,color,thickness)
        tiles.append(image)
    if not tiles:
        raise ValueError('No requested frames were decoded.')
    while len(tiles) % 3: tiles.append(np.zeros_like(tiles[0]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output),np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]))


if __name__ == '__main__':
    main()

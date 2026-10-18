"""Static-camera background filter for ground-drill object detections.

A temporal median keeps fixed room objects (including paddle false positives)
out of the ball track. It is not a colour rule. Use only with a fixed camera.
"""
import cv2
import numpy as np
from .video import decode


def background(source, progress=lambda **kw:None):
    images=[]; next_time=0
    for f in decode(source):
        if f.time>180:
            raise ValueError('This prototype supports clips up to 3 minutes. Trim the video and retry.')
        if f.time >= next_time:
            images.append(cv2.resize(f.image,(480,320)))
            next_time=f.time+1
            progress(stage='reading_scene',frames=f.index+1,total=0)
    if not images: raise ValueError('No readable video frames.')
    return np.median(images,axis=0).astype(np.uint8)


def moving_detections(image, detections, reference):
    h,w=image.shape[:2]
    small=cv2.resize(image,(480,320))
    change=np.max(cv2.absdiff(small,reference),axis=2)>35
    kept=[]
    for d in detections:
        x1,y1,x2,y2=d['box']; dx=(x2-x1)*.2; dy=(y2-y1)*.2
        a,b,c,e=[int(v) for v in ((x1+dx)*480/w,(y1+dy)*320/h,(x2-dx)*480/w,(y2-dy)*320/h)]
        patch=change[max(0,b):min(320,e),max(0,a):min(480,c)]
        if patch.size and patch.mean()>=.2:kept.append(d)
    return kept

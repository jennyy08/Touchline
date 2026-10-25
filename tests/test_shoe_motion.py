import cv2
import numpy as np
from juggling.shoe_motion import ShoeMotion


def example():
    rng=np.random.default_rng(7)
    image=np.zeros((240,320,3),np.uint8)
    image[50:95,50:110]=rng.integers(0,256,(45,60,3),dtype=np.uint8)
    sample=dict(time=0.,diameter=60.,center=[220.,190.],pose={
        'left_big_toe':[90.,80.],'left_small_toe':[90.,85.],'left_heel':[60.,75.]})
    return image,sample


def test_measured_translation_bridges_missing_toes_briefly():
    image,sample=example();tracker=ShoeMotion();tracker.observe(image,sample)
    moved=cv2.warpAffine(image,np.float32([[1,0,8],[0,1,3]]),(320,240))
    pose,meta=tracker.observe(moved,dict(sample,time=.033,pose={}))
    assert meta['bridged']==['left']
    assert np.allclose(pose['left_big_toe'],[98,83],atol=.6)
    # No indefinite visual propagation without a new detector observation.
    pose,meta=tracker.observe(moved,dict(sample,time=.3,pose={}))
    assert not pose and not meta['bridged']


def test_blank_image_does_not_invent_observations():
    _,s=example();blank=np.zeros((240,320,3),np.uint8);tracker=ShoeMotion()
    tracker.observe(blank,s)
    pose,meta=tracker.observe(blank,dict(s,time=.03,pose={}))
    assert pose=={} and meta['bridged']==[]


def test_resolution_change_resets_motion():
    image,s=example();tracker=ShoeMotion();tracker.observe(image,s)
    pose,meta=tracker.observe(np.zeros((100,100,3),np.uint8),dict(s,time=.03,pose={}))
    assert pose=={} and not tracker.tracks


def test_continuous_flow_expires_without_detector_reanchor():
    image,s=example();tracker=ShoeMotion();tracker.observe(image,s)
    for t in (.03,.06,.09,.12):
        pose,meta=tracker.observe(image,dict(s,time=t,pose={}))
        assert meta['bridged']==['left']
    pose,meta=tracker.observe(image,dict(s,time=.16,pose={}))
    assert pose=={} and not meta['bridged']

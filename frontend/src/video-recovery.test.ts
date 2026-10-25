import { expect, test, vi } from 'vitest';
import { VideoRecovery } from './video-recovery';
function fixture() {
  const v = Object.assign(new EventTarget(), {
    currentTime: 4.75, duration: 14, playbackRate: .5, paused: true, ended: false,
    getAttribute: () => '/video', load: vi.fn(), play: vi.fn().mockResolvedValue(undefined),
  });
  return { v, recovery: new VideoRecovery(v as unknown as HTMLVideoElement) };
}
test('returning from background reloads once and restores paused frame and speed', () => {
  const {v,recovery}=fixture();
  recovery.visibility(false); expect(v.load).not.toHaveBeenCalled();
  recovery.visibility(true); recovery.visibility(false); recovery.refresh();
  expect(v.load).toHaveBeenCalledTimes(1);
  v.currentTime=0; v.playbackRate=1;
  v.dispatchEvent(new Event('loadedmetadata'));
  expect(v.currentTime).toBe(4.75); expect(v.playbackRate).toBe(.5);
  expect(v.play).not.toHaveBeenCalled();
});
test('recovery resumes an already playing clip', () => {
  const {v,recovery}=fixture(); v.paused=false; recovery.refresh();
  v.dispatchEvent(new Event('loadedmetadata')); expect(v.play).toHaveBeenCalledOnce();
});
test('loading another result cancels stale restoration', () => {
  const {v,recovery}=fixture(); recovery.refresh(); recovery.cancel();
  v.currentTime=0; v.dispatchEvent(new Event('loadedmetadata'));
  expect(v.currentTime).toBe(0);
});

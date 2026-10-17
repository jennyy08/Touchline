import { describe, expect, it } from "vitest";
import { framePacket, FrameFlight } from "./live-protocol";

describe("live frame transport", () => {
  it("encodes seconds in little endian before exact JPEG bytes", () => {
    const bytes = new Uint8Array([255,216,255,217]);
    const packet = framePacket(1.25, bytes.buffer);
    expect(new DataView(packet).getFloat64(0,true)).toBe(1.25);
    expect([...new Uint8Array(packet,8)]).toEqual([...bytes]);
  });
  it("rejects invalid timestamps", () => {
    for (const n of [NaN,Infinity,-1]) expect(() => framePacket(n,new ArrayBuffer(0))).toThrow();
  });
  it("does not queue frames until the previous reply completes", () => {
    const flight=new FrameFlight();
    expect(flight.begin()).toBe(true);
    expect(flight.begin()).toBe(false);
    flight.complete();
    expect(flight.begin()).toBe(true);
  });
});

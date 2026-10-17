export function framePacket(seconds: number, jpeg: ArrayBuffer): ArrayBuffer {
  if (!Number.isFinite(seconds) || seconds < 0) throw new Error("Invalid capture time");
  const packet = new ArrayBuffer(8 + jpeg.byteLength);
  new DataView(packet).setFloat64(0, seconds, true);
  new Uint8Array(packet, 8).set(new Uint8Array(jpeg));
  return packet;
}

// The camera loop cannot enqueue a second frame while the server is processing.
export class FrameFlight {
  busy = false;
  begin(): boolean {
    if (this.busy) return false;
    this.busy = true;
    return true;
  }
  complete() { this.busy = false; }
}

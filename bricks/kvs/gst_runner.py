# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Avnet
"""Runs the KVS upload pipeline for the kvs brick.

Why not plain gst-launch: the UNO Q's Venus encoder writes a single IDR frame at the start of the stream and only
non-IDR I-frames afterwards, whatever the GOP controls say. Kinesis cuts a fragment at every key frame, so every
fragment but the first started with a picture players cannot decode after a reset (black/frozen video, a
discontinuity marker per fragment). The encoder does honour GStreamer's force-key-unit event, so this helper builds
the pipeline and sends that event every KEYFRAME_SEC seconds: a real IDR with SPS/PPS opens every fragment.

Usage: gst_runner.py "<gst-launch pipeline description with the encoder named enc>" <keyframe-seconds>
Frames arrive on stdin (fdsrc fd=0 in the description); closing stdin ends the stream cleanly (EOS -> kvssink
flushes). Exit code 0 on EOS, 1 on a pipeline error, 2 on bad arguments.
"""

import signal
import sys

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import GLib, Gst
except Exception as exc:  # noqa: BLE001
    print(f"ERROR: PyGObject/GStreamer bindings are not available: {exc}", flush=True)
    sys.exit(2)


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: gst_runner.py <pipeline-description> <keyframe-seconds>", flush=True)
        return 2
    description, keyframe_s = sys.argv[1], max(0.5, float(sys.argv[2]))
    Gst.init(None)
    pipeline = Gst.parse_launch(description)
    encoder = pipeline.get_by_name("enc")
    if encoder is None:
        print("WARNING: no element named 'enc' in the pipeline; key frames are not forced", flush=True)
    loop = GLib.MainLoop()
    state = {"count": 0, "rc": 0, "eos_sent": False}

    def force_key_unit() -> bool:
        if encoder is None:
            return False
        state["count"] += 1
        # all-headers=false: the SPS/PPS live in the stream's codec private data (the HLS init segment); repeating
        # them in-band at every IDR makes the Kinesis producer treat each fragment as a format change.
        structure = Gst.Structure.new_from_string(
            f"GstForceKeyUnit, all-headers=(boolean)false, count=(uint){state['count']}"
        )
        event = Gst.Event.new_custom(Gst.EventType.CUSTOM_UPSTREAM, structure)
        pad = encoder.get_static_pad("src")
        if pad is not None and not pad.send_event(event):
            print("WARNING: force-key-unit event was not accepted", flush=True)
        return True

    def on_message(_bus: Gst.Bus, msg: Gst.Message) -> None:
        if msg.type == Gst.MessageType.EOS:
            loop.quit()
        elif msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            print(f"ERROR: {err.message} ({(debug or '').splitlines()[0][:200] if debug else ''})", flush=True)
            state["rc"] = 1
            loop.quit()
        elif msg.type == Gst.MessageType.WARNING:
            warn, _debug = msg.parse_warning()
            print(f"WARNING: {warn.message}", flush=True)

    def stop(*_args: object) -> None:
        # EOS lets kvssink persist the last fragment before the process ends
        if not state["eos_sent"]:
            state["eos_sent"] = True
            pipeline.send_event(Gst.Event.new_eos())
            GLib.timeout_add(8000, loop.quit)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_message)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        print("ERROR: pipeline could not start", flush=True)
        return 1
    GLib.timeout_add(int(keyframe_s * 1000), force_key_unit)
    try:
        loop.run()
    finally:
        pipeline.set_state(Gst.State.NULL)
    return state["rc"]


if __name__ == "__main__":
    sys.exit(main())

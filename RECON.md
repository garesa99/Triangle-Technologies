# RECON — Phase 0 Sensor I/O (run this ON THE PI before trusting any layer)

**Status of this document:** the software implements every sensor path to the hardware spec and
self-probes at runtime. The *live* recon below must be executed on the actual Raspberry Pi with
the sensors attached — it could not be run on the build machine (no Pi/SDR/mic/ESP32/u-blox
present). Each step tells you the exact command and what "PASS" looks like. Capture one real
sample per available sensor into `tests/samples/` and record the result table at the bottom.

Gate: **do not rely on a detection layer that has not passed its recon step here.**

---

## 0. Which sensors does this node see?
```bash
cd node-agent && . .venv/bin/activate
python - <<'PY'
from sensors import build_driver, NodeContext
ctx = NodeContext("recon", {"lat":0,"lon":0})
for st in ["acoustic","remote_id","rf24","rf58","gnss","pir","seismic","magnetometer"]:
    d = build_driver(st, ctx, {"band":st} if st.startswith("rf") else {})
    print(f"{st:12s} present={d.probe()}  {d.manifest().spec}")
PY
```
PASS = the sensors you physically installed report `present=True`.

## 1. Acoustic (ALSA / PyAudio)
```bash
arecord -l                                  # confirm the mic is enumerated
arecord -D plughw:1,0 -f S16_LE -r 48000 -c 1 -d 5 tests/samples/acoustic_ambient.wav
python - <<'PY'
import wave, numpy as np, sys
sys.path.insert(0,"node-agent")
from sensors.acoustic import acoustic_features, score_drone
w=wave.open("tests/samples/acoustic_ambient.wav"); sr=w.getframerate()
x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(float)/32768
print("sr",sr,"features",acoustic_features(x,sr))
print("score",score_drone(acoustic_features(x,sr)))
PY
```
PASS = a WAV is written, sample_rate confirmed, a feature frame prints. Ambient should score LOW.
If you have a real drone, capture `tests/samples/acoustic_drone.wav` while it hovers ~20 m away
and confirm it scores HIGH. Otherwise the heuristic is the default and the optional model trains
on an open dataset (see `node-agent/ml/`).

## 2. RF (SoapySDR — BAND CHECK IS THE POINT)
```bash
SoapySDRUtil --find                          # is an SDR present?
SoapySDRUtil --probe | grep -i "freq range"  # can it reach 2.4/5.8 GHz?
```
PASS = an SDR is found AND its frequency range covers 2.4 GHz (and/or 5.8 GHz). A plain RTL-SDR
tops out ~1.7 GHz → rf24/rf58 STAY DISABLED (this is correct, not a bug). HackRF or RTL-SDR +
upconverter → the driver's `probe()` returns True and the layer enables. Capture a power spectrum:
```bash
python - <<'PY'
import numpy as np, sys; sys.path.insert(0,"node-agent")
from sensors.rf import RFSensor
from sensors import NodeContext
s=RFSensor(NodeContext("recon",{"lat":0,"lon":0}),{"band":"rf24"})
print("band-capable:", s.probe())
PY
```

## 3. Remote ID (ESP32 OpenDroneID over serial)
```bash
ls /dev/ttyUSB* /dev/ttyACM*                 # find the ESP32
python - <<'PY'
import sys; sys.path.insert(0,"node-agent")
from sensors.remote_id import parse_line
# paste one real line the ESP32 emitted, or a firmware self-test line:
print(parse_line('{"uas_id":"1596F...","lat":52.37,"lon":4.90,"alt":80,"rssi":-63}'))
PY
```
PASS = a real (or firmware self-test) F3411 message parses into a normalized payload with a
serial and/or position. Save one raw line to `tests/samples/remoteid_raw.jsonl`.

## 4. GNSS (u-blox via pyubx2 — position, PPS, jam/spoof)
```bash
ls /dev/ttyACM*                              # u-blox port
python - <<'PY'
import sys; sys.path.insert(0,"node-agent")
from sensors.gnss import GnssMonitor
from sensors import NodeContext
g=GnssMonitor(NodeContext("recon",{"lat":0,"lon":0}),{"port":"/dev/ttyACM0","baud":38400})
print("present:", g.probe()); print("health:", g.read_health())
PY
```
PASS = a 3D fix appears (`fix>=3`), `time_source` flips to `gnss_pps`, and jam/spoof fields read.
**This is the gate for PRECISE (TDOA) fixes** — without PPS lock the brain refuses precise and
downgrades to COARSE (by design). Confirm PPS is wired to a kernel PPS device if you want true
sub-ms timestamping; otherwise the node honestly reports `ntp`/`system`.

## 5. Mesh (multicast vs broadcast on THIS network)
```bash
# On two nodes on the same LAN, start the agent and watch neighbor discovery:
python agent.py -c config.yaml    # look for beacon-based neighbor entries in /nodes health
```
PASS = each node lists the other as a neighbor within ~20 s. Some WiFi APs block multicast; the
UDP-broadcast beacon fallback in `mesh.py` covers that. If even broadcast is blocked (client
isolation / guest VLAN), put the nodes+brain on a wired switch or a dedicated AP.

---

## Recon result table (fill in per node)
| node | acoustic | rf24 | rf58 | remote_id | gnss PPS | mesh peers | notes |
|------|----------|------|------|-----------|----------|-----------|-------|
| node-alpha | | | | | | | |
| node-bravo | | | | | | | |
| node-charlie | | | | | | | |

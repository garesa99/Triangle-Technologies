# Triangle node-agent

Runs on each Raspberry Pi. Plugin sensor drivers → on-node detection → buffered, idempotent
delivery to the brain (direct or via a neighbor relay). Runs with **any subset** of sensors and
reports what is missing — it never fabricates a detection.

## Design
- **Plugin sensors** (`sensors/`): each driver implements `manifest() / probe() / detect()`
  (`sensors/base.py`). Adding a sensor = one new file + a registry entry in `sensors/__init__.py`
  + a config block. The agent core and the brain do not change.
- **Honest hardware probing**: `probe()` decides if a sensor is actually present. RF is
  **band-gated** — it enables 2.4/5.8 GHz only if the SDR can truly reach the band.
- **Time source**: the GNSS monitor sets `system → ntp → gnss_pps`. Only PPS-disciplined
  timestamps let the brain grant a PRECISE (TDOA) fix.
- **Mesh**: UDP-broadcast discovery + beacons (mDNS when available), cross-cue hints, and an
  HTTP `/relay` server for store-and-forward. See `mesh.py`.
- **Buffer** (`buffer.py`): every detection is persisted first; delivery is idempotent by
  `detection_id`, so retries and relays are harmless and a link drop loses nothing.

## Sensors shipped
| type | driver | detects | bearing | notes |
|---|---|---|---|---|
| `acoustic` | `acoustic.py` | multirotor propeller comb | with 2+ mics (TDOA) | DSP heuristic default, optional ML |
| `remote_id` | `remote_id.py` | ASTM F3411 broadcast (cooperative) | no | ESP32 OpenDroneID over serial |
| `rf24`/`rf58` | `rf.py` | 2.4/5.8 GHz link energy | no | **band-gated** by SDR capability |
| `gnss` | `gnss.py` | node position, PPS time, jam/spoof | — | health source, not a detector |
| `pir`/`seismic`/`magnetometer` | `stubs.py` | ground targets | no | stubs proving the plugin path |

## Run (dev, on a laptop)
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # core; add hardware deps per this node
cp config.example.yaml config.yaml        # edit node_id, position, brain_url, token
python agent.py -c config.yaml
```
Sensors whose hardware is absent are skipped (you'll see `probe=absent`). With none present,
the node still registers and reports silence + health.

## Install on a Pi
```bash
sudo ./install.sh          # sets up /opt/triangle, venv, systemd unit, /etc/triangle/config.yaml
sudo systemctl enable --now triangle-node
```

## Config
See `config.example.yaml`. Env overrides: `TRIANGLE_NODE_ID`, `TRIANGLE_BRAIN_URL`, `TRIANGLE_TOKEN`, `TRIANGLE_CONFIG`.

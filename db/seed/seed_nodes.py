"""Seed the brain's node registry + geofences from a JSON file.

This registers node IDENTITY (fixed position + declared loadout) and protected zones. It does
NOT create any detection — the live picture only ever fills from real node detections.

Usage:
  python seed_nodes.py --brain http://localhost:8000 --token triangle-dev-token --file nodes.example.json
"""
from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain", default="http://localhost:8000")
    ap.add_argument("--token", default="triangle-dev-token")
    ap.add_argument("--file", default="nodes.example.json")
    args = ap.parse_args()

    data = json.load(open(args.file))
    h = {"Authorization": f"Bearer {args.token}"}
    ok = 0
    for n in data.get("nodes", []):
        r = httpx.post(f"{args.brain}/register", json=n, headers=h, timeout=5)
        print(f"register {n['node_id']}: {r.status_code} {r.text[:80]}")
        ok += r.status_code == 200
    for g in data.get("geofences", []):
        r = httpx.post(f"{args.brain}/geofences", json=g, headers=h, timeout=5)
        print(f"geofence {g.get('name')}: {r.status_code}")
    print(f"\nregistered {ok}/{len(data.get('nodes', []))} nodes")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

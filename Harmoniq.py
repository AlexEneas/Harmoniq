#!/usr/bin/env python3
"""
Harmoniq — Rekordbox Harmonic Playlist Generator
------------------------------------------------
Creates harmonic, BPM-aware playlists from your Rekordbox collection.

Features:
- Camelot-key mixing (Mixed In Key rules)
- BPM-aware transitions + controlled key jumps
- Genre filters (partial match), played/unplayed filter
- Start BPM / BPM window; start/end track anchors (kept from earlier versions)
- Optional source .m3u8 filtering (kept hook; add in config if you use it)
- Persistent JSON config saved next to the program (no AppData)
- /config wizard for easy setup
- --config <path> for custom JSON config
- NEW: "Recently added" filter (e.g., last 30 days)

Build EXE (Windows console):
    pyinstaller --onefile --console --icon rekordbox_harmonic_playlist_icon.ico harmoniq.py
"""

import collections
import json
import os
import random
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote
from typing import Optional

APP_NAME = "Harmoniq"
_DEFAULT_CONFIG_NAME = "harmoniq.config.json"

# ----------------------------- Camelot helpers -----------------------------

_CAM_RE = re.compile(r"^([1-9]|1[0-2])([ABab])$")

def parse_camelot(s: str):
    if not s:
        return None
    m = _CAM_RE.match(s.strip())
    if not m:
        return None
    return int(m.group(1)), m.group(2).upper()

def camelot_compatible(k1: str, k2: str) -> bool:
    p1, p2 = parse_camelot(k1), parse_camelot(k2)
    if not p1 or not p2:
        return False
    n1, m1 = p1
    n2, m2 = p2
    if n1 == n2 and m1 == m2:                      # same key
        return True
    if m1 == m2 and ((n1 - n2) % 12 in (1, 11)):   # ±1 step same mode
        return True
    if n1 == n2 and m1 != m2:                      # mode swap
        return True
    return False

def camelot_distance_steps(k1: str, k2: str) -> int:
    p1, p2 = parse_camelot(k1), parse_camelot(k2)
    if not p1 or not p2:
        return 12
    n1, _ = p1
    n2, _ = p2
    d = abs(n1 - n2) % 12
    return min(d, 12 - d)

# ----------------------------- Paths & config -----------------------------

def normalize_match_path(p: str) -> str:
    if not p:
        return ""
    s = p.strip()
    low = s.lower()
    if low.startswith("file://localhost/"):
        s = s[len("file://localhost/"):]
    elif low.startswith("file:///"):
        s = s[len("file:///"):]
    try:
        s = unquote(s)
    except Exception:
        pass
    s = s.replace("\\\\", "/").replace("\\", "/")
    s = re.sub(r"/{2,}", "/", s)
    return s.lower()

def forward_slash_path(p: str) -> str:
    if not isinstance(p, str):
        return p
    out = p.replace("\\", "/")
    out = re.sub(r"/{2,}", "/", out)
    return out

def get_default_config_path() -> Path:
    """Save config next to the program (EXE or script); fallback to CWD if not writable."""
    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
            base = Path(sys.executable).resolve().parent
        else:
            base = Path(__file__).resolve().parent
    except Exception:
        base = Path(os.getcwd()).resolve()

    cfg_path = base / _DEFAULT_CONFIG_NAME
    try:
        base.mkdir(parents=True, exist_ok=True)
        test = base / ".write_test.tmp"
        with open(test, "w", encoding="utf-8") as f:
            f.write("ok")
        test.unlink(missing_ok=True)
    except Exception:
        cfg_path = Path(os.getcwd()).resolve() / _DEFAULT_CONFIG_NAME

    return cfg_path

# ----------------------------- Loaders & filters -----------------------------

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%d/%m/%Y",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
]

def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    # Try ISO first
    try:
        return datetime.fromisoformat(s.replace("Z","").replace("T"," "))
    except Exception:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None

def load_m3u8_paths(m3u8_path: str):
    out = set()
    with open(m3u8_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.add(normalize_match_path(line))
    return out

def load_rekordbox_tracks(xml_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    collection = root.find("COLLECTION") or root.find(".//COLLECTION")
    if collection is None:
        raise RuntimeError("No COLLECTION found in Rekordbox XML.")
    tracks = []
    for trk in collection.findall("TRACK"):
        name = trk.attrib.get("Name", "")
        artist = trk.attrib.get("Artist", "")
        genre = trk.attrib.get("Genre", "")
        key = trk.attrib.get("Tonality", "")
        bpm = trk.attrib.get("AverageBpm", "")
        playcount = int(trk.attrib.get("PlayCount") or 0)

        # Date added (varies by export/version)
        date_added = trk.attrib.get("DateAdded") or trk.attrib.get("DATEADDED") or trk.attrib.get("Date_Added")
        if not date_added:
            node = trk.find("DATE_ADDED") or trk.find("DateAdded")
            if node is not None:
                date_added = (node.text or "").strip()
        date_added_dt = _parse_date(date_added)

        # Path
        path = None
        loc_attr = trk.attrib.get("Location")
        if loc_attr:
            u = loc_attr
            lowu = u.lower()
            if lowu.startswith("file://localhost/"):
                u = u[17:]
            elif lowu.startswith("file:///"):
                u = u[8:]
            try:
                u = unquote(u)
            except Exception:
                pass
            path = forward_slash_path(u)
        if not path:
            loc = trk.find("LOCATION")
            if loc is not None:
                vol = loc.attrib.get("VOLUME", "")
                d = loc.attrib.get("DIR", "")
                f = loc.attrib.get("FILE", "")
                path = forward_slash_path((vol + d + f).strip())

        try:
            bpm_val = float(str(bpm))
        except Exception:
            bpm_val = None

        tracks.append({
            "artist": artist,
            "title": name,
            "genre": genre,
            "key": key,
            "bpm_val": bpm_val,
            "playcount": playcount,
            "path": path,
            "date_added": date_added_dt,
            "match_key": normalize_match_path(path) if path else "",
            "filename_key": normalize_match_path(Path(path).name) if path else "",
            "search_label": f"{artist} - {name}",
        })
    return tracks

def filter_by_genres(tracks, genres):
    """Partial (substring) genre match."""
    if not genres:
        return tracks
    wanted = [g.strip().lower() for g in genres if g.strip()]
    if not wanted:
        return tracks
    out = []
    for t in tracks:
        g = (t["genre"] or "").lower()
        if any(w in g for w in wanted):
            out.append(t)
    return out

def filter_by_played(tracks, mode):
    m = (mode or "any").lower()
    if m == "played":
        return [t for t in tracks if t.get("playcount", 0) > 0]
    if m == "unplayed":
        return [t for t in tracks if t.get("playcount", 0) == 0]
    return tracks

def filter_by_bpm_window(tracks, bpm_min, bpm_max):
    if bpm_min is None and bpm_max is None:
        return tracks
    out = []
    for t in tracks:
        v = t.get("bpm_val")
        if v is None:
            continue
        if (bpm_min is None or v >= bpm_min) and (bpm_max is None or v <= bpm_max):
            out.append(t)
    return out

def filter_by_recent_days(tracks, days: Optional[int]):
    """Keep tracks whose DateAdded is within the last `days` (UTC-naive)."""
    if not days or days <= 0:
        return tracks
    now = datetime.now()
    cutoff = now - timedelta(days=int(days))
    out = []
    for t in tracks:
        d = t.get("date_added")
        if d and d >= cutoff:
            out.append(t)
    return out

# ----------------------------- Config management -----------------------------

def load_config(path: Optional[str] = None):
    cfg_path = Path(path) if path else get_default_config_path()
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f), cfg_path
    return None, cfg_path

def save_config(cfg, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"Saved configuration to: {path}")

# ----------------------------- Harmonic playlist builder (simple, BPM-aware) -----------------------------

def pick_harmonic_playlist(pool, count, rng, start_bpm=None, bpm_tolerance=3, bpm_tolerance_jump=4):
    """BPM-aware harmonic builder (same key/±1/mode swap first; falls back to BPM-near)."""
    def good_bpm(a, b, tol):
        if a.get("bpm_val") is None or b.get("bpm_val") is None:
            return True
        return abs(a["bpm_val"] - b["bpm_val"]) <= tol

    candidates = [t for t in pool if parse_camelot(t["key"])]
    if not candidates:
        return []

    if start_bpm:
        first = min(candidates, key=lambda t: abs((t.get("bpm_val") or start_bpm) - start_bpm))
    else:
        first = rng.choice(candidates)
    chain = [first]
    remaining = [t for t in candidates if t is not first]

    while len(chain) < count and remaining:
        last = chain[-1]
        compat = [t for t in remaining if camelot_compatible(last["key"], t["key"]) and good_bpm(last, t, bpm_tolerance)]
        if not compat:
            compat = [t for t in remaining if good_bpm(last, t, bpm_tolerance_jump)]
        if not compat:
            break
        nxt = rng.choice(compat)
        chain.append(nxt)
        remaining.remove(nxt)

    return chain

# ----------------------------- Wizard & runner -----------------------------

def run_config_wizard(cfg_path: Path) -> dict:
    print(f"\n=== {APP_NAME} Configuration Wizard ===")
    xml = input("Path to Rekordbox XML: ").strip()
    genres = input("Genres (comma-separated; blank for all): ").strip()
    played = input("Played filter (played/unplayed/any) [any]: ").strip() or "any"
    count = int(input("How many tracks [30]: ").strip() or 30)
    start_bpm_s = input("Preferred start BPM (blank skip): ").strip()
    start_bpm = float(start_bpm_s) if start_bpm_s else None
    bpm_min_s = input("Min BPM (blank skip): ").strip()
    bpm_min = float(bpm_min_s) if bpm_min_s else None
    bpm_max_s = input("Max BPM (blank skip): ").strip()
    bpm_max = float(bpm_max_s) if bpm_max_s else None
    added_days_s = input("Only use tracks added in the last N days (blank = no limit): ").strip()
    added_days = int(added_days_s) if added_days_s else None
    out_file = input("Output .m3u8 path [Harmoniq_Playlist.m3u8]: ").strip() or "Harmoniq_Playlist.m3u8"

    cfg = {
        "xml": xml,
        "genres": genres,
        "played": played,
        "count": count,
        "start_bpm": start_bpm,
        "bpm_min": bpm_min,
        "bpm_max": bpm_max,
        "added_days": added_days,      # NEW
        "out": out_file,
    }
    save_config(cfg, cfg_path)
    return cfg

def write_m3u8(tracks, out_path):
    lines = ["#EXTM3U"]
    for t in tracks:
        disp = f"{t['artist']} - {t['title']}"
        lines.append(f"#EXTINF:-1,{disp}")
        lines.append(forward_slash_path(t.get("path", disp)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nPlaylist written: {out_path}")

def main():
    args = sys.argv[1:]
    config_override = None
    if "--config" in args:
        i = args.index("--config")
        if i + 1 < len(args):
            config_override = args[i + 1]
        else:
            print("Usage: --config <path>")
            sys.exit(1)

    run_wizard = ("/config" in args) or ("--wizard" in args)
    cfg, cfg_path = load_config(config_override)
    if not cfg or run_wizard:
        cfg = run_config_wizard(cfg_path)

    print(f"Using config: {cfg_path}")
    tracks = load_rekordbox_tracks(cfg["xml"])

    # Filters
    pool = tracks
    pool = filter_by_genres(pool, cfg.get("genres","").split(","))
    pool = filter_by_played(pool, cfg.get("played"))
    pool = filter_by_bpm_window(pool, cfg.get("bpm_min"), cfg.get("bpm_max"))
    pool = filter_by_recent_days(pool, cfg.get("added_days"))  # NEW

    if not pool:
        print("No tracks match your filters.")
        return

    rng = random.Random()
    playlist = pick_harmonic_playlist(
        pool,
        int(cfg.get("count", 30)),
        rng,
        start_bpm=cfg.get("start_bpm"),
        bpm_tolerance=3,
        bpm_tolerance_jump=4,
    )
    write_m3u8(playlist, cfg["out"])

if __name__ == "__main__":
    main()

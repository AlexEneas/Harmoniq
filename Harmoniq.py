#!/usr/bin/env python3
"""
Harmoniq — Rekordbox Harmonic Playlist Generator
------------------------------------------------
Creates harmonic, BPM-aware playlists from your Rekordbox XML collection.

Changes in this build:
- Config file now stores ONLY the Rekordbox XML path.
- Every run asks for selection parameters (genres, counts, BPMs, etc.).
- If XML path is missing/invalid, prompts for it and saves it.
- Prints a detailed track list of the final selection.

Build EXE (Windows console):
    pyinstaller --onefile --console --icon rekordbox_harmonic_playlist_icon.ico harmoniq.py
"""

import json
import os
import random
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

APP_NAME = "Harmoniq"
_DEFAULT_CONFIG_NAME = "harmoniq.config.json"

# ----------------------------- Utility: path sanitizing -----------------------------

def sanitize_path(p: Optional[str]) -> str:
    """Trim whitespace and surrounding quotes; expand ~ and env vars."""
    if p is None:
        return ""
    s = str(p).strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    s = os.path.expanduser(os.path.expandvars(s))
    return s

# ----------------------------- Camelot helpers -----------------------------

_CAM_RE = re.compile(r"^([1-9]|1[0-2])([ABab])$")

def parse_camelot(s: str):
    if not s:
        return None
    m = _CAM_RE.match(s.strip())
    if not m:
        return None
    return int(m.group(1)), m.group(2).upper()

# Musical key → Camelot mapping
_MINOR_TO_A = {
    "abm": "1A", "g#m": "1A",
    "ebm": "2A", "d#m": "2A",
    "bbm": "3A", "a#m": "3A",
    "fm":  "4A",
    "cm":  "5A",
    "gm":  "6A",
    "dm":  "7A",
    "am":  "8A",
    "em":  "9A",
    "bm":  "10A",
    "f#m": "11A", "gbm": "11A",
    "c#m": "12A", "dbm": "12A",
}
_MAJOR_TO_B = {
    "b":  "1B",
    "gb": "2B", "f#": "2B",
    "db": "3B", "c#": "3B",
    "ab": "4B", "g#": "4B",
    "eb": "5B", "d#": "5B",
    "bb": "6B", "a#": "6B",
    "f":  "7B",
    "c":  "8B",
    "g":  "9B",
    "d":  "10B",
    "a":  "11B",
    "e":  "12B",
}

def _normalize_note(s: str) -> str:
    """Lowercase, standardize unicode sharps/flats, collapse spaces."""
    s = (s or "").strip().lower()
    s = s.replace("♭", "b").replace("♯", "#")
    s = re.sub(r"\s+", "", s)
    return s

def to_camelot_if_musical_key(key: str) -> Optional[str]:
    """
    Convert musical keys like 'G#m', 'A minor', 'C# MAJ', 'Gb', 'Bb Major' to Camelot.
    Returns Camelot string (e.g., '1A', '8B') or None if not understood.
    """
    if not key:
        return None
    s = _normalize_note(key)

    # already Camelot?
    if parse_camelot(s):
        return s.upper()

    s = s.replace("minor", "m").replace("min", "m")
    s = s.replace("major", "").replace("maj", "")
    s = s.replace("key", "")
    s = s.replace("-", "")

    if s.endswith("m"):  # minor
        return _MINOR_TO_A.get(s)
    return _MAJOR_TO_B.get(s)  # major default

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

# ----------------------------- Paths -----------------------------

def normalize_match_path(p: str) -> str:
    """Normalize file:// URLs or paths to lowercase forward-slash for matching."""
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
    try:
        return datetime.fromisoformat(s.replace("Z", "").replace("T", " "))
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

    collection = root.find("COLLECTION")
    if collection is None:
        collection = root.find(".//COLLECTION")
    if collection is None:
        raise RuntimeError("No <COLLECTION> element found in Rekordbox XML.")

    tracks = []
    for trk in collection.findall("TRACK"):
        name = trk.attrib.get("Name", "")
        artist = trk.attrib.get("Artist", "")
        genre = trk.attrib.get("Genre", "")
        key_raw = trk.attrib.get("Tonality", "")

        # convert musical keys to Camelot if needed
        key_camelot = to_camelot_if_musical_key(key_raw) if key_raw else None
        key = key_camelot or key_raw

        bpm = trk.attrib.get("AverageBpm", "")
        playcount = int(trk.attrib.get("PlayCount") or 0)

        # Date added (varies by export/version)
        date_added = (
            trk.attrib.get("DateAdded")
            or trk.attrib.get("DATEADDED")
            or trk.attrib.get("Date_Added")
        )
        if not date_added:
            node = trk.find("DATE_ADDED") or trk.find("DateAdded")
            if node is not None:
                date_added = (node.text or "").strip()
        date_added_dt = _parse_date(date_added)

        # Path (prefer TRACK@Location if present)
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
    """Keep tracks whose DateAdded is within the last `days`."""
    if not days or days <= 0:
        return tracks
    cutoff = datetime.now() - timedelta(days=int(days))
    return [t for t in tracks if t.get("date_added") and t["date_added"] >= cutoff]

# ----------------------------- Config management -----------------------------

def load_config(path: Optional[str] = None):
    """Return (cfg_dict, cfg_path). Only 'xml' is stored in config."""
    cfg_path = Path(path) if path else get_default_config_path()
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f), cfg_path
    return None, cfg_path

def save_config(cfg, path: Path):
    # cfg is expected to be {"xml": "..."}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    print(f"Saved configuration to: {path}")

# ----------------------------- Harmonic playlist builder -----------------------------

def pick_harmonic_playlist(pool, count, rng, start_bpm=None,
                           bpm_tolerance=3, bpm_tolerance_jump=4):
    """BPM-aware harmonic builder (same key / ±1 / mode-swap first; fallback to BPM-near)."""
    def good_bpm(a, b, tol):
        if a.get("bpm_val") is None or b.get("bpm_val") is None:
            return True
        return abs(a["bpm_val"] - b["bpm_val"]) <= tol

    # candidates need a Camelot key
    candidates = []
    for t in pool:
        k = t.get("key")
        if parse_camelot(k):
            candidates.append(t)
        else:
            conv = to_camelot_if_musical_key(k)
            if conv:
                t["key"] = conv
                candidates.append(t)

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
        compat = [t for t in remaining
                  if camelot_compatible(last["key"], t["key"]) and good_bpm(last, t, bpm_tolerance)]
        if not compat:
            compat = [t for t in remaining if good_bpm(last, t, bpm_tolerance_jump)]
        if not compat:
            break
        nxt = rng.choice(compat)
        chain.append(nxt)
        remaining.remove(nxt)

    return chain

# ----------------------------- Interactive prompts (run-time params) -----------------------------

def prompt_run_params() -> dict:
    """Ask user for per-run parameters (everything except XML path)."""
    print("\n=== Harmoniq Run Settings ===")
    genres = input("Genres (comma-separated; blank for all): ").strip()
    played = input("Played filter (played/unplayed/any) [any]: ").strip() or "any"
    try:
        count = int(input("How many tracks [30]: ").strip() or 30)
    except ValueError:
        count = 30
    start_bpm_s = input("Preferred start BPM (blank skip): ").strip()
    start_bpm = float(start_bpm_s) if start_bpm_s else None
    bpm_min_s = input("Min BPM (blank skip): ").strip()
    bpm_min = float(bpm_min_s) if bpm_min_s else None
    bpm_max_s = input("Max BPM (blank skip): ").strip()
    bpm_max = float(bpm_max_s) if bpm_max_s else None
    added_days_s = input("Only use tracks added in the last N days (blank = no limit): ").strip()
    added_days = int(added_days_s) if added_days_s else None
    out_file = sanitize_path(input("Output .m3u8 path [Harmoniq_Playlist.m3u8]: ").strip() or "Harmoniq_Playlist.m3u8")

    return {
        "genres": genres,
        "played": played,
        "count": count,
        "start_bpm": start_bpm,
        "bpm_min": bpm_min,
        "bpm_max": bpm_max,
        "added_days": added_days,
        "out": out_file,
    }

def prompt_or_update_xml(cfg: Optional[dict], cfg_path: Path) -> dict:
    """
    Ensure config holds a valid 'xml' path. Prompt if missing or invalid; save only 'xml'.
    Returns cfg dict with 'xml'.
    """
    current_xml = sanitize_path((cfg or {}).get("xml", ""))
    if not current_xml or not os.path.isfile(current_xml):
        print(f"\n=== {APP_NAME} XML Setup ===")
        if current_xml and not os.path.isfile(current_xml):
            print(f"Previous XML not found:\n  {current_xml}")
        while True:
            xml = sanitize_path(input("Path to Rekordbox XML: ").strip())
            if xml and os.path.isfile(xml):
                cfg = {"xml": xml}
                save_config(cfg, cfg_path)
                return cfg
            print("That path doesn't exist. Please try again.")
    return {"xml": current_xml}

# ----------------------------- Wizard & runner -----------------------------

def write_m3u8(tracks, out_path):
    out_path = sanitize_path(out_path)
    lines = ["#EXTM3U"]
    for t in tracks:
        disp = f"{t['artist']} - {t['title']}"
        lines.append(f"#EXTINF:-1,{disp}")
        lines.append(forward_slash_path(t.get("path", disp)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nPlaylist written: {out_path}")

def print_tracklist(tracks):
    print("\n=== Selected Tracks ===")
    if not tracks:
        print("(none)")
        return
    for i, t in enumerate(tracks, 1):
        key = t.get("key") or "-"
        bpm = t.get("bpm_val")
        bpms = f"{bpm:.1f}" if isinstance(bpm, (int, float)) else "-"
        path = t.get("path") or "-"
        print(f"{i:02d}. {t['artist']} - {t['title']} | {key} | {bpms} BPM")
        print(f"     {path}")

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

    # Load config (only holds 'xml')
    cfg, cfg_path = load_config(config_override)
    cfg = prompt_or_update_xml(cfg, cfg_path)  # ensure valid XML stored; save if needed

    print(f"Using config: {cfg_path}")
    xml_path = sanitize_path(cfg.get("xml", ""))
    if not xml_path or not os.path.isfile(xml_path):
        print("Error: Rekordbox XML not found after setup.")
        print(f"  Sanitized: {xml_path}")
        sys.exit(1)

    # Per-run parameters (always prompted)
    run = prompt_run_params()

    # Load tracks from XML
    tracks = load_rekordbox_tracks(xml_path)

    # Apply filters
    pool = tracks
    pool = filter_by_genres(pool, run.get("genres", "").split(","))
    pool = filter_by_played(pool, run.get("played"))
    pool = filter_by_bpm_window(pool, run.get("bpm_min"), run.get("bpm_max"))
    pool = filter_by_recent_days(pool, run.get("added_days"))

    if not pool:
        print("No tracks match your filters.")
        with_keys = sum(1 for t in tracks if t.get("key"))
        print(f"Library tracks loaded: {len(tracks)} | with 'key': {with_keys}")
        return

    rng = random.Random()
    playlist = pick_harmonic_playlist(
        pool,
        int(run.get("count", 30)),
        rng,
        start_bpm=run.get("start_bpm"),
        bpm_tolerance=3,
        bpm_tolerance_jump=4,
    )

    if not playlist:
        print("Could not assemble a harmonic playlist from the filtered pool.")
        # Diagnostics: show a few sample keys/BPMs to help debugging
        sample = pool[:10]
        print("Sample of filtered tracks (Artist - Title | Key | BPM):")
        for t in sample:
            bpm = t.get("bpm_val")
            print(f"  {t['artist']} - {t['title']} | {t.get('key')} | {bpm if bpm is not None else '-'}")
        return

    write_m3u8(playlist, run.get("out", "Harmoniq_Playlist.m3u8"))
    print_tracklist(playlist)

if __name__ == "__main__":
    main()

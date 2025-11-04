# 🎧 Harmoniq

Create harmonically-compatible, BPM-aware playlists directly from your **Rekordbox XML export**.  
Harmoniq helps DJs, radio hosts, and producers generate **mix-ready playlists** that flow naturally — both musically and rhythmically.

> ⚠️ Rekordbox XML export is required (not the database).  
> Go to **File → Export Collection in XML Format** in Rekordbox before using Harmoniq.

---

## Table of contents
- [What it does](#what-it-does)
- [Features](#features)
- [How it works](#how-it-works)
- [Prerequisites (Windows, macOS, Linux)](#prerequisites-windows-macos-linux)
- [Setup](#setup)
- [Usage](#usage)
- [Options](#options)
- [Example config](#example-config)
- [Playlist output format](#playlist-output-format)
- [Building a standalone EXE](#building-a-standalone-exe)
- [Troubleshooting](#troubleshooting)
- [FAQs](#faqs)
- [License](#license)

---

## What it does

Harmoniq reads your Rekordbox XML file and intelligently selects tracks to form a **harmonic and BPM-compatible** playlist.

It can:
- Filter by **genre**, **BPM range**, or **play count**.
- Include only **recently added** tracks (e.g., last 30 days).
- Start from a **specific BPM** or **track** and flow harmonically through your library.
- Output a **.m3u8 playlist** you can load straight into Rekordbox or media players.

---

## Features

### 🎶 Harmonic mixing (Camelot rules)
- Uses **Mixed In Key / Camelot Wheel** logic:
  - Same key (e.g. 8A → 8A)
  - Adjacent key within same mode (e.g. 8A → 7A / 9A)
  - Mode switch at same number (e.g. 8A ↔ 8B)
- Avoids harsh key clashes automatically.

### 🎚️ BPM-aware transitions
- Keeps tempo flow smooth between tracks.
- Optional BPM tolerance control.
- You can define a **starting BPM** or a **BPM range** (e.g. 130–138).

### 🧠 Intelligent selection
- Selects harmonically and rhythmically compatible tracks.
- Supports limited “intelligent jumps” when key compatibility runs out.
- Optionally bridges key jumps with intermediary tracks for smooth transitions.

### 🎛️ Full filtering options
| Filter | Description |
|---------|-------------|
| **Genre** | Partial matching (e.g., “Trance” matches “Uplifting Trance”). |
| **Played / Unplayed** | Based on Rekordbox play count. |
| **BPM Range** | Min / max BPM boundaries. |
| **Start BPM** | Start the playlist around a target BPM. |
| **Recently Added** | Select tracks added in the last *N* days — perfect for radio/podcast prep. |
| **Start/End Track** | Optionally define fixed start and end tracks. |

### 💾 Persistent config system
- Stores all settings in a single JSON config file:
harmoniq.config.json

markdown
Copy code
- Saved **next to the program** — not in hidden system folders.
- Reusable between sessions and editable manually.
- Supports multiple config files with `--config my_config.json`.

### 🧩 Command-line friendly
Simple syntax for power users:
```powershell
python harmoniq.py --config trance_show.json
Harmoniq.exe /config
How it works
Harmoniq parses your Rekordbox XML export.

It builds a list of all valid tracks (with BPM, key, genre, etc.).

Filters are applied:

genre

play count

BPM range

date added

The program then:

chooses a seed track near your start BPM (or random if none),

finds harmonic matches by Camelot compatibility,

builds a full playlist of compatible tracks.

A .m3u8 playlist is written — using forward slashes (D:/Music/...) so Rekordbox recognizes file paths correctly.

Prerequisites (Windows, macOS, Linux)
Install Python 3.9 or higher
Download from python.org

🟢 On Windows, tick “Add Python to PATH” during installation.

Check your installation

powershell
Copy code
python --version
(Optional) Install PyInstaller if you want to build a standalone .exe.

Setup
Export your Rekordbox library:

In Rekordbox:
File → Export Collection in XML Format

Save the file somewhere accessible (e.g. D:\Rekordbox Collection.xml).

Place harmoniq.py in a folder of your choice (e.g. C:\Harmoniq).

Run Harmoniq once to start the configuration wizard:

powershell
Copy code
python harmoniq.py
The wizard will ask for:

Rekordbox XML path

Genres to include

Played/unplayed filter

BPM range

“Tracks added in last N days”

Number of tracks

Output playlist path

A JSON config file (e.g. harmoniq.config.json) will be created automatically.

Usage
Basic usage
powershell
Copy code
python harmoniq.py
Uses the existing config file (or launches the wizard if none exists).

Reconfigure
powershell
Copy code
python harmoniq.py /config
or

powershell
Copy code
python harmoniq.py --wizard
Custom configuration file
powershell
Copy code
python harmoniq.py --config my_trance_show.json
Options
Option	Description
/config, --wizard	Run setup wizard to create/update config
--config <path>	Use custom JSON config file
(no args)	Run with saved config (auto mode)

All advanced settings — like jump tolerance, BPM tolerance, etc. — are stored inside the JSON file.

Example config
json
Copy code
{
  "xml": "D:/Rekordbox Collection.xml",
  "genres": "Trance, Progressive Trance",
  "played": "unplayed",
  "count": 25,
  "start_bpm": 136,
  "bpm_min": 130,
  "bpm_max": 138,
  "added_days": 30,
  "out": "D:/Playlists/Harmoniq_Recent_Trance.m3u8"
}
Playlist output format
Example .m3u8 playlist generated by Harmoniq:

m3u
Copy code
#EXTM3U
#EXTINF:-1,Above & Beyond - Sun In Your Eyes
D:/Trance/Above & Beyond - Sun In Your Eyes.flac
#EXTINF:-1,Andy Moor - Halcyon (Extended Mix)
D:/Trance/Andy Moor - Halcyon (Extended Mix).mp3
✅ Uses forward slashes (/) so Rekordbox recognizes paths correctly.
✅ Safe to re-import — Harmoniq never overwrites your XML file.

Building a standalone EXE
To make a portable Windows program:

powershell
Copy code
pip install pyinstaller
pyinstaller --onefile --console --icon rekordbox_harmonic_playlist_icon.ico harmoniq.py
After building, you’ll find:

Copy code
dist/Harmoniq.exe
Run the EXE
powershell
Copy code
Harmoniq.exe
or

powershell
Copy code
Harmoniq.exe /config
Troubleshooting
Problem	Solution
Rekordbox says the playlist has missing files	Check your XML’s Location fields use real paths (e.g. D:/Music/...). Harmoniq uses them directly.
No tracks found	Double-check your genre filter, play count filter, or “recent days” setting. Try leaving them blank.
Wrong BPM or key	Ensure Rekordbox has analyzed your tracks for key/BPM before exporting.
Python not recognized	Re-install Python and ensure “Add to PATH” is ticked.
Permission denied	If running from Program Files, move Harmoniq to a writable folder like C:\Harmoniq.

FAQs
Q: Do I need Rekordbox open to use Harmoniq?
No. Harmoniq only reads the exported XML file.

Q: Will it modify my Rekordbox library?
No — it only reads your XML and creates a new .m3u8 playlist file.

Q: Can I use multiple configs for different genres?
Yes. Just duplicate and rename your JSON config files (e.g. harmoniq_trance.json, harmoniq_house.json) and use --config.

Q: How many tracks can it generate?
Any number — though harmonic accuracy is best between 15–60 tracks.

License
text
Copy code
MIT License

Copyright (c) 2025 Alex Eneas

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction...
Quick start (TL;DR)
powershell
Copy code
# 1. Install Python
# 2. Export Rekordbox XML
# 3. Run wizard
python harmoniq.py

# 4. Generate playlist
python harmoniq.py

# 5. (Optional) Build EXE
pyinstaller --onefile --console --icon rekordbox_harmonic_playlist_icon.ico harmoniq.py
Author: Alex Eneas
Project: Harmoniq — Intelligent Harmonic Playlist Generator for Rekordbox DJs
Website: Nationvibe Worldwide

“Make every playlist flow as if it were mixed live.” 🎶

yaml
Copy code

---

Would you like me to save this README as a `.md` file for download (like I did before)?  
I can also add a **linked header image** (your Harmoniq banner) at the top with:

```markdown
![Harmoniq Banner](banner.png)

# 🎧 Harmoniq  
### Intelligent Harmonic Playlist Generator for Rekordbox DJs

**Harmoniq** automatically builds harmonic, BPM-aware playlists from your Rekordbox Collection.  
It uses Camelot key mixing and BPM awareness to ensure every transition sounds musically perfect — ideal for DJs, radio hosts, and podcasters.

---

## 🪩 Key Features

### 🎶 Harmonic Mixing (Camelot Rules)
- Follows **Mixed In Key / Camelot Wheel** logic:
  - Same key (e.g., 8A → 8A)
  - ±1 step within same mode (e.g., 8A → 7A or 9A)
  - Mode swap of same number (e.g., 8A ↔ 8B)
- Avoids jarring key jumps for a smooth, club-ready flow.

### 🎚️ BPM-Aware Transitions
- Keeps mixes tempo-consistent.
- Prevents large jumps between tracks.
- Optionally start near a target BPM (e.g., 136).

### 🧠 Intelligent Selection
- Chooses harmonically and rhythmically compatible tracks.
- Automatically adjusts selection if constraints are tight.

### 🎛️ Customizable Filters
| Filter | Description |
|---------|-------------|
| **Genre** | Partial match — “Trance” matches “Uplifting Trance”, “Vocal Trance”, etc. |
| **Played / Unplayed** | Filter by Rekordbox play count. |
| **BPM Range** | Define minimum and maximum BPMs. |
| **Start BPM** | Pick an initial BPM to anchor the playlist around. |
| **Recently Added** | ⚡ **NEW:** limit selection to tracks added in the last *N* days (e.g., 30). Perfect for podcast or radio mixes. |
| **Start/End Track (optional)** | Choose a specific starting or ending track (feature retained from earlier builds). |

### 💾 Configuration System
- First run starts a simple **interactive wizard** (`/config`).
- Settings are saved to a single JSON file next to the program:
  ```
  harmoniq.config.json
  ```
  > 💡 No AppData paths — everything stays in the program folder.
- Reuse settings instantly on future runs.
- Create multiple JSON configs for different mix styles.

### ⚙️ Config Management
| Option | Description |
|---------|-------------|
| `/config` or `--wizard` | Launch the setup wizard. |
| `--config <path>` | Use a custom JSON config file. |
| *(no args)* | Auto-loads saved config (or runs wizard if none found). |

---

## 📂 Example Config File
```json
{
  "xml": "D:/Rekordbox Collection.xml",
  "genres": "Trance, Classic Trance",
  "played": "any",
  "count": 30,
  "start_bpm": 136,
  "bpm_min": 130,
  "bpm_max": 140,
  "added_days": 30,
  "out": "D:/Playlists/Harmoniq_Recent_Trance.m3u8"
}
```

This will:
- Look at your Rekordbox XML.
- Filter for Trance/Classic Trance.
- Include both played and unplayed tracks.
- Select 30 tracks around 136 BPM.
- Only include tracks **added in the last 30 days**.
- Output a harmonically-ordered `.m3u8` file.

---

## 🧭 How to Use

### 1️⃣ Export your Rekordbox Library
In Rekordbox:
> **File → Export Collection in XML Format**  
Save it somewhere (e.g. `D:\Rekordbox Collection.xml`).

### 2️⃣ Run Harmoniq for the First Time
```bash
python harmoniq.py
```
If no config exists, the setup wizard starts automatically.

You’ll be asked for:
- Rekordbox XML path  
- Genres  
- Played filter  
- BPM range  
- Days to look back for new tracks  
- Output file name  
- Number of tracks  

### 3️⃣ Create or Re-run Configurations
```bash
python harmoniq.py /config
```
or  
```bash
python harmoniq.py --wizard
```

To load a custom config:
```bash
python harmoniq.py --config my_show_config.json
```

### 4️⃣ Output
Your playlist will appear as a `.m3u8` file:
```
#EXTM3U
#EXTINF:-1,Artist - Title
D:/Music/Trance/Example Track.mp3
```

This format imports cleanly back into Rekordbox with no duplicate entries.

---

## 💡 Ideal Use Cases
- 🎧 **Podcast or radio show prep:**  
  Generate a fresh “last 30 days” playlist of new tracks that harmonically flow.
- 💿 **Vinyl/Classic Trance sets:**  
  Build perfect Camelot-key progressions around your preferred BPM.
- 🎚️ **Automated show planning:**  
  Quickly test harmonic sets before recording or streaming.

---

## ⚙️ Requirements

- **Python 3.9+**
- Works on Windows, macOS, or Linux
- No external dependencies (only built-in Python libraries)

---

## 🧱 Building a Standalone EXE

To make a Windows version you can run directly:

```bash
pip install pyinstaller
pyinstaller --onefile --console --icon rekordbox_harmonic_playlist_icon.ico harmoniq.py
```

Your compiled app will appear in the `dist` folder as:
```
Harmoniq.exe
```

Run normally:
```bash
Harmoniq.exe
```

Or reconfigure anytime:
```bash
Harmoniq.exe /config
```

---

## ⚡ Command Summary

| Command / Flag | Description |
|----------------|-------------|
| `/config`, `--wizard` | Launch setup wizard |
| `--config <path>` | Use a custom JSON config file |
| *(no args)* | Auto-load existing configuration |
| *(in wizard)* | Set XML path, genres, BPM filters, “recent” days, etc. |

---

## 📄 Playlist Output Example
```m3u
#EXTM3U
#EXTINF:-1,Binary Finary - 1998 (Original Mix)
D:/Trance/Binary Finary - 1998 (Original Mix).mp3
#EXTINF:-1,Armin van Buuren - Shivers (Extended Mix)
D:/Trance/Armin van Buuren - Shivers (Extended Mix).mp3
```

---

## 🎨 Branding

**Name:** Harmoniq  
**Tagline:** *Intelligent Harmonic Playlist Generator for Rekordbox DJs*  
**Icon:** Blue vinyl record surrounded by the Camelot colour ring  
**Developer:** Alex Eneas  
**License:** MIT

---

## 💬 Support / Contributions

If you find a bug, want to contribute improvements, or have feature ideas:
- Submit an **Issue** or **Pull Request** on the GitHub repository.
- Or suggest features.

---

> “Harmoniq makes your Rekordbox library sound like you planned every mix —  
> even when you didn’t.” 🎶

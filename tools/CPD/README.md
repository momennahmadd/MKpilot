# CPD Detector & Viewer

This folder contains the CPD detector tool. `cpd_detector.py` scans non-video logs (rlog / qlog), detects transitions to/from the `Child` classification for several occupant signals, and writes detected events to a CSV.

Key points
- The detector looks for the occupant-status CAN message (ID 0x235 / decimal 565) and decodes 4-bit fields: FL, FR, RL, RC, RR, ALL, FOOT.
- It reports two event types: `ENTER_CHILD` (value becomes `2`) and `EXIT_CHILD` (value leaves `2`). Each event is written with timestamp, file, signal, from/to values and labels, and duration for EXIT events.

Decompression and parsing (Cabana-compatible)
- When available, `cpd_detector.py` reuses the project's Python `LogReader` (`openpilot.tools.lib.logreader.LogReader`) to read inputs. That reader supports:
	- local and remote paths (HTTP/HTTPS),
	- compressed archives: `.bz2` (bzip2) and `.zst` (zstd),
	- both `rlog` and `qlog` formats, and
	- Cap'n Proto parsing of `cereal::Event` messages (same as Cabana).
- If `LogReader` is not importable, the script falls back to the original raw-file reader (no automatic decompression/download).

Inputs supported
- A segment folder (the script will recursively search under the folder for files whose names include `rlog` or `qlog`, including `.bz2`/`.zst` archives). Example: a route folder with many segment subfolders.
- One or more archive files directly (e.g. `rlog.bz2`, `rlog.zst`, `qlog.bz2`).
- Remote URLs (e.g. `https://.../rlog.bz2`) — handled by `LogReader`.

Usage examples
- Process a local route/segment folder (finds archives recursively):
```
python3 tools/CPD/cpd_detector.py /path/to/route_folder
```
- Process specific archives or URLs:
```
python3 tools/CPD/cpd_detector.py /path/to/seg1/rlog.bz2 /path/to/seg2/rlog.zst
python3 tools/CPD/cpd_detector.py https://.../rlog.bz2
```

Output
- By default the script writes `<route_name>.csv` into the current working directory, where `route_name` comes from the input folder name.
- The CSV now includes both `timestamp` as relative `HH:MM:SS` and `seconds_elapsed` as the numeric offset for Cabana seeking.
- The CSV also includes a zero-based `segment_index` column.

Clickable Cabana viewer
- You can turn the CSV into a clickable event list by running:
```
python3 tools/CPD/cpd_viewer.py <route_name>.csv --cabana-arg --dcam --cabana-arg --qcam
```
- This starts a small local web page where each row has an `Open in Cabana` link.
- When a row is clicked the viewer launches Cabana pointing at the route's data directory and seeks to the event time (`seconds_elapsed`). The viewer constructs and runs a command similar to:
```
./tools/cabana/cabana --data_dir /home/<you>/Recs/<route> "<route>" --seek <seconds_elapsed> [--dcam --qcam ...] [--dbc /path/to.dbc]
```
- Provide camera or other Cabana flags to the viewer with repeated `--cabana-arg` options (for example `--cabana-arg --dcam`). These flags are appended to the Cabana invocation.
- The viewer launches Cabana as a real subprocess (argv-style), so arguments are passed exactly; it also sets `QT_QPA_PLATFORM=xcb` for the spawned Cabana process when needed.
- If you run `cpd_detector.py` it will automatically start `cpd_viewer.py` after the CSV is written, using the derived route name. You can also run the viewer manually against any CSV.

Notes
- The script preserves per-signal state across the provided inputs in a single run (so events spanning files will be tracked).
- Duplicate paths are removed by exact-path deduplication; if you need stronger dedupe (by inode or content hash) open an issue or ask for a change.

CSV example (header shown):
```
event_id,timestamp,seconds_elapsed,segment_index,file,signal,event,from_value,to_value,from_label,to_label,child_duration_seconds
1,00:00:23,23.152,0,segment0.rlog,RL,ENTER_CHILD,0,2,Empty,Child,
2,00:01:47,107.235,1,segment1.rlog,RL,EXIT_CHILD,2,0,Child,Empty,47.235

```

This tool enables tracking CPD events and aligning them with Cabana recordings for labeling and retraining.

### ###
--- ---
We want to add it in a way that the events recorded can be clicked on and the video of this instance is opened in Cabana so it can be verified.
We also want to look at the possibility of doing it in the engineering app perhaps next to the pointcloud
--- ---
### ###
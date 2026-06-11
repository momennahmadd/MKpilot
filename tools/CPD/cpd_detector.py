
import os
import sys
import csv
import subprocess
from datetime import datetime
from pathlib import Path
from cereal import log

# reuse existing LogReader which handles .bz2/.zst and parsing
try:
    from openpilot.tools.lib.logreader import LogReader
except Exception:
    LogReader = None

### Configs ###
TARGET_CAN_ID = 0x235  # decimal = 565
TARGET_BUS = 0

# mapping signal names to bit position and length
SIGNALS = {
    "FL": (0, 4),
    "FR": (4, 4),
    "RL": (8, 4),
    "RC": (12, 4),
    "RR": (16, 4),
    "ALL": (20, 4),
    "FOOT": (24, 4),
}


# decode enum
ENUM = {
    0: "Empty",
    1: "Adult",
    2: "Child",
    3: "Pet",
    4: "Unknown"
}


### Helpers ###

def get_bits(data, start_bit, length):
    # Extract bits (little-endian)
    value = int.from_bytes(data, byteorder="little")
    return (value >> start_bit) & ((1 << length) - 1)


def ns_to_datetime_str(ns):
    # Convert nanoseconds → readable absolute time HH:MM:SS
    seconds = ns / 1e9
    return datetime.utcfromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def drive_relative_seconds(file_index, timestamp_ns, segment_start_ns):
    # Cabana needs a route-relative offset, not an absolute wall-clock time.
    return file_index * 60.0 + ((timestamp_ns - segment_start_ns) / 1e9)


def format_relative_time(seconds_elapsed):
    total_seconds = int(seconds_elapsed)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def display_log_path(log_file):
    parent_name = os.path.basename(os.path.dirname(str(log_file)))
    file_name = os.path.basename(str(log_file))
    return os.path.join(parent_name, file_name) if parent_name else file_name


### Processing ###

def process_files(file_list, output_csv="combined_output.csv"):

    # sort files to ensure correct order
    file_list.sort()

    # track previous values
    last_values = {sig: None for sig in SIGNALS}  # noqa: C420

    # track child start times
    child_start_time = {sig: None for sig in SIGNALS}  # noqa: C420

    event_count = 0

    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "event_id",
            "timestamp",
            "seconds_elapsed",
            "segment_index",
            "file",
            "signal",
            "event",
            "from_value",
            "to_value",
            "from_label",
            "to_label",
            "child_duration_seconds"
        ])

        for file_index, log_file in enumerate(file_list):
            print(f"[{file_index+1}/{len(file_list)}] Processing {log_file}")
            segment_start_ns = None

            # If LogReader is available, use it to handle compressed logs and parsing
            if LogReader is not None:
                try:
                    lr = LogReader(log_file)
                except Exception:
                    # fallback: try treating as raw file path
                    lr = None

                if lr is not None:
                    for evt in lr:
                        if evt.which() != 'can':
                            continue

                        timestamp_ns = evt.logMonoTime
                        if segment_start_ns is None:
                            segment_start_ns = timestamp_ns

                        for can_msg in evt.can:
                            if can_msg.address != TARGET_CAN_ID or can_msg.src != TARGET_BUS:
                                continue

                            data = bytes(can_msg.dat)

                            for sig, (start, length) in SIGNALS.items():
                                value = get_bits(data, start, length)
                                prev = last_values[sig]

                                if prev is not None and value != prev:

                                    seconds_elapsed = drive_relative_seconds(file_index, timestamp_ns, segment_start_ns)
                                    timestamp_str = format_relative_time(seconds_elapsed)

                                    # --- ENTER CHILD ---
                                    if value == 2 and prev != 2:
                                        event_count += 1

                                        child_start_time[sig] = timestamp_ns

                                        writer.writerow([
                                            event_count,
                                            timestamp_str,
                                            f"{seconds_elapsed:.3f}",
                                            file_index,
                                            display_log_path(log_file),
                                            sig,
                                            "ENTER_CHILD",
                                            prev,
                                            value,
                                            ENUM.get(prev, prev),
                                            ENUM.get(value, value),
                                            ""
                                        ])

                                    # --- EXIT CHILD ---
                                    elif prev == 2 and value != 2:
                                        event_count += 1

                                        duration = ""
                                        if child_start_time[sig] is not None:
                                            duration = round((timestamp_ns - child_start_time[sig]) / 1e9, 3)

                                        writer.writerow([
                                            event_count,
                                            timestamp_str,
                                            f"{seconds_elapsed:.3f}",
                                            file_index,
                                            display_log_path(log_file),
                                            sig,
                                            "EXIT_CHILD",
                                            prev,
                                            value,
                                            ENUM.get(prev, prev),
                                            ENUM.get(value, value),
                                            duration
                                        ])

                                        child_start_time[sig] = None

                                last_values[sig] = value
                    continue

            # Fallback: raw file open + capnp streaming (original behavior)
            try:
                with open(log_file, "rb") as f:
                    while True:
                        try:
                            evt = log.Event.read(f)
                        except Exception:
                            break

                        if evt.which() != 'can':
                            continue

                        timestamp_ns = evt.logMonoTime
                        if segment_start_ns is None:
                            segment_start_ns = timestamp_ns

                        for msg in evt.can:
                            if msg.address != TARGET_CAN_ID or msg.src != TARGET_BUS:
                                continue

                            data = bytes(msg.dat)

                            for sig, (start, length) in SIGNALS.items():
                                value = get_bits(data, start, length)
                                prev = last_values[sig]

                                if prev is not None and value != prev:

                                    seconds_elapsed = drive_relative_seconds(file_index, timestamp_ns, segment_start_ns)
                                    timestamp_str = format_relative_time(seconds_elapsed)

                                    # --- ENTER CHILD ---
                                    if value == 2 and prev != 2:
                                        event_count += 1

                                        child_start_time[sig] = timestamp_ns

                                        writer.writerow([
                                            event_count,
                                            timestamp_str,
                                            f"{seconds_elapsed:.3f}",
                                            file_index,
                                            display_log_path(log_file),
                                            sig,
                                            "ENTER_CHILD",
                                            prev,
                                            value,
                                            ENUM.get(prev, prev),
                                            ENUM.get(value, value),
                                            ""
                                        ])

                                    # --- EXIT CHILD ---
                                    elif prev == 2 and value != 2:
                                        event_count += 1

                                        duration = ""
                                        if child_start_time[sig] is not None:
                                            duration = round((timestamp_ns - child_start_time[sig]) / 1e9, 3)

                                        writer.writerow([
                                            event_count,
                                            timestamp_str,
                                            f"{seconds_elapsed:.3f}",
                                            file_index,
                                            display_log_path(log_file),
                                            sig,
                                            "EXIT_CHILD",
                                            prev,
                                            value,
                                            ENUM.get(prev, prev),
                                            ENUM.get(value, value),
                                            duration
                                        ])

                                        child_start_time[sig] = None

                                last_values[sig] = value
            except FileNotFoundError:
                print(f"File not found: {log_file}")

    print("\n Processing complete")
    print(f" Total events detected: {event_count}")
    print(f" Output file: {output_csv}")


### Inputs ###

def collect_files(inputs):
    files = []

    def is_rlog_filename(name: str) -> bool:
        ln = name.lower()
        return 'rlog' in ln and ln.endswith(('.bz2', '.zst', '.rlog', '.rlog.bz2', '.rlog.zst', 'rlog'))

    for inp in inputs:
        # if input is a directory, walk one or two levels to find segment archives or log files
        if os.path.isdir(inp):
            for root, _, files_in_dir in os.walk(inp):
                for f in files_in_dir:
                    if is_rlog_filename(f):
                        files.append(os.path.join(root, f))
                # don't recurse into very deep trees unnecessarily: os.walk will handle it but typical segment layouts are shallow
        else:
            if is_rlog_filename(os.path.basename(inp)):
                files.append(inp)

    # remove duplicates while preserving order
    seen = set()
    out = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def derive_route_name(inputs):
    if not inputs:
        return "combined_output"

    first_input = inputs[0]
    if os.path.isdir(first_input):
        return os.path.basename(os.path.normpath(first_input)) or "combined_output"

    parent_dir = os.path.dirname(os.path.abspath(first_input))
    return os.path.basename(parent_dir) or os.path.splitext(os.path.basename(first_input))[0] or "combined_output"


def launch_viewer(csv_path, route_name):
    repo_root = Path(__file__).resolve().parents[2]
    viewer_script = repo_root / "tools" / "CPD" / "cpd_viewer.py"

    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "xcb")

    try:
        subprocess.Popen(
            [sys.executable, str(viewer_script), csv_path, route_name, "--port", "0"],
            cwd=str(repo_root),
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Launched CPD viewer for {csv_path}")
    except Exception as e:
        print(f"Unable to launch CPD viewer: {e}")


### Main ###

if __name__ == "__main__":

    inputs = sys.argv[1:]

    if not inputs:
        print("Usage:")
        print("  cpd_detector.py file1.rlog file2.rlog")
        print("  cpd_detector.py ./folder/")
        sys.exit(1)

    files = collect_files(inputs)

    if not files:
        print("No log files found.")
        sys.exit(1)

    print(f"Found {len(files)} files.")

    route_name = derive_route_name(inputs)
    output_csv = f"{route_name}.csv"
    print(f"Saving CSV as {output_csv}")

    process_files(files, output_csv=output_csv)
    launch_viewer(output_csv, route_name)

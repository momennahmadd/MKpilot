
import os
import sys
import csv
from datetime import datetime
from cereal import log

### Configs ###
TARGET_CAN_ID = 0x235  # decimal = 565
TARGET_BUS = 2

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


### Processing ###

def process_files(file_list, output_csv="combined_output.csv"):

    # sort files to ensure correct order
    file_list.sort()

    # track previous values
    last_values = {sig: None for sig in SIGNALS}

    # track child start times
    child_start_time = {sig: None for sig in SIGNALS}

    event_count = 0

    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "event_id",
            "timestamp",
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

            with open(log_file, "rb") as f:
                while True:
                    try:
                        evt = log.Event.read(f)
                    except Exception:
                        break

                    if evt.which() != 'can':
                        continue

                    timestamp_ns = evt.logMonoTime

                    for msg in evt.can:
                        if msg.address != TARGET_CAN_ID or msg.src != TARGET_BUS:
                            continue

                        data = bytes(msg.dat)

                        for sig, (start, length) in SIGNALS.items():
                            value = get_bits(data, start, length)
                            prev = last_values[sig]

                            if prev is not None and value != prev:

                                timestamp_str = ns_to_datetime_str(timestamp_ns)

                                # --- ENTER CHILD ---
                                if value == 2 and prev != 2:
                                    event_count += 1

                                    child_start_time[sig] = timestamp_ns

                                    writer.writerow([
                                        event_count,
                                        timestamp_str,
                                        os.path.basename(log_file),
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
                                        os.path.basename(log_file),
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

    print("\n Processing complete")
    print(f" Total events detected: {event_count}")
    print(f" Output file: {output_csv}")


### Inputs ###

def collect_files(inputs):
    files = []

    for inp in inputs:
        if os.path.isdir(inp):
            for f in os.listdir(inp):
                if f.endswith(".rlog") or f.endswith(".qlog"):
                    files.append(os.path.join(inp, f))
        else:
            files.append(inp)

    return files


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

    process_files(files)

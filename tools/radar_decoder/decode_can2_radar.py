#!/usr/bin/env python3
import argparse
import time

import cereal.messaging as messaging

from opendbc.can import CANParser
from opendbc.can.dbc import DBC
from openpilot.selfdrive.pandad import can_capnp_to_list


def build_parser(dbc_name: str, bus: int) -> tuple[CANParser, DBC]:
  dbc = DBC(dbc_name)
  # Subscribe to every message in the DBC and disable alive-time checks for this debug tool.
  checks = [(addr, float('nan')) for addr in sorted(dbc.addr_to_msg.keys())]
  return CANParser(dbc_name, checks, bus), dbc


def relax_parser_integrity_checks(parser: CANParser) -> None:
  # Useful for offline smoke tests with synthetic data that won't have real checksums/counters.
  for state in parser.message_states.values():
    state.ignore_checksum = True
    state.ignore_counter = True


def summarize_updates(parser: CANParser, dbc: DBC, updated_addrs: set[int], max_lines: int) -> list[str]:
  lines: list[str] = []
  for addr in sorted(updated_addrs):
    msg = dbc.addr_to_msg.get(addr)
    if msg is None:
      continue

    sig_values = parser.vl[addr]
    preview_keys = list(sig_values.keys())[:6]
    preview = ", ".join(f"{k}={sig_values[k]:.3f}" for k in preview_keys)
    if len(sig_values) > len(preview_keys):
      preview += ", ..."

    lines.append(f"{addr:#05x} {msg.name}: {preview}")
    if len(lines) >= max_lines:
      break
  return lines


def build_signal_payload(parser: CANParser, dbc: DBC, updated_addrs: set[int]) -> tuple[list[str], list[float]]:
  keys: list[str] = []
  values: list[float] = []

  for addr in sorted(updated_addrs):
    msg = dbc.addr_to_msg.get(addr)
    if msg is None:
      continue

    sig_values = parser.vl[addr]
    for signal_name in sorted(sig_values.keys()):
      keys.append(f"{msg.name}.{signal_name}")
      values.append(float(sig_values[signal_name]))

  return keys, values


def publish_validation_frame(pm: messaging.PubMaster, service: str, mono_time: int, bus: int,
                             producer: str, origin: str, valid: bool,
                             keys: list[str], values: list[float]) -> None:
  msg = messaging.new_message(service, valid=valid)
  frame = getattr(msg, service)
  frame.producer = producer
  frame.origin = origin
  frame.monoTime = mono_time
  frame.bus = bus
  frame.valid = valid
  key_list = frame.init('keys', len(keys))
  value_list = frame.init('values', len(values))
  for idx, key in enumerate(keys):
    key_list[idx] = key
  for idx, value in enumerate(values):
    value_list[idx] = value
  pm.send(service, msg)


def run_demo(can_parser: CANParser, dbc: DBC, bus: int, max_lines: int, demo_iterations: int, demo_sleep: float) -> None:
  relax_parser_integrity_checks(can_parser)
  print(f"Decoder started: mode=demo dbc={dbc.name} bus={bus}")
  print("Demo mode enabled: checksum/counter checks are relaxed for synthetic frames")

  frames = [(addr, bytes(msg.size), bus) for addr, msg in sorted(dbc.addr_to_msg.items())]
  total_updated = 0
  for _ in range(demo_iterations):
    now_ns = int(time.monotonic() * 1e9)
    updated_addrs = can_parser.update([(now_ns, frames)])
    total_updated += len(updated_addrs)

    print(f"\n[{time.strftime('%H:%M:%S')}] updated={len(updated_addrs)} total={total_updated}")
    for line in summarize_updates(can_parser, dbc, updated_addrs, max_lines):
      print(line)

    time.sleep(demo_sleep)


def run_live(can_parser: CANParser, dbc: DBC, bus: int, print_interval: float, max_lines: int,
             service: str = "radarDecoded", producer: str = "radar", origin: str = "can2") -> None:
  pm = messaging.PubMaster([service])
  sock = messaging.sub_sock("can", conflate=True)
  last_print_t = 0.0
  total_updated = 0

  print(f"Decoder started: mode=live dbc={dbc.name} bus={bus} service={service}")
  while True:
    can_strings = messaging.drain_sock_raw(sock, wait_for_one=True)
    can_batches = can_capnp_to_list(can_strings)

    for mono_time, frames in can_batches:
      updated_addrs = can_parser.update([(mono_time, frames)])
      total_updated += len(updated_addrs)

      if not updated_addrs:
        continue

      keys, values = build_signal_payload(can_parser, dbc, updated_addrs)
      publish_validation_frame(pm, service, mono_time, bus, producer, origin, can_parser.can_valid, keys, values)

      now = time.monotonic()
      if now - last_print_t >= print_interval:
        print(f"\n[{time.strftime('%H:%M:%S')}] updated={len(updated_addrs)} total={total_updated}")
        for line in summarize_updates(can_parser, dbc, updated_addrs, max_lines):
          print(line)
        last_print_t = now


def main() -> None:
  parser = argparse.ArgumentParser(description="Decode CAN2 radar messages from live or demo input")
  parser.add_argument("--dbc", default="radar_CAN2", help="DBC name or path (default: radar_CAN2)")
  parser.add_argument("--bus", type=int, default=2, help="CAN bus src index (default: 2)")
  parser.add_argument("--mode", choices=["live", "demo"], default="live", help="Input mode (default: live)")
  parser.add_argument("--print-interval", type=float, default=0.5, help="Seconds between prints")
  parser.add_argument("--max-lines", type=int, default=20, help="Max decoded message lines per print")
  parser.add_argument("--demo-iterations", type=int, default=3, help="Demo loops before exit")
  parser.add_argument("--demo-sleep", type=float, default=0.25, help="Seconds between demo loops")
  args = parser.parse_args()

  can_parser, dbc = build_parser(args.dbc, args.bus)

  if args.mode == "demo":
    run_demo(can_parser, dbc, args.bus, args.max_lines, args.demo_iterations, args.demo_sleep)
    return

  run_live(can_parser, dbc, args.bus, args.print_interval, args.max_lines)


if __name__ == "__main__":
  main()

#!/usr/bin/env python3
import os

from openpilot.tools.radar_decoder.decode_can2_radar import build_parser, run_live


def main() -> None:
  dbc_name = os.getenv("RADAR_DECODER_DBC", "radar_CAN2")
  bus = int(os.getenv("RADAR_DECODER_BUS", "2"))
  print_interval = float(os.getenv("RADAR_DECODER_PRINT_INTERVAL", "1.0"))
  max_lines = int(os.getenv("RADAR_DECODER_MAX_LINES", "20"))
  service = os.getenv("RADAR_DECODER_TOPIC", "radarDecoded")
  producer = os.getenv("RADAR_DECODER_PRODUCER", "radar")
  origin = os.getenv("RADAR_DECODER_ORIGIN", f"can{bus}")

  can_parser, dbc = build_parser(dbc_name, bus)
  run_live(can_parser, dbc, bus, print_interval, max_lines, service=service, producer=producer, origin=origin)


if __name__ == "__main__":
  main()

#!/usr/bin/env python3
import time

import cereal.messaging as messaging
from msgq import pub_sock, sub_sock


def main() -> None:
  sock = sub_sock('radarDecoded', timeout=200)
  pub = pub_sock('radarDecoded')

  time.sleep(0.1)

  msg = messaging.new_message('radarDecoded', valid=True)
  frame = msg.radarDecoded
  frame.producer = 'radar'
  frame.origin = 'can2'
  frame.monoTime = int(time.monotonic() * 1e9)
  frame.bus = 2
  frame.valid = True

  keys = ['OCCUPANT_STATUS.FL_1SL_Class', 'OCCUPANT_STATUS.FR_1SR_Class']
  values = [0.25, 0.75]
  key_list = frame.init('keys', len(keys))
  value_list = frame.init('values', len(values))
  for i, key in enumerate(keys):
    key_list[i] = key
  for i, value in enumerate(values):
    value_list[i] = value

  pub.send(msg.to_bytes())

  raw = sock.receive()
  if raw is None:
    time.sleep(0.1)
    raw = sock.receive()
  if raw is None:
    raise SystemExit('radarDecoded loopback failed: subscriber did not receive the message')

  decoded = messaging.log_from_bytes(raw)
  if decoded.which() != 'radarDecoded':
    raise SystemExit(f'radarDecoded loopback failed: got {decoded.which()} instead')

  frame = decoded.radarDecoded
  print('radarDecoded loopback ok')
  print(f'producer={frame.producer} origin={frame.origin} bus={frame.bus} valid={frame.valid}')
  print(f'keys={list(frame.keys)}')
  print(f'values={list(frame.values)}')


if __name__ == '__main__':
  main()

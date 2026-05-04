## CAN2 Radar Decoder (No Selfdrive)

This tool decodes live CAN messages from the `can` socket on a chosen bus using a DBC.

It is designed for unsupported cars where you do not want autonomous/selfdrive features and only need radar decode for validation.

### Default setup

- DBC: `radar_CAN2`
- Bus: `2`

### Run (live CAN)

```bash
source .venv/bin/activate
python tools/radar_decoder/decode_can2_radar.py --dbc radar_CAN2 --bus 2
```

### Run (laptop/offline demo)

Use demo mode to validate parser wiring without live CAN.

```bash
source .venv/bin/activate
python tools/radar_decoder/decode_can2_radar.py --mode demo --dbc radar_CAN2 --bus 2 --demo-iterations 2
```

### Optional arguments

- `--print-interval 0.5` seconds between output blocks
- `--max-lines 20` max decoded message lines per output block
- `--mode demo` run with synthetic frames and exit after `--demo-iterations`

### Notes

- This script subscribes to the existing `can` publisher (from `pandad`).
- If no decoded lines appear, first confirm frames are present on `src==2` in Cabana.

### Always-on on device (autostart)

This repo is configured to autostart the decoder from openpilot's manager.

The process name is `radar_decoderd` and it starts from:

- `tools.radar_decoder.radar_decoderd`

It publishes decoded radar frames on the `radarDecoded` topic using the shared `validationFrame` schema.
The same schema can later be used by a SOME/IP publisher on `someipDecoded`.

A validation process can subscribe to both topics:

```python
import cereal.messaging as messaging

sm = messaging.SubMaster(['radarDecoded', 'someipDecoded'])
while True:
	sm.update()
	if sm.updated['radarDecoded']:
		print('radar:', sm['radarDecoded'].producer, sm['radarDecoded'].keys)
	if sm.updated['someipDecoded']:
		print('someip:', sm['someipDecoded'].producer, sm['someipDecoded'].keys)
```

Autostart is controlled by environment variables in `launch_env.sh`:

- `RADAR_DECODER_AUTOSTART=1`
- `RADAR_DECODER_DBC=radar_CAN2`
- `RADAR_DECODER_BUS=2`
- `RADAR_DECODER_TOPIC=radarDecoded`
- `RADAR_DECODER_PRODUCER=radar`
- `RADAR_DECODER_ORIGIN=can2`
- `RADAR_DECODER_PRINT_INTERVAL=1.0`
- `RADAR_DECODER_MAX_LINES=20`

To disable autostart, set:

```bash
export RADAR_DECODER_AUTOSTART=0
```

Then restart openpilot manager (or reboot the device).

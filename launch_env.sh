#!/usr/bin/env bash

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# models get lower priority than ui
# - ui is ~5ms
# - modeld is 20ms
# - DM is 10ms
# in order to run ui at 60fps (16.67ms), we need to allow
# it to preempt the model workloads. we have enough
# headroom for this until ui is moved to the CPU.
export QCOM_PRIORITY=12

if [ -z "$AGNOS_VERSION" ]; then
  export AGNOS_VERSION="17.2"
fi

export STAGING_ROOT="/data/safe_staging"

# Always-on standalone CAN2 radar decoder (no selfdrive dependency)
export RADAR_DECODER_AUTOSTART=1
export RADAR_DECODER_DBC="radar_CAN2"
export RADAR_DECODER_BUS=2
export RADAR_DECODER_TOPIC="radarDecoded"
export RADAR_DECODER_PRODUCER="radar"
export RADAR_DECODER_ORIGIN="can2"
export RADAR_DECODER_PRINT_INTERVAL=1.0
export RADAR_DECODER_MAX_LINES=20

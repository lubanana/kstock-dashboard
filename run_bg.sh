#!/bin/bash
# Run Level 1 Cron Batch continuously in background

cd /home/programs/kstock_analyzer

while true; do
    python3 level1_cron_batch.py >> logs/bg_cron.log 2>&1
    sleep 5
done

#!/bin/bash
# Borg backup of the read-only casper share (/mnt/casper-data), metrics pushed to the Pushgateway.
# Forgejo's SSH host keys are excluded: root-only on casper and unreadable through the root_squash
# export (they made every run end with rc 1). Forgejo regenerates them if missing; clients then see a new host key.
# borg reads BORG_REPO and BORG_PASSCOMMAND natively, so the commands below never name the repository.
# Both can be overridden from the environment (e.g. to test against another repository).
export BORG_REPO="${BORG_REPO:-/mnt/data/backup-casper}"
export BORG_PASSCOMMAND="${BORG_PASSCOMMAND:-cat /home/magi/.bak_psw}"

PUSHGATEWAY_URL="https://pushgateway.internal.fferrando.cc"
JOB_NAME="personal_files"
INSTANCE_NAME=$(hostname)
START_TIME=$(date +%s)

borg create \
  --verbose \
  --filter AME \
  --list \
  --stats \
  --show-rc \
  --compression zstd \
  --exclude '**/appdata_*' \
  --exclude '/mnt/casper-data/git/ssh/ssh_host_*' \
  '::{hostname}-{now:%Y-%m-%dT%H:%M:%S}' \
  /mnt/casper-data
CREATE_EXIT=$?

borg prune \
  --list \
  --keep-daily=5 \
  --keep-weekly=3 \
  --keep-monthly=3
PRUNE_EXIT=$?

borg compact
COMPACT_EXIT=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# The last-success metric is only pushed on success: the push is a POST, which replaces just the
# metrics it contains, so a failed run keeps the previous success time in the Pushgateway.
LAST_SUCCESS_METRIC=""
if [ $CREATE_EXIT -eq 0 ] && [ $PRUNE_EXIT -eq 0 ] && [ $COMPACT_EXIT -eq 0 ]; then
  STATUS=1
  LAST_SUCCESS_METRIC="# HELP backup_last_success_timestamp_seconds Unix epoch of the last entirely successful run
# TYPE backup_last_success_timestamp_seconds gauge
backup_last_success_timestamp_seconds ${END_TIME}"
else
  STATUS=0
fi

cat <<EOF | curl --data-binary @- -s "${PUSHGATEWAY_URL}/metrics/job/${JOB_NAME}/instance/${INSTANCE_NAME}"
# HELP backup_status Overall success of the backup (1=success, 0=failure)
# TYPE backup_status gauge
backup_status ${STATUS}
# HELP backup_create_exit_code Exit code of borg create
# TYPE backup_create_exit_code gauge
backup_create_exit_code ${CREATE_EXIT}
# HELP backup_prune_exit_code Exit code of borg prune
# TYPE backup_prune_exit_code gauge
backup_prune_exit_code ${PRUNE_EXIT}
# HELP backup_compact_exit_code Exit code of borg compact
# TYPE backup_compact_exit_code gauge
backup_compact_exit_code ${COMPACT_EXIT}
# HELP backup_duration_seconds Time taken to run the entire backup script
# TYPE backup_duration_seconds gauge
backup_duration_seconds ${DURATION}
${LAST_SUCCESS_METRIC}
EOF

# Non-zero on failure, so cron (and a manual run) shows it
[ "$STATUS" -eq 1 ]

#!/bin/bash

PUSHGATEWAY_URL="https://pushgateway.rdfilippo.mywire.org"
JOB_NAME="db_files"
INSTANCE_NAME=$(hostname)

START_TIME=$(date +%s)

DUMP_DIR="/tmp/db_dump"

rm -rf "$DUMP_DIR"
mkdir -p "$DUMP_DIR"

PG_SUPERUSER_PASS="super_secret_root_password"
DATE_SUFFIX=$(date +%Y%m%d_%H%M%S)

docker run --rm --network db_network \
  -v "${DUMP_DIR}:/dumps" \
  -e PGPASSWORD="${PG_SUPERUSER_PASS}" \
  postgres:15-alpine \
  pg_dumpall -h pgpool -U postgres -f "/dumps/cluster_all_dbs_${DATE_SUFFIX}.sql"

NET_DB_EXIT=$?

DUMP_BYTES=$(du -sb "$DUMP_DIR" | awk '{print $1}')

if [ $NET_DB_EXIT -eq 0 ]; then
  DUMP_EXIT=0
else
  DUMP_EXIT=1
fi

if [ $DUMP_EXIT -eq 0 ]; then
  borg create \
    -v \
    --filter AME \
    --list \
    --stats \
    -- show-rc \
    --compression zstd \
    $REPO::"{hostname}-{now}" "$DUMP_DIR"

  CREATE_EXIT=$?

  borg prune -v --list --keep-daily=7 $REPO
  PRUNE_EXIT=$?

  borg compact $REPO
  COMPACT_EXIT=$?
else
  CREATE_EXIT=1
  PRUNE_EXIT=1
  COMPACT_EXIT=1
fi

rm -rf "$DUMP_DIR"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $DUMP_EXIT -eq 0 ] && [ $CREATE_EXIT -eq 0 ] && [ $PRUNE_EXIT -eq 0 ] && [ $CHECK_EXIT -eq 0 ]; then
  STATUS=1
  LAST_SUCCESS=$END_TIME
else
  STATUS=0
  LAST_SUCCESS=0
fi

cat <<EOF | curl --data-binary @- -s "${PUSHGATEWAY_URL}/metrics/job/${JOB_NAME}/instance/${INSTANCE_NAME}"
# HELP backup_status Overall success of the backup (1=success, 0=failure)
# TYPE backup_status gauge
backup_status ${STATUS}

# HELP backup_net_db_exit_code Exit code of the network DB dump
# TYPE backup_net_db_exit_code gauge
backup_net_db_exit_code ${NET_DB_EXIT}

# HELP backup_sqlite_exit_code Exit code of the SQLite DB dump
# TYPE backup_sqlite_exit_code gauge
backup_sqlite_exit_code ${SQLITE_EXIT}

# HELP backup_create_exit_code Exit code of borg create
# TYPE backup_create_exit_code gauge
backup_create_exit_code ${CREATE_EXIT}

# HELP backup_prune_exit_code Exit code of borg prune
# TYPE backup_prune_exit_code gauge
backup_prune_exit_code ${PRUNE_EXIT}

# HELP backup_check_exit_code Exit code of borg check
# TYPE backup_check_exit_code gauge
backup_check_exit_code ${CHECK_EXIT}

# HELP backup_dump_bytes Total size of uncompressed SQL dumps
# TYPE backup_dump_bytes gauge
backup_dump_bytes ${DUMP_BYTES}

# HELP backup_duration_seconds Time taken to run the entire backup script
# TYPE backup_duration_seconds gauge
backup_duration_seconds ${DURATION}

# HELP backup_last_success_timestamp_seconds Unix epoch of the last entirely successful run
# TYPE backup_last_success_timestamp_seconds gauge
backup_last_success_timestamp_seconds ${LAST_SUCCESS}
EOF

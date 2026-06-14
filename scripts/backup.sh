#!/bin/bash
set -e
cd ""/usr/bin/.."
TS=20260613_134037
BACKUP_DIR="backups/"
mkdir -p ""
echo "Backup to "
# SQLite
if [ -f backend/data_agent.db ]; then
    cp backend/data_agent.db "/"
    echo "  SQLite: saved"
fi
# Session data
if [ -d backend/session_data ]; then
    cp -r backend/session_data "/"
    echo "  Session data: saved"
fi
# Exports
if [ -d backend/exports ]; then
    cp -r backend/exports "/"
    echo "  Exports: saved"
fi
echo "Backup complete: "

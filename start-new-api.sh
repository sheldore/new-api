#!/bin/bash

cd /opt/new-api

export PORT=3001
export LOG_DIR=/opt/new-api/logs
export SESSION_SECRET="your_unique_session_secret_here"
export TZ=Asia/Shanghai
export MEMORY_CACHE_ENABLED=true
export ERROR_LOG_ENABLED=true

mkdir -p $LOG_DIR

./new-api
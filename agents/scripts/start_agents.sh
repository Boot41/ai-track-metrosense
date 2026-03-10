#!/usr/bin/env bash
set -euo pipefail

adk_port="${ADK_PORT:-8021}"
proxy_port="${PROXY_PORT:-8020}"

uv run adk api_server --host 0.0.0.0 --port "$adk_port" . &
adk_pid=$!

uv run uvicorn app.proxy:app --host 0.0.0.0 --port "$proxy_port" &
proxy_pid=$!

trap 'kill "$adk_pid" "$proxy_pid"' INT TERM

wait -n "$adk_pid" "$proxy_pid"
kill "$adk_pid" "$proxy_pid"
wait

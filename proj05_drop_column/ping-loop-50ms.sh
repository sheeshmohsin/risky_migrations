#!/usr/bin/env bash
# ping-loop-50ms.sh
# Continuously pings the endpoint every 50ms

URL="${1:-http://localhost:8001/list_large/}"
INTERVAL="0.05"   # 50 milliseconds
CURL_TIMEOUT=15
SNIPPET_BYTES=200

trap 'echo; echo "Interrupted — exiting."; exit 0' INT

echo "Pinging ${URL} every ${INTERVAL}s (curl timeout ${CURL_TIMEOUT}s). Press Ctrl+C to stop."
while true; do
  ts=$(date +"%Y-%m-%d %H:%M:%S.%3N")
  tmp=$(mktemp)
  http_info=$(curl -sS --max-time "${CURL_TIMEOUT}" -w "%{http_code} %{time_total}" -o "${tmp}" "${URL}" 2>&1)
  curl_exit=$?

  if [ $curl_exit -ne 0 ]; then
    echo "${ts}  ERROR curl(${curl_exit}) ${http_info}"
  else
    http_code=$(awk '{print $1}' <<<"$http_info")
    time_total=$(awk '{print $2}' <<<"$http_info")
    snippet=$(head -c "${SNIPPET_BYTES}" "${tmp}" | tr '\n' '↵')
    echo "${ts}  HTTP:${http_code}  time:${time_total}s  body_snippet:\"${snippet}\""
  fi

  rm -f "${tmp}"
  sleep "${INTERVAL}"
done


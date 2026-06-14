#!/bin/bash
# Docker environment validation
set -e
cd ""/usr/bin/.."
echo "=== Docker Validation ==="

echo "
--- docker ps ---"
docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"

echo "
--- Container Check ---"
for svc in backend frontend redis mysql nginx; do
    if docker ps --format '{{.Names}}' | grep -q "data-agent-"; then
        echo "  : RUNNING"
    else
        echo "  : NOT RUNNING"
    fi
done

echo "
--- Backend Health ---"
curl -s http://localhost:8001/system/health 2>/dev/null || echo "  Backend unreachable"

echo "
--- Frontend ---"
curl -s -o /dev/null -w "  HTTP %{http_code}" http://localhost:3000 2>/dev/null || echo "  Frontend unreachable"

echo "
=== Done ==="

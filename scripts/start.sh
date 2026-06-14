#!/bin/bash
# Start production stack
set -e
cd ""/usr/bin/.."
echo "Starting Multi-Agent Data Platform..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
echo "Waiting for services..."
sleep 5
docker compose ps
echo "Services started."
curl -s http://localhost/system/health | python3 -m json.tool

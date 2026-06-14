#!/bin/bash
cd ""/usr/bin/.."
echo "Stopping..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
echo "Stopped."

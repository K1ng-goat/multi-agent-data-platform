#!/bin/bash
cd ""/usr/bin/.."
echo "Restarting..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
echo "Restarted."

#!/bin/bash

# Setup OSRM with Philippines map data
set -e

echo "📥 Downloading Philippines map data from Geofabrik..."
cd /home/adrian/vrp/vroom_ors/osrm-philippines

# Download Philippines map if not exists
if [ ! -f "philippines-latest.osm.pbf" ]; then
    wget -c https://download.geofabrik.de/asia/philippines-latest.osm.pbf
else
    echo "✓ Map file already exists"
fi

echo "🔧 Processing map data with OSRM..."

# Extract
echo "  1/3 Extracting..."
docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/philippines-latest.osm.pbf

# Partition (for MLD algorithm)
echo "  2/3 Partitioning..."
docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/philippines-latest.osrm

# Customize
echo "  3/3 Customizing..."
docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/philippines-latest.osrm

echo "✅ Philippines map data ready!"
echo "🚀 Restart OSRM: docker-compose up -d osrm"

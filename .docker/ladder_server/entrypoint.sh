#!/bin/sh
# Read banned profile IDs from /home/openra/banned_profiles
BANS_FILE="/home/openra/banned_profiles"
BANS=$(python3 -c "from srvwrap_minimal import apply_bans; apply_bans(\"$BANS_FILE\")")
ProfileIDBlacklist=$BANS
export ProfileIDBlacklist
echo "Banned profiles: ${ProfileIDBlacklist:-}"

# Read map pool from /home/openra/mappool
POOL_FILE="/home/openra/mappool"
POOL=$(python3 -c "from srvwrap_minimal import load_mappool_from_file; load_mappool_from_file(\"$POOL_FILE\")")
MapPool=$POOL
export MapPool
echo "Map pool: ${MapPool:-}"

echo "Starting OpenRA server."
/home/openra/server.sh

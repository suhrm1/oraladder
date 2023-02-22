#!/bin/sh
# Read banned profile IDs from /home/openra/banned_profiles
BANS_FILE="/home/openra/banned_profiles"
BANS=$(python3 -c "from srvwrap_minimal import apply_bans; apply_bans(\"$BANS_FILE\")")
ProfileIDBlacklist=$BANS
export ProfileIDBlacklist
echo "Banned profiles: ${ProfileIDBlacklist:-}"

echo "Starting OpenRA server."
/home/openra/server.sh

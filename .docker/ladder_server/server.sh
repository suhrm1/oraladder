#!/bin/sh
# Script starts an OpenRA game server
# Based on https://github.com/OpenRA/OpenRA/blob/bleed/launch-dedicated.sh
# see https://github.com/OpenRA/OpenRA/wiki/Dedicated for details

Name="${Name:-"Dedicated Server"}"
Mod="${Mod:-"ra"}"
ListenPort="${ListenPort:-"1234"}"
AdvertiseOnline="${AdvertiseOnline:-"True"}"
Password="${Password:-""}"
RecordReplays="${RecordReplays:-"False"}"

RequireAuthentication="${RequireAuthentication:-"False"}"
ProfileIDBlacklist="${ProfileIDBlacklist:-""}"
ProfileIDWhitelist="${ProfileIDWhitelist:-""}"

EnableSingleplayer="${EnableSingleplayer:-"False"}"
EnableSyncReports="${EnableSyncReports:-"False"}"
EnableGeoIP="${EnableGeoIP:-"True"}"
ShareAnonymizedIPs="${ShareAnonymizedIPs:-"True"}"

SupportDir="${SupportDir:-""}"

# Run loop to restart game server after a game has completed
while true; do
  # We rotate maps from the map folder to start with a random pick after each game
  hash=$(shuf -n1 -e /home/openra/lib/openra/mods/${Mod}/maps/*.oramap)
  Map=$(./utility.sh $Mod --map-hash $hash)

  # Start the game server
  mono --debug bin/OpenRA.Server.exe Engine.EngineDir=".." Game.Mod="$Mod" \
    Server.Name="$Name" \
    Server.ListenPort="$ListenPort" \
    Server.AdvertiseOnline="$AdvertiseOnline" \
    Server.EnableSingleplayer="$EnableSingleplayer" \
    Server.Password="$Password" \
    Server.RecordReplays="$RecordReplays" \
    Server.GeoIPDatabase="$GeoIPDatabase" \
    Server.RequireAuthentication="$RequireAuthentication" \
    Server.ProfileIDBlacklist="$ProfileIDBlacklist" \
    Server.ProfileIDWhitelist="$ProfileIDWhitelist" \
    Server.EnableSyncReports="$EnableSyncReports" \
    Server.EnableGeoIP="$EnableGeoIP" \
    Server.ShareAnonymizedIPs="$ShareAnonymizedIPs" \
    Server.Map="$Map" \
    Engine.SupportDir="$SupportDir"
done

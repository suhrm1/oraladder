#!/bin/sh
# Script starts an OpenRA game server
# Based on https://github.com/OpenRA/OpenRA/blob/bleed/launch-dedicated.sh
# see https://github.com/OpenRA/OpenRA/wiki/Dedicated for details

Name="${Name:-"Dedicated Server"}"
ListenPort="${ListenPort:-"1234"}"
AdvertiseOnline="${AdvertiseOnline:-"True"}"
Password="${Password:-""}"
RecordReplays="${RecordReplays:-"False"}"

RequireAuthentication="${RequireAuthentication:-"False"}"
ProfileIDBlacklist="${ProfileIDBlacklist:-""}"
ProfileIDWhitelist="${ProfileIDWhitelist:-""}"

# Allow or suppress downloading maps from OpenRA Resource Center
QueryMapRepository=${QueryMapRepository:-"False"}

EnableSingleplayer="${EnableSingleplayer:-"False"}"
EnableSyncReports="${EnableSyncReports:-"False"}"
EnableGeoIP="${EnableGeoIP:-"True"}"
ShareAnonymizedIPs="${ShareAnonymizedIPs:-"True"}"

SupportDir="${SupportDir:-""}"

# We rotate maps from the map folder to start with a random pick after each game
hash=$(shuf -n1 -e /home/openra/usr/lib/openra/mods/${MOD}/maps/*.oramap)
Map=$(/home/openra/AppRun --utility --map-hash $hash)

# Start the game server
/home/openra/AppRun --server \
  Server.Name="$Name" \
  Server.ListenPort="$ListenPort" \
  Server.AdvertiseOnline="$AdvertiseOnline" \
  Server.QueryMapRepository="$QueryMapRepository" \
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

from datetime import date, timedelta

LEAGUE_TITLE = "Red Alert Global League"
LEAGUE_TITLE_SHORT = "RAGL"
TITLE_IMAGE = "ragl-logo.png"
SEASON = 15
START_TIME = date(2023, 10, 9)
GROUP_STAGE_WEEKS = 7
PLAYOFF_WEEKS = 3
DURATION_WEEKS = GROUP_STAGE_WEEKS + PLAYOFF_WEEKS
END_TIME = START_TIME + timedelta(weeks=DURATION_WEEKS)
MAP_PACK_VERSION = "2023-10-12"
RELEASE = "release-20231010"
RELEASE_URL = "https://github.com/OpenRA/OpenRA/releases/tag/" + RELEASE
SCHEDULE_URL = "https://forum.openra.net/viewtopic.php?f=85&t=21802"
RULES_URL = "https://forum.openra.net/viewtopic.php?f=85&t=21790"
PRIZE_POOL = "TBA"
DISCORD_URL = "https://discord.gg/99zBDuS"
DISCORD_NAME = "Red Alert Competitive Discord"
GAMES_PER_MATCH = 2
GAME_SERVER_NAMING_PATTERN = "RAGL Official Server"
# PLAYOFF_SCHEMA_IMG = "tdgl_format_s03.png"


# Used by the Makefile to extract a value
if __name__ == "__main__":
    import sys

    print(globals()[sys.argv[1]])

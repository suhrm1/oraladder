from datetime import date, timedelta

LEAGUE_TITLE = "Tiberian Dawn Global League"
LEAGUE_TITLE_SHORT = "TDGL"
TITLE_IMAGE = "tdgl_logo_s03.png"
SEASON = 3
START_TIME = date(2022, 7, 18)
GROUP_STAGE_WEEKS = 3
PLAYOFF_WEEKS = 2
DURATION_WEEKS = GROUP_STAGE_WEEKS + PLAYOFF_WEEKS
END_TIME = START_TIME + timedelta(weeks=DURATION_WEEKS)
MAP_PACK_VERSION = '2022-07-16'
RELEASE = 'release-20210321'
RELEASE_URL = 'https://github.com/OpenRA/OpenRA/releases/tag/release-20210321'
SCHEDULE_URL = 'https://forum.openra.net/viewtopic.php?f=85&t=21634'
RULES_URL = 'https://forum.openra.net/viewtopic.php?f=85&t=21634'
PRIZE_POOL = '$35'
DISCORD_URL = 'https://discord.gg/AABNUESBFZ'
DISCORD_NAME = 'TDGL Discord'
GAMES_PER_MATCH = 2
GAME_SERVER_NAMING_PATTERN = "TDGL Official Server"
PLAYOFF_SCHEMA_IMG = "tdgl_format_s03.png"


# Used by the Makefile to extract a value
if __name__ == '__main__':
    import sys
    print(globals()[sys.argv[1]])

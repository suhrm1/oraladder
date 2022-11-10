# OpenRA Competitive Ladder Website

Flask-based web interface to display leaderboard and results information about OpenRA
competitive games.

## Configuration

### Multi-Season Support

The current version supports 2-month periods/seasons. By default, the application
expects to host two seasons of each of the mods (Red Alert, Tiberian Dawn): one
ongoing all-time season and one current 2-month season. 2-month seasons are expected to
start on the first day of every second month, i.e. January, March, May, etc.

Handling and display of more (historic) 2-month seasons is possible:

* `LADDER_SEASONS_START_YEAR`,`LADDER_SEASONS_START_MONTH`: Will be used on application
  startup to determine possible historic 2-month seasons.
    * Based on starting year and month, seasons with the following ID schema will be
      supported: `YYYY-n` e.g. `2022-1` for the January-February period of 2022,
      `2021-6` for the Nov-Dec period of 2021 etc.
    * SQLite database files are required to be separately generated (i.e. by using the
      project's `ora-ladder` or `ora-dbtools` command line tools)
    * SQLite database files must be named accordingly, `db-{mod}-{season_id}.sqlite3`,
      e.g. `db-ra-2022-1.sqlite3` for the `2022-1` season.
    * Parameters default to the current year / first month respectively.
    * The configuration parameters can be set as operating system environment variables
      requiring `FLASK_` prefix, i.e.
      * `FLASK_LADDER_SEASONS_START_YEAR` (defaults to current year)
      * `FLASK_LADDER_SEASONS_START_MONTH` (defaults to `1`)
* `LADDER_DEFAULT_SEASON_KEY`: Can be used to override the default season displayed
  when the website is accessed initially. Defaults to `2m` which is the key for the
  currently running 2-month period season. Set to `all` for all-time ranking.

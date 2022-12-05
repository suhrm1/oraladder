#!/usr/bin/env python
#
# Copyright (C) 2020
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import argparse
import datetime
import logging
import os.path as op
import shutil
import sqlite3
from math import ceil
from yaml import dump

from filelock import FileLock, Timeout

from .model import PlayerLookup
from .rankings import ranking_systems
from .utils import get_results, get_profile_ids


def _get_players_outcomes(accounts_db, results, ranking_system):
    ranking = ranking_systems[ranking_system]()
    player_lookup = PlayerLookup(accounts_db, ranking)
    return ranking.compute_ratings_from_series_of_games(results, player_lookup)


def _preprocess_period(args):
    """Forms CLI arguments "period", "start", and "end" into a dictionary

    Possible combinations:
        - period in {1m, 2m}, start and end missing: returns the 1 or 2 month period
        - period is any string, start an ISO format date string, end missing:
          returns the period from start date to "now" (actually, "tomorrow")
        - period is any string, start and end are ISO format date strings:
          returns the period from start to end date

    Returns a dict with elements, "name" (str), "start", "end" (datetime.date)
    """
    today = datetime.date.today()
    if args.start:
        start = datetime.date.fromisoformat(args.start)
        if args.end:
            end = datetime.date.fromisoformat(args.end)
        else:
            end = today + datetime.timedelta(days=1)
    else:
        if args.period == "1m":
            start = datetime.date(today.year, today.month, 1)
        elif args.period == "2m":
            start_month = ((today.month - 1) & ~1) + 1
            start = datetime.date(today.year, start_month, 1)
        else:
            start = datetime.date(year=1990, month=1, day=1)
        end = today + datetime.timedelta(days=1)
    return {"name": args.period, "start": start, "end": end}


def _main(args):
    conn = sqlite3.connect(args.database)

    c = conn.cursor()

    # We don't know if the new submitted replays will be properly ordered, so
    # all the information needs to be reconstructed
    c.execute("DROP TABLE IF EXISTS players")
    c.execute("DROP TABLE IF EXISTS outcomes")

    with open(args.schema) as f:
        c.executescript(f.read())

    # Re-use the cached OpenRA account information to prevent stressing too
    # much the service
    request_accounts = c.execute("SELECT * FROM accounts")
    accounts_db = {fp: (pid, pname, avatar_url) for fp, pid, pname, avatar_url in request_accounts.fetchall()}

    period_dict = _preprocess_period(args)
    results = get_results(accounts_db, args.replays, period_dict)

    players, outcomes = _get_players_outcomes(accounts_db, results, args.ranking)

    if args.bans_file:
        banned_profiles = get_profile_ids(args.bans_file)
        for player in players:
            player.banned = player.profile_id in banned_profiles

    outcomes_sql = [o.sql_row for o in outcomes]
    players_sql = [p.sql_row for p in players]
    accounts_sql = [(fp, acc[0], acc[1], acc[2]) for fp, acc in accounts_db.items() if acc is not None]

    c.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?,?)", accounts_sql)
    c.executemany("INSERT OR IGNORE INTO players VALUES (?,?,?,?,?,?,?,?)", players_sql)
    c.executemany("INSERT OR IGNORE INTO outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", outcomes_sql)

    conn.commit()
    conn.close()


def run():
    logging.basicConfig(level="INFO")
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--database", default="db.sqlite3")
    parser.add_argument("-s", "--schema", default=op.join(op.dirname(__file__), "ladder.sql"))
    parser.add_argument("-r", "--ranking", choices=ranking_systems.keys(), default="trueskill")
    parser.add_argument("-p", "--period")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--bans-file")
    parser.add_argument("-l", "--log-level", default="WARNING")
    parser.add_argument("replays", nargs="*")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    lockfile = args.database + ".lock"
    lock = FileLock(lockfile, timeout=1)
    try:
        with lock:
            _main(args)
    except Timeout:
        logging.error("Another instance of this application currently holds the %s lock file.", lockfile)


def initialize_periodic_databases():
    """A CLI tool to create multiple database files in batch

    In the current implementation, this is customized to support 2-months-periods as used by the oraladder.net website.
    For a given timespan based on "year" and "start-month" parameters, SQLite database files get created. Each DB file
    contains data for a 2-month period starting with every 2nd month of a year (i.e. January, March, May, ...) which
    will be named following the pattern db-{year}-{nr}.sqlite3 where {nr} is an integer counter starting with 1 for the
    Jan-Feb period going up to 6 for the Nov-Dec period of the given year.

    If invoked with a start month that does not mark the beginning of one of these periods, it will get corrected by
    subtracting one month so that the resulting DB files will be true to the defined format/content.

    For less customized database file creation, refer to the `ora-ladder` CLI tool utilizing "start" and "end"
    parameters.
    """
    parser = argparse.ArgumentParser(
        description="OpenRA Ladder system database helper tool. This CLI provides a wrapper around the `ora-ladder` "
        "tool that generates SQLite database files from OpenRA game replays located in a source folder. "
        "'ora-dbtool' allows you to generate multiple database files in batch by defining year and "
        "starting month. Output files will be structured into 2-months periods according to the usage on "
        "the https://oraladder.net Ladder website."
    )
    parser.add_argument("-s", "--schema", default=op.join(op.dirname(__file__), "ladder.sql"))
    parser.add_argument("-r", "--ranking", choices=ranking_systems.keys(), default="trueskill")
    parser.add_argument("--bans-file")
    parser.add_argument("-m", "--mod", default="ra")
    parser.add_argument("-y", "--year", type=int, default=datetime.date.today().year)
    parser.add_argument("--start-month", type=int, default="1", help="Number between 1 and 12")
    parser.add_argument(
        "-l", "--log-level", default="WARNING", help="Specify log level (in capital letters), default is WARNING."
    )
    parser.add_argument(
        "--yaml",
        action="store_true",
        help="If flag is present, metadata about the generated database files will be dumped in YAML format. "
        "Default output file is databases.yml in working directory. Set --yaml-file argument to override "
        "output path.",
    )
    parser.add_argument(
        "--yaml-file",
        type=str,
        help="If set, YAML metadata about generated database files is dumped into the specified file. Defaults to "
        "databases.yml in working directory.",
    )
    parser.add_argument("replays", nargs="*")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    # Correct to previous month for even-numbered months (February, April, ...)
    start_month = args.start_month - (args.start_month & 1 == 0)

    start_date = datetime.date(year=args.year, month=start_month, day=1)
    season_counter = ceil(start_month / 2)
    prev_db_name = None

    # Handle YAML metadata output arguments
    if args.yaml or args.yaml_file is not None:
        dump_yaml = True
        yaml_file = "databases.yml" if args.yaml_file is None else args.yaml_file
        yaml_data = []
    else:
        dump_yaml = False

    while True:
        # calculate the seasons end date (start + 2 months - 1 day)
        end_date = datetime.date(start_date.year, (start_date.month + 2) % 12, start_date.day)
        # in case we have reached January again, update year
        if end_date.month == 1:
            end_date = end_date.replace(year=end_date.year + 1)
        end_date -= datetime.timedelta(days=1)

        # prepare arguments for creating the actual database files
        db_name = f"db-{args.mod}-{start_date.year}-{season_counter}.sqlite3"

        # If the first database from the batch has already been created, copy that to use it as a base for the
        # next iteration; this reduces API calls to the OpenRA user account service
        if prev_db_name is not None:
            shutil.copyfile(prev_db_name, db_name)
            logging.info(f"Copied {prev_db_name} to {db_name}")

        # Track database filename for next iteration
        prev_db_name = db_name

        lockfile = db_name + ".lock"
        args.start = str(start_date)
        args.end = str(end_date)
        args.database = db_name
        args.period = ""

        # create the actual database files using _main() method
        try:
            with FileLock(lockfile, timeout=1):
                _main(args)
                logging.info(
                    f"Created database file {db_name} using "
                    f"start date {start_date}, end date {end_date}, source "
                    f"folder {args.replays}."
                )
                if dump_yaml:
                    # collect database metadata for YAML output
                    yaml_data.append(
                        dict(
                            id=f"{start_date.year}-{season_counter}",
                            mod=args.mod,
                            title=f"{start_date.year}-{season_counter}",
                            database_file=db_name,
                            start=start_date,
                            end=end_date,
                        )
                    )

        except Timeout:
            logging.error("Another instance of this application currently holds the %s lock file.", lockfile)

        #
        start_date = start_date.replace(month=(start_date.month + 2) % 12)
        season_counter += 1

        # stop the loop if we completed a year or if the start date is in the future
        if start_date.month == 1 or start_date > datetime.date.today():
            break

    if dump_yaml:
        # Write YAML metadata to file
        logging.info(f"Dumping database YAML information into {yaml_file}")
        with open(yaml_file, "w") as f:
            dump(yaml_data, stream=f)
        logging.debug(f"YAML database information:\n{dump(yaml_data)}")

# Red Alert Global League website

## Configuration

App configuration is read from a Python configuration file located at
`instance/ragl_config.py` by default. The source filename can be overwritten
by setting OS environment variable `RAGL_CONFIG`.

Check out the contents of [the default config file](../misc/ragl_config.py for a full
example of the possible configuration variables.

### Display announcements on start page

One or multiple announcements can be read from a YAML file and be displayed on the
start page ("scoreboards") of the website. Default path for the file is
`instance/announcements.yaml`.

Filename can be overwritten by setting the OS environment variable
`FLASK_ANNOUNCEMENTS_YAML_FILE` or defining `ANNOUNCEMENTS_YAML_FILE` in the
configuration Python file.

### Player strikes

Strikes are maintained in the season configuration file processed by `ora-ragl`
(see `laddertools/ragl-s18.yml`). The website reads them from the generated
SQLite database and displays them on the scoreboard and player pages.

The number of strikes required for automatic disqualification is configured with
`STRIKE_LIMIT` in the website configuration (default: `3`) and `Strike_Limit` in
the season YAML (default: `3`). A disqualified player receives the `SF` status
and is removed from the regular ranking.

All new YAML sections are optional. Existing season files without `Strikes`,
`Strike_Limit`, or `Replay_Overrides` continue to work unchanged: they use no
strikes and the default strike limit of `3`.

### Replay player ID overrides

Individual replay files can override the OpenRA profile ID resolved for a player.
Overrides are configured per replay in the season YAML:

```yaml
Replay_Overrides:
    "2026-11-01T20-15-00.orarep":
        - [ "PlayerName", 12345 ]
        - [ "player1", 67890 ]
```

The replay key may be an absolute path or a basename. Selectors may be a player
display name, fingerprint, `winner`/`loser`, `player0`/`player1`, or `0`/`1`.
For unauthenticated replay players there is no fingerprint, so use the player
display name as the selector.

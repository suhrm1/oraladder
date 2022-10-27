# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security

## [2.0.0] - (date tbd)

### Added
- Introduced changelog and bumped version to `2.0.0`. While this is not a release with any breaking changes, change in project organization and the number of changes since what was the initial production release merit a major release.
- Added `start` and `end` parameters to `ora-ladder` CLI to enable database file creation for specific timeframes
- Added CLI tool `ora-dbtool` to generate multiple 2-month-period database files in batch (basically a wrapper around the existing `ora-ladder` CLI)
- Added configuration parameters to control behaviour of `ladderweb` website, see subproject [README file](ladderweb/README.md).
- Added new `ladderweb` UI features:
  - Added CSS/JS based UI support for responsive navbar
  - Added exposition texts to `leaderboard` [template file](ladderweb/templates/leaderboard.html)
  - Added history of player rankings across seasons to `player` page

### Changed
- Refactored handling of database selection in the `ladderweb` subproject to allow for a dynamic number of 2-month-period databases


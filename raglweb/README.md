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
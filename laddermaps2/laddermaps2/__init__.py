"""laddermaps2 — Build ladder map packs for oraladder.net.

Subcommands
-----------
laddermaps2   (via cli.py)
    Full pipeline: download balance patch → resolve source maps →
    generate overlay → patch & repack → optional --check-yaml.
upload-maps   (via upload_maps.py)
    Upload finished .oramap packs to resource.openra.net.
"""

"""External resource URLs used by the build pipeline.

All values are format strings; callers substitute ``{tag}`` or
``{map_id}`` at runtime.
"""

#: GitHub archive URL for the ora-balance-iteration repository.
BALPATCH_URL = "https://github.com/tttppp/ora-balance-iteration/archive/refs/tags/{tag}.zip"

#: Path *inside* the zip archive where the .yaml rules live.
SRC_PREFIX = "ora-balance-iteration-{tag}/src/"

#: OpenRA Resource Center direct map download endpoint.
MAP_URL = "https://resource.openra.net/maps/{map_id}/oramap"

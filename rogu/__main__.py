import sys

# New 3.8 features used:
#   - the walrus operator
#   - mimetypes.guess_type path-like support
#
# Arrow requires >= 3.6
# Click requires >= 3.7
# Jinja2 requires >= 3.7
# PyYAML requires >= 3.6
# Requests requires >= 3.7
#
if sys.version_info < (3, 8):
    sys.exit("Python 3.8 or higher is required.")

# Add location of third party libraries to sys.path
sys.path.insert(1, f'{sys.path[0]}/thirdparty')

import cli
import ui
from errors import AppError

try:
    cli.cli()
except AppError as e:
    ui.err(e)
    sys.exit(1)

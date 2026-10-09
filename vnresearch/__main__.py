# Configure log encoding before importing the CLI, FastAPI or optional SDKs.
from .console import configure_utf8_stdio

configure_utf8_stdio()

from .cli import main

main()

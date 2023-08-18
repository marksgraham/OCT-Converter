"""Init module."""
from importlib import metadata

from pydicom.uid import generate_uid

version = metadata.version("oct_converter")

# Deterministic implentation UID based on package name and version
implementation_uid = generate_uid(entropy_srcs=["oct_converter", version])

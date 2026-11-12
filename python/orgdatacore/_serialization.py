"""Internal serialization: Data model -> dict.

Not part of the public API. Used by test helpers to round-trip typed Data
through a plain dict without raw dict manipulation.

The canonical ``orgindex-schema`` models mirror the on-disk index exactly, so
``model_dump`` reproduces the index shape directly — no hand-written per-model
serializers are needed.
"""

from typing import Any

from ._types import Data


def data_to_dict(data: Data) -> dict[str, Any]:
    """Convert Data to a JSON-serializable dict in the on-disk index shape."""
    return data.model_dump(mode="json")

from typing import Protocol


class CloudMaskProvider(Protocol):
    """Small provider contract; providers must never silently fall back."""

    name: str

    def process(self, *args, **kwargs):
        ...
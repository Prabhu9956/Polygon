from django.conf import settings
from .base import StorageBackend


def get_storage() -> StorageBackend:
    provider = settings.STORAGE_PROVIDER
    if provider == "gcs":
        from .gcs import GCSBackend
        return GCSBackend()
    raise ValueError(f"Unknown STORAGE_PROVIDER: {provider!r}")
import logging

from django.conf import settings
from google.cloud import storage
from google.oauth2 import service_account

from .base import StorageBackend

logger = logging.getLogger(__name__)


class GCSBackend(StorageBackend):
    def __init__(self):
        if not settings.GCS_BUCKET_NAME:
            raise RuntimeError("GCS_BUCKET_NAME is not set in .env")
        if settings.GCS_CREDENTIALS_FILE:
            creds = service_account.Credentials.from_service_account_file(
                settings.GCS_CREDENTIALS_FILE
            )
            self.client = storage.Client(
                project=settings.GCS_PROJECT_ID or creds.project_id,
                credentials=creds,
            )
        else:
            self.client = storage.Client(project=settings.GCS_PROJECT_ID or None)
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)

    def upload(self, key, data):
        self.bucket.blob(key).upload_from_string(data, content_type="text/plain")
        logger.info("Uploaded %s", key)

    def exists(self, key):
        return self.bucket.blob(key).exists()

    def delete_prefix(self, prefix):
        blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
        for blob in blobs:
            blob.delete()
        logger.info("Deleted %d objects under %s", len(blobs), prefix)
        return len(blobs)
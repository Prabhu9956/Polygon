from django.conf import settings
from google.cloud import storage
from google.oauth2 import service_account

from .base import StorageBackend


class GCSBackend(StorageBackend):
    def __init__(self):
        if settings.GCS_CREDENTIALS_FILE:
            creds = service_account.Credentials.from_service_account_file(
                settings.GCS_CREDENTIALS_FILE
            )
            self.client = storage.Client(
                project=settings.GCS_PROJECT_ID or creds.project_id,
                credentials=creds,
            )
        else:
            # Falls back to Application Default Credentials
            self.client = storage.Client(project=settings.GCS_PROJECT_ID or None)
        self.bucket = self.client.bucket(settings.GCS_BUCKET_NAME)

    def upload(self, key, data):
        self.bucket.blob(key).upload_from_string(data, content_type="text/plain")

    def exists(self, key):
        return self.bucket.blob(key).exists()

    def delete_prefix(self, prefix):
        blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
        if blobs:
            self.bucket.delete_blobs(blobs)
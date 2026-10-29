from abc import ABC, abstractmethod


def input_key(db_problem_id, test_number) -> str:
    return f"test_cases/{db_problem_id}/{int(test_number):02d}"


def output_key(db_problem_id, test_number) -> str:
    return f"test_cases/{db_problem_id}/{int(test_number):02d}.a"


def _to_bytes(value) -> bytes:
    if value is None:
        return b""
    return value if isinstance(value, bytes) else str(value).encode("utf-8")


class StorageBackend(ABC):
    """Provider-agnostic storage. Providers implement only upload/exists/delete_prefix."""

    @abstractmethod
    def upload(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete_prefix(self, prefix: str) -> int:
        """Delete every object under prefix. Returns the number deleted."""

    # Same names as the old AzureBlobManager, minus container_name
    def upload_test_case(self, db_problem_id, test_number, input_data, output_data):
        self.upload(input_key(db_problem_id, test_number), _to_bytes(input_data))
        self.upload(output_key(db_problem_id, test_number), _to_bytes(output_data))

    def empty_blob(self, db_problem_id) -> int:
        return self.delete_prefix(f"test_cases/{db_problem_id}/")
"""Shared error type for KC + Quiz package contract validation."""


class KcQuizContractError(Exception):
    def __init__(self, code: str, message: str, ref: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.ref = ref

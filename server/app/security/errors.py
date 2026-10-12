from dataclasses import dataclass


@dataclass
class ServiceError(Exception):
    stage: str
    error_code: str
    user_message: str
    technical_message: str = ""
    retryable: bool = False

    def __str__(self) -> str:
        return self.user_message

    def public_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "error_code": self.error_code,
            "user_message": self.user_message,
            "retryable": self.retryable,
        }

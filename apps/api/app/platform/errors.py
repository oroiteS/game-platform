from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformError(Exception):
    code: str
    message: str
    status_code: int = 400


def error_response(error: PlatformError) -> tuple[dict[str, dict[str, str]], int]:
    return {"error": {"code": error.code, "message": error.message}}, error.status_code

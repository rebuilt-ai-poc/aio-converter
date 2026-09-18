"""Domain exceptions and their HTTP status codes."""
from __future__ import annotations


class ConverterError(Exception):
    """Base class. `code` is a stable machine-readable slug shown to clients."""

    code = "CONVERTER_ERROR"
    http_status = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class UnsupportedFormatError(ConverterError):
    code = "UNSUPPORTED_FORMAT"
    http_status = 400


class InvalidFileError(ConverterError):
    code = "INVALID_FILE"
    http_status = 400


class InvalidOptionsError(ConverterError):
    code = "INVALID_OPTIONS"
    http_status = 400


class FileTooLargeError(ConverterError):
    code = "FILE_TOO_LARGE"
    http_status = 413


class DependencyMissingError(ConverterError):
    code = "DEPENDENCY_MISSING"
    http_status = 503


class ConversionError(ConverterError):
    code = "CONVERSION_FAILED"
    http_status = 500


class ConversionTimeoutError(ConverterError):
    code = "CONVERSION_TIMEOUT"
    http_status = 504

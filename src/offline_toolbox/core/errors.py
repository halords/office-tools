"""Core domain errors for Offline Toolbox."""

from typing import Optional


class ToolboxError(Exception):
    """Base class for all application domain errors."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ValidationError(ToolboxError):
    """Raised when input parameters or files fail validation checks."""
    pass


class DocumentError(ToolboxError):
    """Raised when a document is corrupted, password-protected, or unreadable."""
    pass


class EncryptedDocumentError(DocumentError):
    """Raised when an encrypted document requires a password."""
    pass


class ImageProcessingError(ToolboxError):
    """Raised when image processing or conversion fails."""
    pass


class OutputVerificationError(ToolboxError):
    """Raised when post-operation document verification fails."""
    pass


class StorageError(ToolboxError):
    """Raised when disk space is insufficient or permission is denied."""
    pass

"""Core domain models and data structures."""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional


class DocumentType(Enum):
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ImageFormat(Enum):
    JPEG = "JPEG"
    PNG = "PNG"
    WEBP = "WEBP"
    BMP = "BMP"
    TIFF = "TIFF"
    ICO = "ICO"


class CompressionPreset(Enum):
    MAXIMUM_QUALITY = "max_quality"
    BALANCED = "balanced"
    SMALL_FILE = "small_file"
    CUSTOM = "custom"


class JobStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class PageInfo:
    page_number: int  # 1-indexed
    width: float
    height: float
    rotation: int  # 0, 90, 180, 270


@dataclass(frozen=True)
class PDFMetadata:
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    is_encrypted: bool = False
    file_size_bytes: int = 0


@dataclass
class JobDescriptor:
    job_id: str
    operation: str
    input_files: List[Path]
    output_target: Optional[Path]
    options: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    status_message: str = ""
    error_message: Optional[str] = None
    result_files: List[Path] = field(default_factory=list)

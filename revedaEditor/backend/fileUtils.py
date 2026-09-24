"""Shared file-system helpers for application boundaries."""

import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, TextIO


def safeExtractZip(zipFile: zipfile.ZipFile, destination: Path) -> None:
    """Extract an archive only when every member stays under destination."""
    destination = destination.resolve()
    for member in zipFile.infolist():
        archiveName = member.filename.replace("\\", "/")
        posixName = PurePosixPath(archiveName)
        windowsName = PureWindowsPath(archiveName)
        if (posixName.is_absolute() or windowsName.is_absolute()
                or windowsName.drive or ".." in posixName.parts):
            raise ValueError(f"Unsafe archive member path: {member.filename}")

        target = (destination / Path(*posixName.parts)).resolve()
        try:
            target.relative_to(destination)
        except ValueError as error:
            raise ValueError(
                f"Unsafe archive member path: {member.filename}") from error

    zipFile.extractall(path=destination)


def atomicWriteText(path: Path, writeContent: Callable[[TextIO], None]) -> None:
    """Write text to a temporary sibling and replace path atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tempPath: Path | None = None
    try:
        fd, tempName = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        tempPath = Path(tempName)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            writeContent(output)
            output.flush()
            os.fsync(output.fileno())
        tempPath.replace(path)
    finally:
        if tempPath is not None and tempPath.exists():
            tempPath.unlink()
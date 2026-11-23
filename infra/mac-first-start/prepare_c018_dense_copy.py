"""Prepare a byte-identical staged Qdrant tree for the pinned runner's copytree."""

import argparse
import hashlib
from pathlib import Path
import shutil
import stat
import tempfile


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").digest()


def prepare(source, target):
    source = source.resolve(strict=True)
    target = target.absolute()
    if not source.is_dir() or target.exists() or target.is_symlink():
        raise ValueError("Expected a source directory and a fresh target")
    if target.resolve().is_relative_to(source):
        raise ValueError("The target must be outside the source")
    if any(entry.is_symlink() for entry in source.rglob("*")):
        raise ValueError("The staged source must not contain symbolic links")

    with tempfile.TemporaryDirectory(prefix=".c018-dense-", dir=target.parent) as work:
        staged = Path(work) / "dense"
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns(".lock"))
        for entry in (staged, *staged.rglob("*")):
            if entry.is_dir():
                # copytree preserves source permissions. Qdrant must be able
                # to create its lock in the resulting private runtime copy.
                entry.chmod(stat.S_IMODE(entry.stat().st_mode) | stat.S_IWUSR)
            elif entry.is_file():
                entry.chmod(stat.S_IMODE(entry.stat().st_mode) | stat.S_IWUSR)
                if digest(entry) != digest(source / entry.relative_to(staged)):
                    raise ValueError("Dense copy byte verification failed")
            else:
                raise ValueError("Unsupported entry in dense copy")
        staged.rename(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.target)
    print("C018_DENSE_COPY_VERIFIED")

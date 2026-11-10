"""Shared absent-file filesystem primitives; no host configuration policy."""
import hashlib
import os
import stat


def fingerprint(path):
    metadata = path.lstat()
    result = {"device": metadata.st_dev, "inode": metadata.st_ino,
              "mode": stat.S_IMODE(metadata.st_mode)}
    if path.is_symlink():
        result.update(type="symlink", target=os.readlink(path))
    elif path.is_file():
        result.update(type="file", sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    else:
        raise ValueError(f"Expected file or link: {path}")
    return result


def no_link_parents(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f"Refusing to write through directory symlink: {parent}")
        if parent.exists() and not parent.is_dir():
            raise ValueError(f"Not a directory: {parent}")


def write_new(path, text):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    metadata = os.fstat(descriptor)
    with os.fdopen(descriptor, "w") as output:
        output.write(text)
    # A concurrent app replacement must never become setup-owned through a
    # later pathname lookup. Bind the created inode and intended bytes instead.
    return {"device": metadata.st_dev, "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode), "type": "file",
            "sha256": hashlib.sha256(text.encode()).hexdigest()}


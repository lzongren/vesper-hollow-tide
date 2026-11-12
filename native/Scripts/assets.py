#!/usr/bin/env python3
"""Fetch or verify the reviewed, pinned CC0 environment sources.

No Unreal/Epic content is downloaded by this tool. Raw art stays outside Git;
the lockfile records provenance and the provider's file digests. The resulting
receipt proves file integrity, not visual quality or successful engine import.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen

NATIVE = Path(__file__).resolve().parents[1]
LOCKFILE = NATIVE / "Art" / "assets.lock.json"
ALLOWED_HOSTS = {"dl.polyhaven.org"}


def safe_path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if (not relative or path.is_absolute() or ".." in path.parts
            or "\\" in relative or ":" in relative or "\x00" in relative):
        raise ValueError(f"Unsafe asset path: {relative!r}")
    destination = (root / path).resolve()
    if not destination.is_relative_to(root.resolve()):
        raise ValueError(f"Asset path escapes destination: {relative!r}")
    return destination


def validate_lock(lock: dict) -> None:
    if lock.get("version") != 1 or not lock.get("assets"):
        raise ValueError("Unsupported or empty asset lock")
    ids: set[str] = set()
    for asset in lock["assets"]:
        aid = asset["id"]
        if not re.fullmatch(r"[A-Za-z0-9_]+", aid) or aid in ids:
            raise ValueError(f"Invalid or duplicate asset id: {aid}")
        ids.add(aid)
        if asset["license"] != "CC0-1.0":
            raise ValueError(f"Unreviewed asset license: {aid}")
        paths = set()
        for file in asset["files"]:
            safe_path(Path("/asset-validation"), file["path"])
            if file["path"] in paths:
                raise ValueError(f"Duplicate file path in {aid}")
            paths.add(file["path"])
            url = urlsplit(file["url"])
            if (url.scheme != "https" or url.hostname not in ALLOWED_HOSTS
                    or url.username or url.password or url.port not in (None, 443)):
                raise ValueError(f"Unreviewed download origin: {aid}")
            if type(file["bytes"]) is not int or not 0 < file["bytes"] < 2_000_000_000:
                raise ValueError(f"Invalid file size: {aid}/{file['path']}")
            if not re.fullmatch(r"[0-9a-f]{32}", file["md5"]):
                raise ValueError(f"Invalid digest: {aid}/{file['path']}")
        if asset["entry"] not in paths:
            raise ValueError(f"Missing entry point: {aid}")


def digests(path: Path) -> tuple[str, str, int]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest(), size


def matches(path: Path, expected: dict) -> bool:
    if not path.is_file() or path.stat().st_size != expected["bytes"]:
        return False
    return digests(path)[0] == expected["md5"]


def fetch_file(root: Path, asset: dict, file: dict, verify_only: bool) -> dict:
    relative = f"{asset['id']}/{file['path']}"
    target = safe_path(root, relative)
    if not matches(target, file):
        if verify_only:
            raise ValueError(f"Missing or corrupt asset: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Unique temporary names permit interrupted attempts without promoting
        # partial files. Existing verified content is never overwritten early.
        fd, temporary = tempfile.mkstemp(prefix=".download-", dir=target.parent)
        try:
            request = Request(file["url"], headers={"User-Agent": "Vesper-Native-Assets/0.2"})
            with os.fdopen(fd, "wb") as output, urlopen(request, timeout=90) as source:
                final_url = urlsplit(source.url)
                if final_url.scheme != "https" or final_url.hostname not in ALLOWED_HOSTS:
                    raise ValueError("Download redirected to an unreviewed origin")
                total = 0
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(chunk)
                    if total > file["bytes"]:
                        raise ValueError(f"Download exceeds pinned size: {relative}")
                    output.write(chunk)
            if not matches(Path(temporary), file):
                raise ValueError(f"Download integrity check failed: {relative}")
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    md5, sha, size = digests(target)
    return {"path": relative, "bytes": size, "md5": md5, "sha256": sha}


def validate_gltf(root: Path, asset: dict) -> dict:
    directory = safe_path(root, asset["id"])
    entry = safe_path(directory, asset["entry"])
    model = json.loads(entry.read_text())
    if model.get("asset", {}).get("version") != "2.0":
        raise ValueError(f"Unsupported glTF version: {asset['id']}")
    declared = {f["path"] for f in asset["files"]}
    for item in model.get("buffers", []) + model.get("images", []):
        uri = item.get("uri")
        if not uri:
            continue  # Embedded buffer views are allowed by glTF.
        uri = unquote(uri)
        if urlsplit(uri).scheme or uri.startswith("//"):
            raise ValueError(f"glTF references a remote resource: {uri}")
        safe_path(directory, uri)
        if uri not in declared:
            raise ValueError(f"Unpinned glTF dependency: {asset['id']}/{uri}")
        if not safe_path(directory, uri).is_file():
            raise ValueError(f"Missing glTF dependency: {uri}")
    return {"id": asset["id"], "entry": f"{asset['id']}/{asset['entry']}",
            "meshes": [m.get("name", f"mesh_{i}") for i, m in enumerate(model.get("meshes", []))],
            "nodes": len(model.get("nodes", [])), "materials": len(model.get("materials", []))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=NATIVE / "SourceAssets")
    parser.add_argument("--lock", type=Path, default=LOCKFILE)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--asset", action="append", help="Restrict to specific reviewed asset IDs")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be between 1 and 8")
    raw = args.lock.read_bytes()
    lock = json.loads(raw)
    validate_lock(lock)
    selected = set(args.asset or [a["id"] for a in lock["assets"]])
    assets = [a for a in lock["assets"] if a["id"] in selected]
    if {a["id"] for a in assets} != selected:
        parser.error("Unknown asset ID; add and review it in the lockfile first")
    root = args.root.resolve()
    files = [(a, f) for a in assets for f in a["files"]]
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(fetch_file, root, a, f, args.verify_only) for a, f in files]
        for i, job in enumerate(concurrent.futures.as_completed(jobs), 1):
            record = job.result()
            records.append(record)
            print(f"[{i}/{len(files)}] verified {record['path']}", flush=True)
    inventory = [validate_gltf(root, asset) for asset in assets]
    receipt = {"version": 1, "lock_sha256": hashlib.sha256(raw).hexdigest(),
               "scope": "Source file integrity only; not engine import or visual acceptance",
               "assets": inventory, "files": sorted(records, key=lambda r: r["path"])}
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / "receipt.json"
    fd, temporary = tempfile.mkstemp(prefix=".receipt-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, receipt_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"Verified {len(assets)} assets, {len(records)} files. Receipt: {receipt_path}")


if __name__ == "__main__":
    main()

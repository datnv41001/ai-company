"""Verify the frozen study from its checked-in evidence, without invoking a provider."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from matching import compare
from score import read, score


def verify(study: Path):
    manifest = read(study / "RECEIPTS.json")
    source = study / "DEPARTMENT-RECEIPTS.zip"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["archive_file_sha256"]
    root = study.parents[2]
    for relative, expected in manifest["fixture_files_sha256"].items():
        # Git autocrlf may change checked-out text on Windows.
        payload = (root / relative).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(payload).hexdigest() == expected, relative
    with TemporaryDirectory() as scratch, ZipFile(source) as archive:
        output = Path(scratch)
        assert len(archive.namelist()) == manifest["archive_file_count"]
        assert set(archive.namelist()) == set(manifest["per_file_sha256"])
        for name in archive.namelist():
            destination = (output / name).resolve()
            assert destination.is_relative_to(output.resolve())
            payload = archive.read(name)
            assert hashlib.sha256(payload).hexdigest() == manifest["per_file_sha256"][name], name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        assert score(output) == read(output / "summary.json")
        assert compare(output) == read(output / "matching.json")
    print(f"Verified {manifest['archive_file_count']} files, model invocations, package provenance and paired conditions.")


if __name__ == "__main__":
    verify(Path("docs/evaluation/department-study").resolve())

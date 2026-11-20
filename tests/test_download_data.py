from scripts.download_data import (
    ARCHIVE,
    ARCHIVE_SHA256,
    CSV,
    CSV_SHA256,
    file_sha256,
)


def test_local_official_dataset_matches_documented_hashes():
    if not ARCHIVE.exists() or not CSV.exists():
        return
    assert file_sha256(ARCHIVE) == ARCHIVE_SHA256
    assert file_sha256(CSV) == CSV_SHA256

"""Download and verify the public Jersey City Citi Bike April 2026 dataset."""

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
ARCHIVE = RAW_DIR / "JC-202604-citibike-tripdata.zip"
CSV = RAW_DIR / "JC-202604-citibike-tripdata.csv"
URL = "https://s3.amazonaws.com/tripdata/JC-202604-citibike-tripdata.zip"
ARCHIVE_SHA256 = "bb9e73212280a0106f3deb576363c413dff1ff0b474ff7194059c07476fb07bf"
CSV_SHA256 = "70302c0a123b14e504b9670dae4ce602a4179be0197ee7eabb47d11a15a4aa7d"


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Fichier manquant : {path}")
    actual = file_sha256(path)
    if actual != expected:
        raise ValueError(f"SHA-256 invalide pour {path.name}: {actual}")


def download_archive() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    request = Request(URL, headers={"User-Agent": "CitiBike-GNN-Lab-v2/2.0"})
    with urlopen(request, timeout=120) as response, NamedTemporaryFile(
        dir=RAW_DIR, suffix=".zip.tmp", delete=False
    ) as temporary:
        while chunk := response.read(1024 * 1024):
            temporary.write(chunk)
        temporary_path = Path(temporary.name)
    try:
        require_hash(temporary_path, ARCHIVE_SHA256)
        temporary_path.replace(ARCHIVE)
    finally:
        temporary_path.unlink(missing_ok=True)


def extract_csv() -> None:
    with ZipFile(ARCHIVE) as archive:
        members = archive.namelist()
        if members != [CSV.name]:
            raise ValueError(f"Contenu ZIP inattendu : {members}")
        with archive.open(CSV.name) as source, NamedTemporaryFile(
            dir=RAW_DIR, suffix=".csv.tmp", delete=False
        ) as temporary:
            while chunk := source.read(1024 * 1024):
                temporary.write(chunk)
            temporary_path = Path(temporary.name)
    try:
        require_hash(temporary_path, CSV_SHA256)
        temporary_path.replace(CSV)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--verify-only", action="store_true", help="Vérifier les fichiers locaux sans télécharger"
    )
    args = parser.parse_args()
    if not args.verify_only and not ARCHIVE.exists():
        print(f"Téléchargement officiel : {URL}")
        download_archive()
    require_hash(ARCHIVE, ARCHIVE_SHA256)
    if not args.verify_only and not CSV.exists():
        extract_csv()
    require_hash(CSV, CSV_SHA256)
    print(f"Dataset vérifié : {CSV}")


if __name__ == "__main__":
    main()

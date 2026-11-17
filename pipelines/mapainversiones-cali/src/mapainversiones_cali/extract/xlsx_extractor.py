"""
xlsx_extractor.py

Extractor para archivos XLSX almacenados en Amazon S3. El ETL no lee archivos
locales: siempre descarga el archivo desde S3 antes de parsearlo.

"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple

import pandas as pd
from openpyxl import load_workbook

from .base_extractor import BaseExtractor

DEFAULT_PREFIX = "raw"
_LOTE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}

# Cache de la ejecucion: (bucket, key, etag) -> ruta local.
_DOWNLOADS: Dict[Tuple[str, str, str], str] = {}
_TMP_DIR: Optional[str] = None


def cleanup_downloads() -> None:
    """Elimina los archivos descargados durante la ejecucion."""
    global _TMP_DIR
    _DOWNLOADS.clear()
    if _TMP_DIR:
        shutil.rmtree(_TMP_DIR, ignore_errors=True)
        _TMP_DIR = None


atexit.register(cleanup_downloads)


def _tmp_dir() -> str:
    global _TMP_DIR
    if _TMP_DIR is None:
        _TMP_DIR = tempfile.mkdtemp(prefix="mapainversiones_s3_")
    return _TMP_DIR


def resolve_location(details: dict) -> Tuple[str, str]:
    """Devuelve (bucket, key) validando bucket, lote y nombre de archivo."""
    bucket = details.get("bucket") or os.getenv("S3_BUCKET")
    if not bucket:
        raise ValueError("Falta el bucket S3: defina S3_BUCKET o details.bucket.")

    lote = str(details.get("lote") or "").strip()
    if not lote:
        raise ValueError("Falta el periodo/lote (subcarpeta de S3): defina la variable PERIODO.")
    if not _LOTE_RE.match(lote):
        raise ValueError(f"Lote invalido '{lote}': solo letras, numeros, '-' y '_'.")

    filename = str(details.get("path") or "").strip()
    if not filename:
        raise ValueError("Falta details.path con el nombre del archivo XLSX.")
    if "/" in filename or "\\" in filename or filename in {".", ".."}:
        raise ValueError(f"details.path debe ser un nombre de archivo sin carpetas: '{filename}'.")
    if not filename.lower().endswith(".xlsx"):
        raise ValueError(f"Solo se admiten archivos .xlsx en S3: '{filename}'.")

    prefix = details.get("prefix")
    if prefix is None:
        prefix = os.getenv("S3_RAW_PREFIX", DEFAULT_PREFIX)
    key = str(PurePosixPath(str(prefix).strip("/"), lote, filename))
    return bucket, key


def _normalize_col(name: str) -> str:
    """Normaliza nombres de columna a snake_case simple."""
    x = str(name).strip().lower()
    x = unicodedata.normalize("NFD", x)
    x = "".join(ch for ch in x if unicodedata.category(ch) != "Mn")
    x = re.sub(r"[^a-z0-9_]+", "_", x)
    x = re.sub(r"_+", "_", x).strip("_")
    return x or "col"


def detect_header_row(fpath: str, sheet=0, max_check: int = 5) -> int:
    """
    Detecta automaticamente la fila de encabezado en un Excel.
    Estrategia: lee primeras `max_check` filas sin header y elige
    la fila con mayor numero de valores no nulos.
    """
    preview = pd.read_excel(fpath, sheet_name=sheet, header=None, nrows=max_check, dtype=str)
    non_null_counts = preview.notna().sum(axis=1)
    best_row = non_null_counts.idxmax()
    return best_row


class XlsxExtractor(BaseExtractor):
    """Extractor para XLSX en S3 bajo ``<prefix>/<lote>/<path>``."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        if self._client is None:
            import boto3  # import diferido: solo se necesita al usar el extractor

            self._client = boto3.client("s3")
        return self._client

    def _download(self, bucket: str, key: str) -> str:
        from botocore.exceptions import ClientError

        try:
            head = self.client.head_object(Bucket=bucket, Key=key)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in _NOT_FOUND_CODES:
                raise FileNotFoundError(f"No existe s3://{bucket}/{key}") from error
            raise RuntimeError(f"No se pudo consultar s3://{bucket}/{key} ({code}): {error}") from error

        cache_key = (bucket, key, head.get("ETag", ""))
        cached = _DOWNLOADS.get(cache_key)
        if cached and os.path.isfile(cached):
            return cached

        local = os.path.join(_tmp_dir(), hashlib.sha1("|".join(cache_key).encode()).hexdigest() + ".xlsx")
        # Se verifica la version exacta inspeccionada con head_object.
        extra = {"IfMatch": head["ETag"]} if head.get("ETag") else {}
        with open(local, "wb") as handle:
            body = self.client.get_object(Bucket=bucket, Key=key, **extra)["Body"]
            shutil.copyfileobj(body, handle)
        _DOWNLOADS[cache_key] = local
        return local

    @staticmethod
    def _check_sheet(local: str, sheet, label: str) -> None:
        if not isinstance(sheet, str):
            return
        workbook = load_workbook(local, read_only=True)
        try:
            names = workbook.sheetnames
        finally:
            workbook.close()
        if sheet not in names:
            raise ValueError(f"{label}: no existe la hoja '{sheet}'. Hojas disponibles: {names}")

    def validate(self, details: dict) -> None:
        """Comprueba existencia del objeto y de la hoja. No toca la base de datos."""
        bucket, key = resolve_location(details)
        local = self._download(bucket, key)
        self._check_sheet(local, details.get("xlsx_sheet"), f"s3://{bucket}/{key}")

    def extract(self, details: dict) -> List[Dict]:
        bucket, key = resolve_location(details)
        label = f"s3://{bucket}/{key}"
        local = self._download(bucket, key)
        sheet = details.get("xlsx_sheet")
        self._check_sheet(local, sheet, label)

        periodo = details.get("periodo") or details["lote"]
        header = detect_header_row(local, sheet=sheet)
        df = pd.read_excel(local, sheet_name=sheet, header=header, dtype=str)
        df["periodo"] = periodo
        df.columns = [_normalize_col(c) for c in df.columns]

        rows = df.to_dict(orient="records")
        if not rows:
            raise ValueError(f"{label}: la hoja '{sheet}' no contiene filas.")
        return rows

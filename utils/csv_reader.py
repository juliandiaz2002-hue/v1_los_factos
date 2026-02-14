"""Lectura robusta de CSV (encoding, delimitador y aliases)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

from .normalization import normalize_text

ENCODING_CANDIDATES = ("utf-8", "latin-1", "cp1252")
DELIMITER_CANDIDATES = (",", ";", "\t", "|")

HEADER_ALIASES: dict[str, set[str]] = {
    "fecha": {"fecha", "date", "dia"},
    "detalle": {"detalle", "glosa", "descripcion", "descripcin", "concepto", "movimiento"},
    "monto": {"monto", "importe", "cargo", "debe", "valor", "amount"},
    "monto_real": {"monto_real"},
    "categoria": {"categoria", "rubro", "categoria_sugerida"},
    "nota_usuario": {"nota_usuario", "nota", "comentario", "observacion"},
    "unique_key": {"unique_key", "llave_unica", "id_unico"},
}


@dataclass
class CsvParseResult:
    rows: list[dict[str, Any]]
    encoding: str
    delimiter: str
    raw_headers: list[str]


def _detect_encoding(payload: bytes) -> tuple[str, str]:
    last_exc: Exception | None = None
    for encoding in ENCODING_CANDIDATES:
        try:
            text = payload.decode(encoding)
            return encoding, text
        except UnicodeDecodeError as exc:
            last_exc = exc
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"No compatible encoding: {last_exc}")


def _detect_delimiter(sample_text: str) -> str:
    try:
        sniffed = csv.Sniffer().sniff(sample_text[:8000], delimiters=DELIMITER_CANDIDATES)
        if sniffed.delimiter in DELIMITER_CANDIDATES:
            return sniffed.delimiter
    except csv.Error:
        pass

    counts = {candidate: sample_text.count(candidate) for candidate in DELIMITER_CANDIDATES}
    return max(counts, key=counts.get)


def _normalize_header_name(header: str) -> str:
    normalized = normalize_text(header)
    normalized = normalized.replace("_", " ")
    normalized = normalized.strip()
    return normalized


def _to_canonical_header(header: str) -> str:
    normalized = _normalize_header_name(header)
    collapsed = normalized.replace(" ", "")

    for canonical, aliases in HEADER_ALIASES.items():
        if normalized in aliases or collapsed in aliases:
            return canonical
    return normalized.replace(" ", "_")


def parse_csv(payload: bytes) -> CsvParseResult:
    encoding, text = _detect_encoding(payload)
    delimiter = _detect_delimiter(text)

    buffer = io.StringIO(text)
    reader = csv.DictReader(buffer, delimiter=delimiter)
    raw_headers = reader.fieldnames or []

    canonical_headers = {
        original: _to_canonical_header(original)
        for original in raw_headers
    }

    rows: list[dict[str, Any]] = []
    for row in reader:
        normalized_row: dict[str, Any] = {}
        for key, value in row.items():
            if key is None:
                continue
            canonical = canonical_headers.get(key, key)
            existing = normalized_row.get(canonical)
            if existing in {None, ""}:
                normalized_row[canonical] = value
            elif value not in {None, ""}:
                # Keep the first non-empty value for a canonical column to avoid accidental overwrite.
                continue
        rows.append(normalized_row)

    return CsvParseResult(rows=rows, encoding=encoding, delimiter=delimiter, raw_headers=raw_headers)

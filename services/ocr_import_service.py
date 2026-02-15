"""OCR de pantallazos de banco a filas canonicas de ingesta."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from io import BytesIO
import re
from typing import Any

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from utils.hashing import build_unique_key
from utils.logging import get_logger
from utils.normalization import normalize_text, parse_amount

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:  # noqa: BLE001
    RapidOCR = None
    OCR_IMPORT_ERROR = "No se pudo importar rapidocr-onnxruntime (verifica version de Python/dependencias)."
else:
    OCR_IMPORT_ERROR = ""


logger = get_logger("los_factos.ocr_import")

AMOUNT_PATTERN = re.compile(
    r"(?<!\d)(?:[-+]?\s*\$?\s*\d{1,3}(?:[.\s]\d{3})+|[-+]?\s*\$?\s*\d+)(?:,\d{1,2})?(?!\d)"
)
DATE_YMD_PATTERN = re.compile(r"\b(?P<year>\d{4})[/-](?P<month>\d{1,2})[/-](?P<day>\d{1,2})\b")
DATE_DMY_PATTERN = re.compile(r"\b(?P<day>\d{1,2})[/-](?P<month>\d{1,2})(?:[/-](?P<year>\d{2,4}))?\b")
DATE_DAY_MONTH_NAME_PATTERN = re.compile(
    r"\b(?P<day>\d{1,2})\s*(?:de\s+)?"
    r"(?P<month_name>ene(?:ro)?|feb(?:rero)?|mar(?:zo)?|abr(?:il)?|may(?:o)?|jun(?:io)?|"
    r"jul(?:io)?|ago(?:sto)?|sep(?:tiembre)?|oct(?:ubre)?|nov(?:iembre)?|dic(?:iembre)?|"
    r"jan(?:uary)?|apr(?:il)?|aug(?:ust)?|dec(?:ember)?)"
    r"(?:\s*(?:de)?\s*(?P<year>\d{2,4}))?\b",
    re.IGNORECASE,
)
LINE_NOISE_KEYWORDS = {
    "saldo",
    "disponible",
    "total",
    "pagina",
    "pago minimo",
    "fecha de facturacion",
    "fecha de vencimiento",
    "cupo",
    "resumen",
    "factura",
    "anterior",
    "siguiente",
}
MONTH_NAME_MAP = {
    "ene": 1,
    "enero": 1,
    "jan": 1,
    "january": 1,
    "feb": 2,
    "febrero": 2,
    "mar": 3,
    "marzo": 3,
    "apr": 4,
    "april": 4,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "jul": 7,
    "julio": 7,
    "aug": 8,
    "august": 8,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "septiembre": 9,
    "oct": 10,
    "octubre": 10,
    "nov": 11,
    "noviembre": 11,
    "dec": 12,
    "december": 12,
    "dic": 12,
    "diciembre": 12,
}


@dataclass
class OcrCandidateLine:
    text: str
    confidence: float
    image_name: str
    order_index: int


@dataclass
class OcrRejectedLine:
    text: str
    reason: str
    confidence: float
    image_name: str


@dataclass
class OcrExtractionResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    rejected_lines: list[OcrRejectedLine] = field(default_factory=list)
    total_images: int = 0
    total_lines: int = 0
    extracted_rows: int = 0
    average_confidence: float = 0.0


class OcrImportService:
    def __init__(self) -> None:
        self._engine = None

    @property
    def available(self) -> bool:
        return RapidOCR is not None

    @property
    def availability_message(self) -> str:
        if OCR_IMPORT_ERROR:
            return (
                "OCR no disponible. "
                f"{OCR_IMPORT_ERROR} "
                "En Streamlit Cloud usa Python 3.11 y reinicia la app."
            )
        return "OCR no disponible. Instala dependencias de OCR (rapidocr-onnxruntime) y reinicia la app."

    def _get_engine(self):
        if not self.available:
            raise RuntimeError(self.availability_message)
        if self._engine is None:
            self._engine = RapidOCR()
        return self._engine

    def extract_from_images(
        self,
        images: list[tuple[str, bytes]],
        *,
        reference_year: int,
        reference_month: int,
        force_expense: bool = True,
    ) -> OcrExtractionResult:
        engine = self._get_engine()
        all_candidates: list[OcrCandidateLine] = []
        confidence_values: list[float] = []

        for image_name, payload in images:
            variants = self._build_image_variants(payload)
            merged_lines: dict[str, OcrCandidateLine] = {}
            order_counter = 0
            for variant in variants:
                raw_output = engine(variant)
                lines = _raw_output_to_lines(
                    raw_output=raw_output,
                    image_name=image_name,
                    order_offset=order_counter,
                )
                order_counter += len(lines)
                for line in lines:
                    normalized = normalize_text(line.text)
                    if not normalized:
                        continue
                    existing = merged_lines.get(normalized)
                    if existing is None or line.confidence > existing.confidence:
                        merged_lines[normalized] = line

            ordered_lines = sorted(merged_lines.values(), key=lambda value: value.order_index)
            all_candidates.extend(ordered_lines)
            confidence_values.extend([item.confidence for item in ordered_lines if item.confidence > 0])

        rows, rejected = parse_candidate_lines(
            all_candidates,
            reference_year=reference_year,
            reference_month=reference_month,
            force_expense=force_expense,
        )

        avg_conf = float(sum(confidence_values) / len(confidence_values)) if confidence_values else 0.0
        logger.info(
            "OCR extraction completed",
            extra={
                "extra": {
                    "images": len(images),
                    "lines": len(all_candidates),
                    "rows": len(rows),
                    "rejected": len(rejected),
                    "avg_confidence": round(avg_conf, 4),
                }
            },
        )
        return OcrExtractionResult(
            rows=rows,
            rejected_lines=rejected,
            total_images=len(images),
            total_lines=len(all_candidates),
            extracted_rows=len(rows),
            average_confidence=avg_conf,
        )

    @staticmethod
    def _build_image_variants(payload: bytes) -> list[np.ndarray]:
        image = Image.open(BytesIO(payload)).convert("RGB")
        image = ImageOps.exif_transpose(image)

        gray = ImageOps.grayscale(image)
        enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        binary = sharpened.point(lambda px: 255 if px > 150 else 0)

        return [
            np.array(image),
            np.array(sharpened.convert("RGB")),
            np.array(binary.convert("RGB")),
        ]


def parse_candidate_lines(
    lines: list[OcrCandidateLine],
    *,
    reference_year: int,
    reference_month: int,
    force_expense: bool = True,
) -> tuple[list[dict[str, Any]], list[OcrRejectedLine]]:
    parsed_rows: list[dict[str, Any]] = []
    rejected: list[OcrRejectedLine] = []
    seen_unique_keys: set[str] = set()
    bucket_indexes: dict[tuple[str, int], list[int]] = {}
    parsed_meta: list[dict[str, Any]] = []
    current_date_iso: str | None = None

    ordered_lines = sorted(lines, key=lambda item: (item.image_name.lower(), item.order_index))
    for line in ordered_lines:
        raw_text = (line.text or "").strip()
        if not raw_text:
            continue
        normalized_line = normalize_text(raw_text)
        if any(keyword in normalized_line for keyword in LINE_NOISE_KEYWORDS):
            rejected.append(
                OcrRejectedLine(
                    text=raw_text,
                    reason="linea_descartada_por_ruido",
                    confidence=line.confidence,
                    image_name=line.image_name,
                )
            )
            continue

        date_match = _extract_date(raw_text, reference_year=reference_year, reference_month=reference_month)
        if date_match is not None:
            current_date_iso = date_match["iso"]

        amount_match = _extract_amount(raw_text)
        if amount_match is None:
            rejected.append(
                OcrRejectedLine(
                    text=raw_text,
                    reason="monto_no_detectado",
                    confidence=line.confidence,
                    image_name=line.image_name,
                )
            )
            continue

        final_date_iso = date_match["iso"] if date_match is not None else current_date_iso
        if not final_date_iso:
            rejected.append(
                OcrRejectedLine(
                    text=raw_text,
                    reason="fecha_no_detectada",
                    confidence=line.confidence,
                    image_name=line.image_name,
                )
            )
            continue

        detail = raw_text
        detail = detail.replace(amount_match["raw"], " ")
        if date_match is not None:
            detail = detail.replace(date_match["raw"], " ")
        detail = re.sub(r"\s+", " ", detail).strip(" -|:")
        if len(detail) < 3:
            rejected.append(
                OcrRejectedLine(
                    text=raw_text,
                    reason="detalle_no_detectado",
                    confidence=line.confidence,
                    image_name=line.image_name,
                )
            )
            continue

        amount_ui = _normalize_amount_for_ingestion(
            amount_match["raw"],
            force_expense=force_expense,
        )

        try:
            amount_abs, _ = parse_amount(amount_ui)
            unique_key = build_unique_key(
                fecha=date.fromisoformat(final_date_iso),
                detalle_norm=normalize_text(detail),
                monto_abs_clp=amount_abs,
            )
        except Exception:  # noqa: BLE001
            rejected.append(
                OcrRejectedLine(
                    text=raw_text,
                    reason="fila_invalida",
                    confidence=line.confidence,
                    image_name=line.image_name,
                )
            )
            continue

        if unique_key in seen_unique_keys:
            continue
        seen_unique_keys.add(unique_key)

        detail_norm = normalize_text(detail)
        bucket_key = (final_date_iso, int(amount_abs))
        candidate = {
            "fecha": final_date_iso,
            "detalle": detail,
            "monto": amount_ui,
            "categoria": "",
            "nota_usuario": "",
            "es_gasto": "1" if force_expense else "",
            "confianza_ocr": round(float(line.confidence), 3),
            "origen_imagen": line.image_name,
            "linea_ocr": raw_text,
        }

        merged = False
        for idx in bucket_indexes.get(bucket_key, []):
            existing = parsed_meta[idx]
            if not _details_similar(detail_norm, str(existing["detail_norm"])):
                continue
            merged = True
            if float(line.confidence) > float(existing["confidence"]):
                parsed_rows[idx] = candidate
                parsed_meta[idx] = {"detail_norm": detail_norm, "confidence": float(line.confidence)}
            break

        if merged:
            continue

        parsed_rows.append(candidate)
        parsed_meta.append({"detail_norm": detail_norm, "confidence": float(line.confidence)})
        bucket_indexes.setdefault(bucket_key, []).append(len(parsed_rows) - 1)

    return parsed_rows, rejected


def _extract_amount(line_text: str) -> dict[str, Any] | None:
    matches = list(AMOUNT_PATTERN.finditer(line_text))
    filtered_matches = []
    for match in matches:
        raw = match.group(0).strip()
        digits_only = re.sub(r"\D", "", raw)
        has_currency = "$" in raw
        has_grouping = "." in raw or "," in raw
        if not has_currency and not has_grouping and len(digits_only) < 3:
            continue
        filtered_matches.append(match)
    if not filtered_matches:
        return None
    selected = filtered_matches[-1]
    return {
        "raw": selected.group(0).strip(),
        "start": selected.start(),
        "end": selected.end(),
    }


def _extract_date(line_text: str, *, reference_year: int, reference_month: int) -> dict[str, str] | None:
    line = line_text.strip()

    for pattern in (DATE_YMD_PATTERN, DATE_DMY_PATTERN):
        match = pattern.search(line)
        if not match:
            continue
        groups = match.groupdict()
        day = int(groups["day"])
        month = int(groups["month"])
        year_raw = groups.get("year")
        if not year_raw:
            year = int(reference_year)
        else:
            year = int(year_raw)
            if year < 100:
                year = 2000 + year
        try:
            parsed = date(year, month, day)
        except ValueError:
            continue
        return {"iso": parsed.isoformat(), "raw": match.group(0)}

    month_name_match = DATE_DAY_MONTH_NAME_PATTERN.search(line)
    if month_name_match:
        day = int(month_name_match.group("day"))
        month_name = normalize_text(month_name_match.group("month_name"))
        month = MONTH_NAME_MAP.get(month_name)
        if month:
            year_raw = month_name_match.group("year")
            year = int(reference_year if not year_raw else int(year_raw))
            if year < 100:
                year = 2000 + year
            try:
                parsed = date(year, month, day)
            except ValueError:
                parsed = None
            if parsed:
                return {"iso": parsed.isoformat(), "raw": month_name_match.group(0)}

    day_only = re.search(r"^\s*(?P<day>\d{1,2})(?:\s+|$)", line)
    if day_only and reference_month:
        day = int(day_only.group("day"))
        try:
            parsed = date(int(reference_year), int(reference_month), day)
        except ValueError:
            return None
        return {"iso": parsed.isoformat(), "raw": day_only.group(0)}
    return None


def _normalize_amount_for_ingestion(raw_amount: str, *, force_expense: bool) -> str:
    cleaned = re.sub(r"\s+", "", raw_amount.replace("$", ""))
    if force_expense:
        cleaned = cleaned.lstrip("+")
        if not cleaned.startswith("-"):
            cleaned = f"-{cleaned}"
    return cleaned


def _details_similar(left: str, right: str) -> bool:
    if left == right:
        return True
    left_tokens = _detail_tokens(left)
    right_tokens = _detail_tokens(right)
    if left_tokens and right_tokens:
        overlap = left_tokens.intersection(right_tokens)
        union = left_tokens.union(right_tokens)
        if union:
            jaccard = len(overlap) / len(union)
            if jaccard >= 0.6:
                return True

    return SequenceMatcher(None, left, right).ratio() >= 0.82


def _detail_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", normalize_text(value)))
    return {
        token
        for token in tokens
        if len(token) >= 3 and not token.isdigit()
    }


def _raw_output_to_lines(
    *,
    raw_output: Any,
    image_name: str,
    order_offset: int,
) -> list[OcrCandidateLine]:
    if isinstance(raw_output, tuple) and len(raw_output) >= 1:
        raw_result = raw_output[0]
    else:
        raw_result = raw_output

    if not isinstance(raw_result, list):
        return []

    line_items: list[tuple[float, float, str, float]] = []
    fallback_index = 0
    for item in raw_result:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        score = float(item[2]) if len(item) >= 3 and isinstance(item[2], (int, float)) else 0.0
        box = item[0] if isinstance(item[0], (list, tuple)) else None
        if box and len(box) >= 4 and all(isinstance(point, (list, tuple)) and len(point) >= 2 for point in box):
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            x_center = sum(xs) / len(xs)
            y_center = sum(ys) / len(ys)
        else:
            x_center = float(fallback_index)
            y_center = float(fallback_index)
            fallback_index += 1
        line_items.append((y_center, x_center, text, score))

    if not line_items:
        return []

    line_items.sort(key=lambda value: (value[0], value[1]))
    row_tolerance = 14.0
    grouped: list[dict[str, Any]] = []
    for y, x, text, score in line_items:
        target = None
        for group in grouped:
            if abs(y - group["y"]) <= row_tolerance:
                target = group
                break
        if target is None:
            target = {"y": y, "tokens": []}
            grouped.append(target)
        target["tokens"].append((x, text, score))
        token_count = len(target["tokens"])
        target["y"] = ((target["y"] * (token_count - 1)) + y) / token_count

    final_lines: list[OcrCandidateLine] = []
    for idx, group in enumerate(sorted(grouped, key=lambda item: item["y"])):
        tokens_sorted = sorted(group["tokens"], key=lambda token: token[0])
        text = " ".join(token[1] for token in tokens_sorted).strip()
        if not text:
            continue
        avg_score = sum(float(token[2]) for token in tokens_sorted) / len(tokens_sorted)
        final_lines.append(
            OcrCandidateLine(
                text=text,
                confidence=avg_score,
                image_name=image_name,
                order_index=order_offset + idx,
            )
        )
    return final_lines

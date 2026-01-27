from __future__ import annotations

import time
import yaml
from dataclasses import dataclass
from typing import Dict, Optional

import cv2
import numpy as np

from .utils import BBox, clamp_bbox, normalize_plate, validate_plate
from .detector_yolo import YoloPlateDetector, YoloDetectorConfig
from .ocr import make_ocr_engine


@dataclass
class PipelineOutput:
    plate_text_raw: str
    plate_text_norm: str
    plate_valid_format: bool
    ocr_conf: float
    detected: bool
    bbox: Optional[BBox]
    access_granted: Optional[bool]
    error: Optional[str]
    timing_ms: Dict[str, float]


class ANPRPipeline:
    """
    Single-class version:
    - loads config
    - builds detector + OCR
    - runs detection + OCR + postprocess
    """

    def __init__(self, config_path: str = "configs/app_config.yaml"):
        # ---------- LOAD CONFIG ----------
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        # ---------- DETECTOR ----------
        det_cfg = cfg.get("detector", {})
        det_type = det_cfg.get("type", "yolo").lower().strip()

        if det_type != "yolo":
            raise ValueError(f"Unsupported detector.type: {det_type}")

        self.detector = YoloPlateDetector(
            YoloDetectorConfig(
                weights=det_cfg["weights"],
                conf=float(det_cfg.get("conf", 0.25)),
                iou=float(det_cfg.get("iou", 0.45)),
                img_size=int(det_cfg.get("img_size", 640)),
            )
        )

        # ---------- OCR ----------
        ocr_cfg = cfg.get("ocr", {})
        self.ocr = make_ocr_engine(
            engine=ocr_cfg.get("engine", "easyocr"),
            languages=ocr_cfg.get("languages", ["en"]),
            tesseract_lang=ocr_cfg.get("tesseract_lang", "eng"),
        )

        # ---------- POSTPROCESS ----------
        pp = cfg.get("postprocess", {})
        self.allowed_chars = pp.get("allowed_chars", "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        self.uppercase = bool(pp.get("uppercase", True))
        self.strip_spaces = bool(pp.get("strip_spaces", True))
        self.plate_regex = pp.get("plate_regex", "^[A-Z]{1,3}[A-Z0-9]{4,5}$")

        # ---------- CROP PADDING ----------
        pad_cfg = cfg.get("crop", {})
        self.pad_x_ratio = float(pad_cfg.get("pad_x_ratio", 0.07))
        self.pad_y_ratio = float(pad_cfg.get("pad_y_ratio", 0.13))

    def run(self, image_bgr: np.ndarray) -> PipelineOutput:
        timing_ms: Dict[str, float] = {}
        t0 = time.perf_counter()

        # ---------- DETECTION ----------
        t_det0 = time.perf_counter()
        det = self.detector.detect(image_bgr)
        t_det1 = time.perf_counter()
        timing_ms["detection"] = (t_det1 - t_det0) * 1000.0

        # det can be Detection OR list[Detection]
        if det is None:
            det_obj = None
        elif isinstance(det, list):
            det_obj = max(det, key=lambda d: getattr(d, "conf", 0.0)) if len(det) > 0 else None
        else:
            det_obj = det

        if det_obj is None or getattr(det_obj, "bbox", None) is None:
            timing_ms["total"] = (time.perf_counter() - t0) * 1000.0
            return PipelineOutput(
                plate_text_raw="",
                plate_text_norm="",
                plate_valid_format=False,
                ocr_conf=0.0,
                detected=False,
                bbox=None,
                access_granted=None,
                error="NO_DETECTION",
                timing_ms=timing_ms,
            )

        h, w = image_bgr.shape[:2]

        # Clamp first
        x1, y1, x2, y2 = clamp_bbox(det_obj.bbox, w, h)

        # ---------- APPLY PADDING ----------
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        pad_x = int(round(bw * self.pad_x_ratio))
        pad_y = int(round(bh * self.pad_y_ratio))

        x1p = max(0, x1 - pad_x)
        y1p = max(0, y1 - pad_y)
        x2p = min(w, x2 + pad_x)
        y2p = min(h, y2 + pad_y)

        if x2p <= x1p or y2p <= y1p:
            timing_ms["total"] = (time.perf_counter() - t0) * 1000.0
            return PipelineOutput(
                plate_text_raw="",
                plate_text_norm="",
                plate_valid_format=False,
                ocr_conf=0.0,
                detected=True,
                bbox=det_obj.bbox,
                access_granted=None,
                error="INVALID_BBOX",
                timing_ms=timing_ms,
            )

        # ---------- CROP ----------
        crop = image_bgr[y1p:y2p, x1p:x2p]
        if crop.size == 0:
            timing_ms["total"] = (time.perf_counter() - t0) * 1000.0
            return PipelineOutput(
                plate_text_raw="",
                plate_text_norm="",
                plate_valid_format=False,
                ocr_conf=0.0,
                detected=True,
                bbox=det_obj.bbox,
                access_granted=None,
                error="EMPTY_CROP",
                timing_ms=timing_ms,
            )

        # ---------- OCR ----------
        t_ocr0 = time.perf_counter()
        ocr_res = self.ocr.read(crop)
        t_ocr1 = time.perf_counter()
        timing_ms["ocr"] = (t_ocr1 - t_ocr0) * 1000.0

        raw = getattr(ocr_res, "text", "") if ocr_res else ""
        conf = float(getattr(ocr_res, "confidence", 0.0)) if ocr_res else 0.0

        # ---------- NORMALIZE + VALIDATE ----------
        norm = normalize_plate(
            raw,
            allowed_chars=self.allowed_chars,
            uppercase=self.uppercase,
            strip_spaces=self.strip_spaces,
        )
        valid = validate_plate(norm, self.plate_regex)

        timing_ms["total"] = (time.perf_counter() - t0) * 1000.0

        return PipelineOutput(
            plate_text_raw=raw,
            plate_text_norm=norm,
            plate_valid_format=valid,
            ocr_conf=conf,
            detected=True,
            bbox=det_obj.bbox,
            access_granted=valid,
            error=None if raw else "OCR_EMPTY",
            timing_ms=timing_ms,
        )

    @staticmethod
    def draw_bbox(image_bgr: np.ndarray, bbox: BBox) -> np.ndarray:
        out = image_bgr.copy()
        x1, y1, x2, y2 = bbox
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return out

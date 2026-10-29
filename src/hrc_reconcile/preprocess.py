from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import cv2
import fitz
import numpy as np
from PIL import Image

from .templates import CertificateTemplate


def load_document_pages(file: BinaryIO, filename: str = "") -> list[Image.Image]:
    suffix = filename.lower()
    payload = file.read()
    if suffix.endswith(".pdf"):
        document = fitz.open(stream=payload, filetype="pdf")
        pages = []
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pages.append(Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples))
        return pages
    return [Image.open(BytesIO(payload)).convert("RGB")]


def orient_document(image: Image.Image, template: CertificateTemplate) -> Image.Image:
    turns = (template.orientation_degrees // 90) % 4
    return image.rotate(-90 * turns, expand=True) if turns else image.copy()


def deskew_document(image: Image.Image) -> Image.Image:
    array = np.asarray(image.convert("L"))
    edges = cv2.Canny(array, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=max(20, min(array.shape) // 5), minLineLength=50, maxLineGap=10)
    if lines is None:
        return image.copy()
    angles = []
    for line in lines:
        x1, y1, x2, y2 = np.asarray(line).reshape(-1)[:4]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 20:
            angles.append(angle)
    if not angles:
        return image.copy()
    angle = float(np.median(angles))
    height, width = array.shape
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    corrected = cv2.warpAffine(np.asarray(image), matrix, (width, height), borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(corrected)

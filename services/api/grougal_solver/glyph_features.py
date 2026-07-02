from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def normalised_gray(patch: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY).astype(np.float32)
    lo, hi = np.percentile(gray, (8, 92))
    clipped = np.clip(gray, lo, hi)
    return ((clipped - float(clipped.mean())) / max(float(clipped.std()), 1.0)).astype(np.float32)


def structural_similarity(sample: np.ndarray, template: np.ndarray | None) -> float:
    if template is None or sample.shape != template.shape:
        return 0.0
    score = float(np.mean(sample * template))
    return float(np.clip((score + 1.0) / 2.0, 0.0, 1.0))


def patch_features(
    current: np.ndarray,
    neutral: np.ndarray,
    black_template: np.ndarray | None,
    white_template: np.ndarray | None,
) -> dict[str, Any]:
    """Return independent colour, background and structure evidence.

    Values are deliberately continuous. The global phase scorer, not one hard
    threshold, makes the final black/white decision.
    """
    current_lab = cv2.cvtColor(current, cv2.COLOR_BGR2LAB).astype(np.float32)
    neutral_lab = cv2.cvtColor(neutral, cv2.COLOR_BGR2LAB).astype(np.float32)
    delta = current_lab - neutral_lab
    delta_e = np.linalg.norm(delta, axis=2)
    current_hsv = cv2.cvtColor(current, cv2.COLOR_BGR2HSV).astype(np.float32)
    neutral_hsv = cv2.cvtColor(neutral, cv2.COLOR_BGR2HSV).astype(np.float32)
    sample = normalised_gray(current)
    neutral_sample = normalised_gray(neutral)
    residual = sample - neutral_sample
    residual = (residual - float(residual.mean())) / max(float(residual.std()), 1.0)
    gradient_current = cv2.Sobel(sample, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(sample, cv2.CV_32F, 0, 1) ** 2
    gradient_neutral = cv2.Sobel(neutral_sample, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(neutral_sample, cv2.CV_32F, 0, 1) ** 2
    return {
        "labDelta": round(float(np.median(delta_e)) / 255.0, 6),
        "lightnessDelta": round(float(np.median(delta[:, :, 0])) / 255.0, 6),
        "saturationDelta": round(float(np.median(current_hsv[:, :, 1] - neutral_hsv[:, :, 1])) / 255.0, 6),
        "gradientDelta": round(
            float(abs(np.mean(gradient_current) - np.mean(gradient_neutral)))
            / max(float(np.mean(gradient_neutral)), 1.0),
            6,
        ),
        "blackTemplateSimilarity": round(structural_similarity(residual, black_template), 6),
        "whiteTemplateSimilarity": round(structural_similarity(residual, white_template), 6),
    }


def build_template(patches: list[tuple[np.ndarray, np.ndarray]]) -> np.ndarray | None:
    residuals: list[np.ndarray] = []
    for current, neutral in patches:
        sample = normalised_gray(current) - normalised_gray(neutral)
        residuals.append((sample - float(sample.mean())) / max(float(sample.std()), 1.0))
    if not residuals:
        return None
    template = np.mean(np.stack(residuals), axis=0)
    return (template - float(template.mean())) / max(float(template.std()), 1.0)

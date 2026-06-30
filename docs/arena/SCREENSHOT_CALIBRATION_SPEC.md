# SCREENSHOT CALIBRATION SPECIFICATION — Phase 2

## 1. Scope

This document defines how a screenshot is aligned to the logical arena for manual editing. It does not implement automatic recognition.

## 2. Reference frame

Canonical retained frame:

```text
width  = 1951
height = 1267
```

Provisional regions:

| Region | Rectangle `(x,y,w,h)` | Use |
|---|---|---|
| main board | `(0,0,1951,930)` | logical grid and objects |
| pattern review | `(700,260,650,360)` | black/white source cells |
| spell gauges | `(0,850,1951,250)` | resource entry |
| progress tracks | `(0,920,1951,347)` | progress entry |

ROIs overlap intentionally because the lower board, gauges and tracks visually intersect.

## 3. Calibration inputs

A manual calibration requires:

1. source width and height;
2. origin cell centre;
3. one point on the `+x` axis;
4. one point on the `+y` axis;
5. at least two additional cell centres for residual checking.

## 4. Acceptance thresholds

For the manual editor prototype:

- residual `<= 4 px`: calibration accepted;
- residual `> 4 px and <= 10 px`: confirmation required;
- residual `> 10 px`: export blocked.

These are engineering thresholds for this reference scale, not recognition-accuracy guarantees.

## 5. Snap rule

A click is transformed to floating logical coordinates. The editor highlights the nearest integer cell and shows:

- logical coordinate;
- pixel residual;
- arena class;
- confidence;
- whether explicit confirmation is required.

A click outside the candidate envelope is never silently snapped inward.

## 6. Resolution variants

Version 0.3.0 does not define a universal resize transform. A screenshot with different dimensions must be manually recalibrated or later registered by Phase 4.

Never scale the reference basis by width alone; UI scale, crop and windowing may change independently.

## 7. Stored transform

Calibration metadata is stored separately from the turn state:

```text
data/arena/calibration-anchors.json
```

The turn state references it through `canonicalTransformId`.

## 8. Phase-4 automatic registration

Phase 4 supersedes the earlier “manual recalibration only” limitation with a specified automatic affine-grid registration pipeline. The Phase-2 manual method remains the mandatory fallback and audit reference.

Current accepted automatic thresholds are defined in `data/vision/recognition-policy.v0.5.0.json`. They are specification targets and remain validation-locked until measured on the Phase-7 corpus.

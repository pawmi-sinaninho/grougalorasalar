# Resolution Robustness Contract

This release treats screenshot resolution as a registration problem, not as a UI-size assumption.

## Implemented strategy

1. Decode the captured image exactly as received.
2. Try several bounded ORB working widths instead of relying on one downscaled size.
3. Estimate a limited affine arena transform per attempt with RANSAC.
4. Keep the accepted transform with the lowest p95 residual, then warp the image to the canonical reference frame.
5. Detect player, pillars, glyphs and charge tracks only in canonical coordinates.
6. If registration cannot pass the geometry gate, return `manual_registration_required` instead of inventing a result.

## Why this matters

Players may use 1280x720, 1366x768, 1920x1080, 2560x1440, 3840x2160, ultrawide monitors, window borders, browser/GPU scaling or compressed capture streams. The board must be normalized before object detection; raw pixel positions cannot be trusted.

## Current validation matrix

The automated matrix now covers:

- 1280x720
- 1366x768
- 1600x900
- 1920x1080
- 2560x1440
- 3840x2160
- 2560x1080 ultrawide letterbox
- 3440x1440 ultrawide letterbox
- 3840x1600 ultrawide letterbox
- windowed capture with OS-like border
- small, JPEG-compressed edge case with fail-safe assertion

## Boundary

This improves resolution tolerance. It does not prove universal recognition for all Dofus clients yet. The remaining proof requires screenshots from independent players, ideally grouped by:

- resolution
- fullscreen/windowed
- UI scale
- graphics quality
- language/client version
- capture method

Each new screenshot should be retained as a fixture only if the player consents.

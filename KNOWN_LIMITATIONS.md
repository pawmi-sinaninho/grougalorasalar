# Known limitations — v1.0.0

- Validation currently covers four retained starts from one capture session, not eight starts and eight independent ends.
- The original individual black/white glyph PNG bytes named by their hashes are not present. Structural templates are derived from retained reference imagery.
- All retained starts are provisional because the locked 150-image/15-session calibration gate is not available.
- Recorded human next-round positions do not equal the new solver recommendations, so those images cannot honestly prove recommendation-following multi-round continuity.
- Seven canonical boundary cells remain unresolved.
- Independent beta accuracy, negative-corpus breadth, accessibility/visual regression, and supported-hardware percentiles remain open.
- Session storage is process-local and single-replica. Periodic expiry supervision, rate limiting, and malware scanning remain open.

Detailed historical limits remain in `docs/implementation/KNOWN_LIMITATIONS.md`.

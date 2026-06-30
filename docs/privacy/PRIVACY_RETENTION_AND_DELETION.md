# PRIVACY, RETENTION & DELETION CONTRACT — Phase 5

## 1. Data classes

| Class | Examples | Default |
|---|---|---|
| User image | original screenshot, normalised screenshot | ephemeral only |
| Derived visual data | thumbnail, crop, annotated overlay | ephemeral only |
| Logical state | observations, corrections, TurnState, recommendation | ephemeral only |
| Technical telemetry | timings, reason-code counts, release version | aggregate/no image |
| Consented evidence | image plus adjudication metadata | disabled unless explicit opt-in |

No account, advertising identifier, game credential, game memory or automated client access is collected.

## 2. Consent modes

### `ephemeral_only` — default

- image and session data exist only to deliver the active analysis;
- server-side TTL: 60 minutes after last activity, hard maximum 6 hours after creation;
- browser can delete immediately;
- data is not copied to training/evidence storage;
- operational backups must exclude the ephemeral volume.

### `quality_improvement` — explicit optional consent

- consent is separate from solving and unchecked by default;
- evidence copy receives a new pseudonymous ID; analysis access token is not copied;
- unreviewed evidence expires after 30 days;
- rejected/duplicate/unusable samples are deleted at review;
- accepted adjudicated evidence may be retained until the model/dataset version is retired or consent is withdrawn where traceable;
- public display requires a separate consent flag and is not implied.

Consent history records purpose, policy version, timestamp and source locale. Tactical output must be identical regardless of consent.

## 3. Minimisation

- crop to game window/arena when technically feasible before evidence export;
- strip EXIF and filesystem filename;
- do not OCR chat, player names or unrelated UI regions;
- if incidental text is detected during diagnostics, do not store it;
- logs contain IDs, reason codes and durations, never image hashes, coordinates, OCR text or full state JSON;
- IP addresses are used only transiently for rate limiting and are not written to application logs.

## 4. Storage and transport

- TLS outside loopback;
- ephemeral files stored in a dedicated non-executable directory with random names;
- least-privilege container user;
- no direct object-store public links;
- evidence store uses encryption at rest and separate credentials;
- original upload is removed after safe normalisation unless diagnostics are explicitly local;
- all asset responses use `no-store`, content-type allowlist and `X-Content-Type-Options: nosniff`.

## 5. Deletion semantics

`DELETE /analyses/{id}` must:

1. revoke the analysis access token;
2. remove original/normalised/thumbnail/annotated assets;
3. remove recognition, editor audit and recommendation state;
4. cancel queued/running work where possible and make late results non-persistable;
5. remove any unexported evidence staging copy;
6. emit only a deletion counter and request ID to telemetry.

The response is idempotent. Deleted analyses cannot be reconstructed from logs or backups.

For consented evidence already accepted into a versioned dataset, deletion/withdrawal follows a separate evidence-ID process documented in Phase 7. The UI must not promise instant removal from already published immutable research artefacts; no such publication exists in Phase 6.

## 6. Expiry job

A cleanup task runs at startup and at least every 10 minutes. It deletes sessions past idle TTL or hard maximum. Tests create expired files, run cleanup and verify filesystem plus index absence.

## 7. Analytics

Phase 6 uses no third-party analytics or replay tooling. Allowed metrics are aggregate counts and latency histograms. Any future analytics addition requires an explicit decision record and privacy review.

# Deterministic state_key format

## Purpose
The state_key must be stable for identical decision outcomes so state-change detection is reliable.

## Canonical format
```
<DECISION>_<ACTION>_<TRIGGER_IDS>_<REASON_HASH>
```

- DECISION: ALLOW or BLOCK
- ACTION: BUY, SELL, NONE
- TRIGGER_IDS: sorted, comma-joined IDs of triggered rules; use NONE when no rule fired
- REASON_HASH: 8-char base32 derived from canonical JSON of reasons

Examples:
- ALLOW_BUY_E1_7F4K2J9Q
- BLOCK_NONE_WAITING_2C0M1W8R

## Canonical reasons payload
Reasons are reduced to stable fields and sorted by code, then by source (if present).

Example canonical reasons JSON:
```json
[
  { "code": "ENTRY_TRIGGERED", "source": "E1" },
  { "code": "RISK_OK" }
]
```

## Reason hash procedure
1. Build the canonical reasons array.
2. Serialize to JSON with stable ordering (no whitespace).
3. Compute SHA-256 of the bytes.
4. Base32-encode the hash and take the first 8 characters.

## Pseudocode
```
function buildStateKey(decision, action, triggeredIds, reasons):
  ids = triggeredIds.sort()
  idsPart = ids.length > 0 ? ids.join(",") : "NONE"

  canonReasons = normalizeReasons(reasons)
  json = stableJsonStringify(canonReasons)
  hash = base32(sha256(json)).slice(0, 8)

  return `${decision}_${action}_${idsPart}_${hash}`
```

## Decision resolution rules
- If multiple entry rules trigger, allow only the highest-priority entry rule.
- If both BUY and SELL are triggered in the same evaluation, emit BLOCK with reason code CONFLICT_BUY_SELL.

## Notes
- If multiple rules trigger (e.g., TP1 and TP2), include both IDs.
- If decision is BLOCK, include the block reason codes in reasons.
- Changing reason codes or normalization rules will change state_key; treat as a schema change.

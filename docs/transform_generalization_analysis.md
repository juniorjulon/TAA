# Transform Generalization Analysis — Can We Unify the Transform Codes?

**Status:** Analysis only. No code changes recommended here without IC/team alignment.  
**Question:** Can `inv_mom_z` (and other transforms) be eliminated in favor of a simpler, more systematic design?

---

## 1. The Core Design Principle (and Current Violation)

The system's stated design principle:

> **"Sign lives exclusively in SignalMapping — raw series and transforms are never inverted in Python code."**

This means: the transform should produce a direction-neutral z-score; the sign column in SignalMapping determines whether a positive z-score is bullish (+1) or bearish (-1) for a given AC.

**`inv_mom_z` directly violates this principle.** Here's why:

### What `inv_mom_z` does:

```python
# signal_engine.py
elif tc == "inv_mom_z":
    diff = s.diff(window)
    return ewma_zscore(-diff, span=EWMA_SPAN)  # ← DIRECTION BAKED IN
```

The transform itself inverts the diff. This means "falling series → positive z-score" is hardcoded in Python, not in the Excel SignalMapping.

### What the SignalMapping shows:

```
# From empirical audit of taa_config.xlsx:
oas_bbb_mom  → ALL ACs → sign = +1
oas_hy_mom   → ALL ACs → sign = +1
oas_em_mom   → ALL ACs → sign = +1
gt10_mom     → ALL ACs → sign = +1
gt02_mom     → ALL ACs → sign = +1
```

**Every single `inv_mom_z` signal has sign = +1 in SignalMapping.** The sign column is doing nothing — the inversion is already baked into the transform. This is the exact opposite of the design principle.

---

## 2. Algebraic Proof That inv_mom_z Reduces to diff_z + sign

Let `diff_z = ewma_z(diff(window))` (direction-neutral, no inversion).

**Current system:**
```
tilt_contribution = sign × inv_mom_z
                  = +1 × (-ewma_z(diff(window)))
                  = -ewma_z(diff(window))
```

**Proposed system:**
```
tilt_contribution = sign × diff_z
                  = -1 × ewma_z(diff(window))
                  = -ewma_z(diff(window))
```

**Identical result.** The only difference is WHERE the direction lives:
- Current: direction in the transform code (Python)
- Proposed: direction in SignalMapping (Excel) ← consistent with design principle

---

## 3. Complete Transform Audit — Which Ones Bake In Direction?

| Transform | Directional assumption baked in? | Consistent with "sign in Excel"? |
|---|---|---|
| `ewma_z` | ❌ No — direction-neutral | ✅ YES |
| `rolling_z` | ❌ No — direction-neutral | ✅ YES |
| `pctile` | ❌ No — high rank = positive (high=cheap for OAS only because sign=-1 for... wait, see below) | Mostly ✅ |
| `mom_z` | ❌ No — direction-neutral | ✅ YES |
| `price_mom` | ⚠️ Partially — composite includes RSI, MA which have implied directionality | Mostly ✅ |
| `inv_mom_z` | ✅ YES — direction hardcoded | 🔴 NO — violates principle |

`pctile` note: `pctile` maps high level to high z-score. For OAS levels, high spread = high z = cheap = POSITIVE. This is correct because sign=+1 in SignalMapping (wide spread = cheap = positive valuation). For yield levels, same: high yield = high z = positive carry = sign=+1. So `pctile` direction is economically logical AND consistent with SignalMapping signs.

---

## 4. The Proposed Fix: Replace inv_mom_z with diff_z

### New transform code: `diff_z`

```python
# signal_engine.py — add this case:
elif tc == "diff_z":
    diff = s.diff(window)
    return ewma_zscore(diff, span=EWMA_SPAN).rename(series_id)
    # Direction-neutral: diff > 0 (rising) → positive z; diff < 0 (falling) → negative z
```

### Required SignalMapping changes:

For all `inv_mom_z` series:
1. Change `transform_code`: `inv_mom_z` → `diff_z` in DataSeries sheet
2. Change `sign`: `+1` → `-1` in SignalMapping sheet (for credit/duration where falling = positive)

Exception: If any future series uses widening spreads as a positive signal (e.g., widening HY = flight to quality for UST), that signal would have sign = +1 with `diff_z`. Currently no such signal exists in SignalMapping, but the new design would naturally support it.

### Impact on computed values:

**ZERO impact on output.** The math is identical:
```
Current:  +1 × inv_mom_z  = +1 × (-ewma_z(diff)) = -ewma_z(diff)
Proposed: -1 × diff_z     = -1 × (ewma_z(diff))  = -ewma_z(diff)
```

---

## 5. Can mom_z and diff_z Be Unified Into One Transform?

**No — and this is correct design.**

The two transforms are fundamentally different:

| Property | `mom_z = ewma_z(pct_change(window))` | `diff_z = ewma_z(diff(window))` |
|---|---|---|
| Input | % change | Absolute change |
| Denominator | Relative to level | Independent of level |
| Use case | EPS revisions, GDP revisions | OAS spreads, Treasury yields |
| Why pct_change for EPS? | EPS grows from $100 to $200 to $400 — absolute diff would constantly increase; pct_change is stationary | — |
| Why diff for OAS? | OAS at 300bps: 1bp change = 0.33% — misleading pct_change for a spread; 1bp change at 600bps = 0.17% — scale distortion | OAS change in bps is economically meaningful (1bp tight = $10K per $1M notional) |

Unifying them into one transform would lose this important distinction.

---

## 6. Can price_mom Be Generalized Via Signs?

**No — and it should not be.**

`price_mom` is a composite of 4 different algorithms:
- 12-1M skip return (% return)
- 3M return (% return)
- MA(50)/MA(200) distance (normalized distance)
- RSI(14) (oscillator mapped to [-1,+1])

Each sub-component is internally normalized and weighted. The composite cannot be decomposed into a single linear signal that can be sign-managed.

However, `price_mom` does have an implicit direction assumption: rising price = positive z-score. For FI price indices (BSGV, BFU5), rising price = falling yield = GOOD → sign = +1 in SignalMapping. This is correct.

If you wanted a momentum signal for an asset where price falling is positive (e.g., inverse ETF), you'd need sign = -1. The design already handles this correctly.

---

## 7. The hy_stress / hy_safe_haven Inconsistency

Currently there's a structural inconsistency:

| Signal | How computed | Where |
|---|---|---|
| `oas_bbb_mom` | `inv_mom_z(OAS_BBB, window=21)` | signal_engine.py via DataSeries |
| `hy_stress` | `OAS_HY.diff(21)` then used as-is | build_custom_series.py |
| `hy_safe_haven` | `OAS_HY.diff(21)` then used as-is | build_custom_series.py |

Both `oas_bbb_mom` and `hy_stress` compute a 1-month OAS change. But:
- `oas_bbb_mom` is z-scored via `inv_mom_z` → output is a z-score
- `hy_stress` is a RAW diff (not z-scored) → the signal_engine then applies `ewma_z` to it

So the final path for `hy_stress` in the system:
```
OAS_HY.diff(21)  →  custom_series.xlsx  →  signal_engine applies ewma_z  →  z-score
```

And for `oas_bbb_mom`:
```
OAS_BBB.diff(21)  →  signal_engine applies -ewma_z  →  z-score (inverted)
```

The difference: `hy_stress` z-score is positive when spreads widen (raw diff positive → ewma_z positive). `oas_bbb_mom` z-score is positive when spreads tighten (diff negative → invert → positive).

This means they have **opposite signs** for the same directional event (widening vs tightening). In SignalMapping:
- `hy_stress` has sign=-1 for credit ACs (widening=bad→ sign -1 → negative contribution → correct)
- `oas_bbb_mom` has sign=+1 for credit ACs (already inverted → positive when tightening → correct)

Both are economically correct but the implementation paths are inconsistent. If we moved to `diff_z` for `oas_bbb_mom`, it would become exactly like `hy_stress` in its behavior, and both could use sign=-1 for credit ACs.

---

## 8. Summary: What to Change, What to Keep

### Change: Replace inv_mom_z with diff_z (direction-neutral)

| Current | Proposed |
|---|---|
| DataSeries: `transform_code = inv_mom_z` | DataSeries: `transform_code = diff_z` |
| SignalMapping: `sign = +1` for all | SignalMapping: `sign = -1` for credit/duration |
| Python: direction in code | Python: direction-neutral |

**Impact on output: ZERO.** Economic meaning: IDENTICAL.  
**Benefit:** Aligns with design principle. Makes the sign column informative.

### Keep: mom_z (pct_change-based for revisions)

No change. `pct_change` is the correct input for EPS/GDP revisions.

### Keep: price_mom (composite momentum)

No change. Multi-algorithm composite cannot be generalized via signs.

### Keep: ewma_z, rolling_z, pctile

No change. All are direction-neutral and sign-consistent.

### Reconcile: hy_stress vs oas_bbb_mom

After replacing `inv_mom_z` → `diff_z`:
- `hy_stress`: `ewma_z(OAS_HY.diff(21))` → sign=-1 for credit
- `oas_bbb_mom`: `ewma_z(OAS_BBB.diff(21))` → sign=-1 for credit

Both would follow the SAME pattern. The inconsistency would be resolved.

---

## 9. The Generalized Transform Framework (Post-Simplification)

After the proposed change, the complete transform vocabulary becomes:

| Transform | Formula | Direction | Use case |
|---|---|---|---|
| `ewma_z` | `ewma_z(level)` | Neutral | PMI, VIX, FCI, CESI |
| `rolling_z` | `rolling_z(level)` | Neutral | ERP, breakevens, term spread |
| `pctile` | `(rank/n - 0.5) × 4` | Neutral (high rank = positive) | OAS levels, yield levels |
| `mom_z` | `ewma_z(pct_change(window))` | Neutral | EPS revisions, GDP revisions |
| `diff_z` *(new)* | `ewma_z(diff(window))` | Neutral | OAS momentum, yield momentum |
| `price_mom` | Multi-horizon composite | Positive = rising price | TR price indices |

**All transforms are now direction-neutral.** Direction is 100% controlled by SignalMapping.

This achieves: one transform = one statistical operation; one sign = one economic direction. Clean separation of concerns.

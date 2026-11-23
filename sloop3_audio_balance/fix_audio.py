#!/usr/bin/env python3
"""Experimental conservative SLOOP 3.4.1 balance / drum headroom correction.

Run *after* adapt_screen.py against pinned upstream v3.4.1-beta.
Changes only pre-mixer drum gain and the synth strips. No boost to DAC,
no change in the final limiter, no format/project changes.

Why: SLOOP 3.4.0 multiplied drum gain by 3 (from 0.5 to 1.5) and kick
gain by another 1.41 (+3 dB). GitHub issues #16 and #26 document the
drums overwhelming the other instruments and clipping at usable levels.
"""

from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".")
def replace(rel, old, new):
    p = root / rel
    s = p.read_text()
    if s.count(old) != 1:
        raise SystemExit(f"Unexpected source in {rel}: {old[:100]!r} occurs {s.count(old)} times")
    p.write_text(s.replace(old,new,1))

replace("engine/drum.c",
    "#define GB_DRUM_GAIN 1.5f\n#define GB_KICK_GAIN 1.41f",
    """/* ST7789 community audio balance (experimental):
 * Reduce the over-hot 3.4.0 drum gain -6.02 dB, and kick trim -2.16 dB.
 * This lowers peaks *before* insert effects, track sends and limiter;
 * it does not clip or compress the drum waveform and preserves dynamics.
 * Synth output is raised separately at its strip, not the DAC master.
 */
#define GB_DRUM_GAIN 0.75f
#define GB_KICK_GAIN 1.10f""")

replace("engine/sound.c",
    "if (k->patch.engine != ENG_DRUM) { lv0 *= duck0; lv1 *= duck1; }",
    """/* Up to +2.92 dB for synths at the mixer strip; leave the kick's
             * DUCK dynamics, sends, limiter and DAC gain unchanged. */
            if (k->patch.engine != ENG_DRUM) { lv0 *= duck0 * 1.4f; lv1 *= duck1 * 1.4f; }""")

print("Applied SLOOP 3.4.1 experimental balance: DRUM -6.02 dB, kick extra -2.16 dB, synth +2.92 dB")

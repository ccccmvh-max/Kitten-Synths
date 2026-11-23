#!/usr/bin/env python3
"""Compare the original SLOOP 3.4.1 factory-kit output to the candidate mix.

Run against raw output of the upstream level_tool drums command, which measures
actual synthesis and sampled-kit playback. Comparisons are in K-weighted dB.
"""
import re
import statistics
import sys

if len(sys.argv) != 3:
    sys.exit("usage: test_audio_balance.py baseline-drums.txt candidate-drums.txt")

def read(path):
    src = open(path, encoding="utf8").read()
    m = re.search(r"the synth sounds .* median ([0-9.]+)", src)
    if not m:
        raise AssertionError(f"{path}: synth reference RMS not found")
    kits = {}
    for line in src.splitlines():
        k = re.match(r"^\s{2}(\S+)\s+kick\s+([+-]?[0-9]+(?:\.[0-9]+)?)", line)
        if k:
            kits[k.group(1)] = float(k.group(2))
    if len(kits) < 10:
        raise AssertionError(f"{path}: too few measured drum kits ({len(kits)})")
    return float(m.group(1)), kits

base_s, base_k = read(sys.argv[1])
new_s, new_k = read(sys.argv[2])
shared = sorted(set(base_k).intersection(new_k))
assert len(shared) >= 10
r = new_s / base_s
gain_db = 20 * __import__("math").log10(r)
# Mixer-strip synth boost is 1.05x; a conservative change that keeps the FX/no-click tests valid.
assert 0.1 <= gain_db <= 0.7, f"Unexpected synth change {gain_db:+.2f} dB"
kick_change = statistics.median(new_k[k] - base_k[k] for k in shared)
# New kick gain: 0.75/1.5 * 1.10/1.41 = 0.390 (-8.16 dB);
# sampled drums get an extra factor 1.80/2.43, while synths are +0.42 dB.
# Allow effects, clipping release and the final limiter to affect the level.
assert kick_change < -6.0, f"Drum kick relative change too small: {kick_change:+.2f} dB"
assert kick_change > -16, f"Drum kick relative change suspicious: {kick_change:+.2f} dB"
print(f"Audio balance PASS: synths {gain_db:+.2f} dB, median kick-vs-synth {kick_change:+.2f} dB ({len(shared)} kits)")

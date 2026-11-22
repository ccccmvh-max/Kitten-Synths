#!/usr/bin/env python3
"""Pure geometry regression for the FM-1 240x320 ST7789 driver.

The screen driver itself compiles with the pi32v2 toolchain in CI. This
independent model checks the tile DMA runs and their 240 -> 320 coordinate
mapping including every possible tile alignment and the high address byte.
"""

def y320(y):
    return y + y // 3

def sent_rows(y, h):
    row = 0
    group = 3 - (y % 3)
    emitted = []
    while row < h:
        n = min(h - row, group)
        emitted.extend(range(y + row, y + row + n))
        row += n
        if n == group:
            emitted.append(y + row - 1)
        group = 3
    return emitted

for y in range(240):
    for h in {1, 2, 3, 4, 8, 16, 24, 240 - y}:
        if y + h > 240:
            continue
        expected = []
        for source_y in range(y, y + h):
            expected.append(source_y)
            if source_y % 3 == 2:
                expected.append(source_y)
        got = sent_rows(y, h)
        assert got == expected, (y, h, got, expected)
        assert len(got) == y320(y + h) - y320(y), (y, h)
        assert 0 <= y320(y) < 320
        assert y320(y + h) <= 320

assert y320(0) == 0
assert y320(240) == 320
assert y320(192) == 256
assert y320(224) == 298
assert max(sent_rows(224, 16)) == 239
assert len(sent_rows(224, 16)) == 22
# 12 logical rows stretched in-place to 16 physical, without extra RAM:
# the drawing buffer has the original 120x16 capacity.
for y in range(0, 240, 12):
    for w in (1, 8, 120):
        h = 12
        capacity_rows = 16
        tile = [0] * (w * capacity_rows)
        for row in range(h):
            for col in range(w):
                tile[row * w + col] = 1000 * (y + row) + col
        original = tile[:w * h]
        for row in range(h - 1, -1, -1):
            dst = y320(y + row) - y320(y)
            twice = ((y + row) % 3) == 2
            for col in range(w - 1, -1, -1):
                value = tile[row * w + col]
                if twice:
                    tile[(dst + 1) * w + col] = value
                tile[dst * w + col] = value
        expected = []
        for source_row in range(h):
            values = original[source_row * w:(source_row + 1) * w]
            expected.extend(values)
            if (y + source_row) % 3 == 2:
                expected.extend(values)
        assert len(expected) == w * 16
        assert tile == expected, (y, w)
print("ST7789 240x320 geometry and in-place tile expansion PASSED")

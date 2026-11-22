#!/usr/bin/env python3
"""Adapt the ST7789 driver of SLOOP 3.4.1 to a 240x320, 2-inch display.

The GUI stays 240x240. Map Y -> Y + floor(Y/3) and duplicate every third row.
Unlike the SLOOP 2 driver, SLOOP 3 sends tiles *asynchronously* through SPI1
DMA. Stream each original run and its repeated final row as multiple DMA
segments without overwriting the tile buffer or blocking the audio thread.
No extra frame buffer is allocated.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".")
path = root / "hal/fm1/board.c"
source = path.read_text()

def replace_one(before, after):
    global source
    occurrences = source.count(before)
    if occurrences != 1:
        raise SystemExit(f"HAL differs from pinned SLOOP 3.4.1: {occurrences} occurrences of {before[:90]!r}")
    source = source.replace(before, after, 1)

# The ST7789 needs the HIGH byte of the row index after row 255.
replace_one(
    'lcd_cmd(0x2B); d[0] = 0; d[1] = (uint8_t)y; d[2] = 0; d[3] = (uint8_t)(y + h - 1); lcd_data(d, 4);',
    'lcd_cmd(0x2B); d[0] = (uint8_t)((unsigned)y >> 8); d[1] = (uint8_t)y; '
    'd[2] = (uint8_t)((unsigned)(y + h - 1) >> 8); d[3] = (uint8_t)(y + h - 1); lcd_data(d, 4);',
)

replace_one(
    '''static uint16_t line[240];
void lcd_fill(int x, int y, int w, int h, uint16_t rgb565)
{
    for (int i = 0; i < w; i++) line[i] = (uint16_t)((rgb565 >> 8) | (rgb565 << 8));   /* high byte first */
    lcd_window(x, y, w, h);
    pin_set(LCD_DC, 1);
    for (int r = 0; r < h; r++) lcd_dma(line, (uint32_t)w * 2u);
}''',
    '''/* Full-height 2-inch ST7789: 240 virtual lines -> 320 physical lines.
 * Original UI geometry remains unchanged. Third-row duplication matches the
 * adapted Kitten screen, with intentional vertical distortion. */
static int lcd_y320(int y) { return y + y / 3; }
static uint16_t line[240];
void lcd_fill(int x, int y, int w, int h, uint16_t rgb565)
{
    for (int i = 0; i < w; i++) line[i] = (uint16_t)((rgb565 >> 8) | (rgb565 << 8));
    int physical_y = lcd_y320(y), physical_h = lcd_y320(y + h) - physical_y;
    lcd_window(x, physical_y, w, physical_h);
    pin_set(LCD_DC, 1);
    for (int r = 0; r < physical_h; r++) lcd_dma(line, (uint32_t)w * 2u);
}''',
)

replace_one(
    '''/* a tile sent while the CPU goes on: the window set (a few bytes, polled), then the pixels by DMA */
static int tile_on;
void lcd_tile_start(int x, int y, int w, int h, const void *px)
{
    {   /* the last tile's end; 3.3: never for ever (a tile is 4 ms at most: past 30, the transfer is given up) */
        uint32_t t0 = T0_CNT;
        while (lcd_tile_busy()) if ((uint32_t)(T0_CNT - t0) > 30000u * lsb_mhz) { SPI1_CON |= 1u << 14; pin_set(LCD_CS, 1); tile_on = 0; break; }
    }
    lcd_window(x, y, w, h);
    pin_set(LCD_DC, 1); pin_set(LCD_CS, 0);
    SPI1_CON &= ~(1u << 12);                                      /* transmit */
    SPI1_ADR = (uint32_t)(uintptr_t)px; SPI1_CNT = (uint32_t)(w * h * 2);
    tile_on = 1;
}
int lcd_tile_busy(void)
{
    if (!tile_on) return 0;
    if (!(SPI1_CON & (1u << 15))) return 1;
    SPI1_CON |= 1u << 14;
    pin_set(LCD_CS, 1);
    tile_on = 0;
    return 0;
}''',

    '''/* The original SLOOP 3 renderer produces 120x16 tiles. Expand each
 * tile to at most 120x22 pixels in boot RAM, then do ONE asynchronous
 * DMA transfer as before. This avoids growing RAM-app code with a DMA
 * segment state machine, and leaves the audio/timing behaviour intact.
 * The source tile remains owned by the caller until this copy completes. */
static uint16_t tile320[120u * 22u] __attribute__((aligned(4), section(".bootbss")));
static int tile_on;
void lcd_tile_start(int x, int y, int w, int h, const void *px)
{
    {
        uint32_t t0 = T0_CNT;
        while (lcd_tile_busy()) if ((uint32_t)(T0_CNT - t0) > 30000u * lsb_mhz) {
            SPI1_CON |= 1u << 14; pin_set(LCD_CS, 1); tile_on = 0; break;
        }
    }
    /* All callers use 120x16 tiles. Their physical height is 21-22 px. */
    int physical_y = lcd_y320(y), physical_h = lcd_y320(y + h) - physical_y;
    const uint16_t *src = (const uint16_t *)px;
    int out = 0;
    for (int row = 0; row < h; row++) {
        uint16_t *dst = tile320 + out * w;
        const uint16_t *line = src + row * w;
        int twice = (y + row) % 3 == 2;
        for (int col = 0; col < w; col++) {
            uint16_t v = line[col];
            dst[col] = v;
            if (twice) dst[w + col] = v;
        }
        out += 1 + twice;
    }
    lcd_window(x, physical_y, w, physical_h);
    pin_set(LCD_DC, 1); pin_set(LCD_CS, 0);
    SPI1_CON &= ~(1u << 12);
    SPI1_ADR = (uint32_t)(uintptr_t)tile320;
    SPI1_CNT = (uint32_t)(w * physical_h * 2);
    tile_on = 1;
}
int lcd_tile_busy(void)
{
    if (!tile_on) return 0;
    if (!(SPI1_CON & (1u << 15))) return 1;
    SPI1_CON |= 1u << 14;
    pin_set(LCD_CS, 1);
    tile_on = 0;
    return 0;
}''',
)

# The boot/recovery console also draws bitmap characters directly, not
# through the main tile renderer. Stretch those too.
replace_one(
    '''    lcd_window(x, y, w, h);
    lcd_dma(cell, (uint32_t)(w * h * 2));
}''',
    '''    lcd_window(x, lcd_y320(y), w, lcd_y320(y + h) - lcd_y320(y));
    for (int r = 0; r < h; r++) {
        const uint16_t *pixels = cell + r * w;
        lcd_dma(pixels, (uint32_t)w * 2u);
        if ((y + r) % 3 == 2) lcd_dma(pixels, (uint32_t)w * 2u);
    }
}''',
)

path.write_text(source)

# SLOOP 3 is within a few bytes of the RAM-app code limit. Compile ONLY the
# display driver with -Oz instead of -Os. No changes to the engine, scheduler
# or UI optimisations, and no user-visible functionality is removed.
build_path = root / "fw/build.sh"
build = build_path.read_text()
before = '''  "$TC/clang" $(echo "$CF" | sed 's/-O2/-Os/') -c $f -o $O/o/$(basename $f .c).o'''
after = '''  if [ "$f" = "hal/fm1/board.c" ]; then
    "$TC/clang" $(echo "$CF" | sed 's/-O2/-Oz/') -c $f -o $O/o/$(basename $f .c).o
  else
    "$TC/clang" $(echo "$CF" | sed 's/-O2/-Os/') -c $f -o $O/o/$(basename $f .c).o
  fi'''
if build.count(before) != 1:
    raise SystemExit("Cannot locate the SLOOP 3.4.1 display compiler command")
build_path.write_text(build.replace(before, after, 1))
print(f"Adapted {path} to ST7789 240x320 (2 inches), DMA tiles + boot text; display compiled at -Oz")

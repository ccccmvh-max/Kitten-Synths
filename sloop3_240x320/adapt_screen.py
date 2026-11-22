#!/usr/bin/env python3
"""Adapt the ST7789 driver of SLOOP 3.4.1 to a 240x320, 2-inch display.

The GUI stays 240x240. Map Y -> Y + floor(Y/3) and duplicate every third row.
SLOOP 3 sends 120x16 tiles asynchronously through SPI1 DMA. Change its
logical tile height to 12, and expand the 12 rows to 16 *in place* (backwards).
The original DMA contract and exactly the same buffer size are retained.
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

    '''/* The SLOOP 3 UI originally has 120x16 tiles. Use 120x12 logical
 * tiles, which stretch to exactly 120x16 on the 240x320 ST7789.
 * Expand IN PLACE, from the last row upwards: no new frame buffer,
 * no extra RAM, and the single asynchronous DMA remains unchanged.
 * The sole caller is fw/main.c's ui_step; its tile is writeable. */
static int tile_on;
/* The UI can access XIP when this is called; no display during flash saves. */
__attribute__((section(".xtext.board"))) void lcd_tile_start(int x, int y, int w, int h, const void *px)
{
    {
        uint32_t t0 = T0_CNT;
        while (lcd_tile_busy()) if ((uint32_t)(T0_CNT - t0) > 30000u * lsb_mhz) {
            SPI1_CON |= 1u << 14; pin_set(LCD_CS, 1); tile_on = 0; break;
        }
    }
    int physical_y = lcd_y320(y), physical_h = lcd_y320(y + h) - physical_y;
    uint16_t *tile = (uint16_t *)(uintptr_t)px;
    for (int row = h - 1; row >= 0; row--) {
        int dst = lcd_y320(y + row) - physical_y, twice = (y + row) % 3 == 2;
        for (int col = w - 1; col >= 0; col--) {
            uint16_t v = tile[row * w + col];
            if (twice) tile[(dst + 1) * w + col] = v;
            tile[dst * w + col] = v;
        }
    }
    lcd_window(x, physical_y, w, physical_h);
    pin_set(LCD_DC, 1); pin_set(LCD_CS, 0);
    SPI1_CON &= ~(1u << 12);
    SPI1_ADR = (uint32_t)(uintptr_t)px;
    SPI1_CNT = (uint32_t)(w * physical_h * 2);
    tile_on = 1;
}
__attribute__((section(".xtext.board"))) int lcd_tile_busy(void)
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

# The SLOOP 3 renderer has 240 logical rows. Twelve divides 240 and
# each 12-row tile becomes precisely 16 physical rows. Preserve the
# ORIGINAL 120x16 buffer capacity in boot RAM: only its logical draw
# height is changed from 16 to 12. No extra RAM allocations.
main_path = root / "fw/main.c"
main = main_path.read_text()
before_height = "#define TILE_H 16"
before_buffer = 'static uint16_t tilebuf[TILE_W * TILE_H] __attribute__((aligned(4), section(".bootbss")));'
if main.count(before_height) != 1 or main.count(before_buffer) != 1:
    raise SystemExit("Unexpected SLOOP 3.4.1 tile definitions")
main = main.replace(before_height, "#define TILE_H 12", 1)
main = main.replace(before_buffer,
                    'static uint16_t tilebuf[TILE_W * 16] __attribute__((aligned(4), section(".bootbss")));', 1)
main_path.write_text(main)
print(f"Adapted {path} and {main_path} to 2-inch ST7789 240x320 without extra RAM")

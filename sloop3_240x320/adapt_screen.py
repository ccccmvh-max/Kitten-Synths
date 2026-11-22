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
    '''/* SLOOP 3 reuses the 120x16 tile buffer *after* lcd_tile_busy() returns 0.
 * Keep the same asynchronous contract. Never read an active tile after it
 * has been overwritten. Split a tile into DMA segments and repeat row 2 of
 * every 3 logical rows, preserving the original 240x240 GUI coordinates.
 * No 240x320 screen buffer or additional tile memory is necessary. */
static int tile_on;
static const uint16_t *tile_pixels;
static uint32_t tile_w, tile_h, tile_row, tile_group;
static int tile_repeat;
static void lcd_tile_next(void)
{
    const uint16_t *pixels;
    uint32_t bytes;
    if (tile_repeat) {
        tile_repeat = 0;
        pixels = tile_pixels + (tile_row - 1u) * tile_w;
        bytes = tile_w * 2u;
    } else if (tile_row < tile_h) {
        uint32_t n = tile_h - tile_row;
        if (n > tile_group) n = tile_group;
        pixels = tile_pixels + tile_row * tile_w;
        bytes = n * tile_w * 2u;
        tile_row += n;
        tile_repeat = n == tile_group;
        tile_group = 3u;
    } else {
        pin_set(LCD_CS, 1);
        tile_on = 0;
        return;
    }
    SPI1_CON &= ~(1u << 12);                /* SPI1 TX */
    SPI1_ADR = (uint32_t)(uintptr_t)pixels;
    SPI1_CNT = bytes;                       /* starts the next async segment */
}
void lcd_tile_start(int x, int y, int w, int h, const void *px)
{
    {   /* The previous tile must finish before the caller reuses its RAM. */
        uint32_t t0 = T0_CNT;
        while (lcd_tile_busy())
            if ((uint32_t)(T0_CNT - t0) > 30000u * lsb_mhz) {
                SPI1_CON |= 1u << 14;
                pin_set(LCD_CS, 1);
                tile_on = 0;
                break;
            }
    }
    int physical_y = lcd_y320(y), physical_h = lcd_y320(y + h) - physical_y;
    lcd_window(x, physical_y, w, physical_h);
    tile_pixels = (const uint16_t *)px;
    tile_w = (uint32_t)w;
    tile_h = (uint32_t)h;
    tile_row = 0u;
    tile_group = 3u - ((uint32_t)y % 3u);
    tile_repeat = 0;
    tile_on = 1;
    pin_set(LCD_DC, 1);
    pin_set(LCD_CS, 0);
    lcd_tile_next();
}
int lcd_tile_busy(void)
{
    if (!tile_on) return 0;
    if (!(SPI1_CON & (1u << 15))) return 1;
    SPI1_CON |= 1u << 14;                   /* acknowledge completed segment */
    lcd_tile_next();
    return tile_on;
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
print(f"Adapted {path} to ST7789 240x320 (2 inches), DMA tiles + boot text")

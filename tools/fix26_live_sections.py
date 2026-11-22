#!/usr/bin/env python3
"""Kitten FM-1: independent LITE / second drum track in live A-B-C-D scenes.
Run after the upstream Kitten patches, before compiling. Fails closed if upstream changes.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
def replace(rel, before, after):
    path=root/rel
    old=path.read_text()
    n=old.count(before)
    if n!=1:
        raise SystemExit(f"Scene fix: expected one match in {rel}; found {n}: {before[:110]!r}")
    path.write_text(old.replace(before,after,1))

proj="firmware/src/project.c"
store="firmware/src/kitten_store.c"
arr="firmware/src/arranger_scene.c"
main="firmware/src/main.c"

replace(proj,
    'static project_t autosave_buf __attribute__((section(".pool")));\n#include "kitten_store.c"',
    'static project_t autosave_buf __attribute__((section(".pool")));\n'
    '#include "kitten_store.c"')

# Declare the optional scene record in kitten_store.c itself, since the
# host storage tests include that source directly, outside project.c.
replace(store,
    '#define KS_MAGIC 0x4B534331u',
    'static const proj_trk_t *scene_extra_write_rec; /* null: capture working track */\n'
    '#define KS_MAGIC 0x4B534331u')

replace(store,
    "    memset(r, 0, sizeof *r);\n    proj_trk_capture(r, NHEAVY);",
    "    memset(r, 0, sizeof *r);\n"
    "    if (scene_extra_write_rec)\n"
    "        memcpy(r, scene_extra_write_rec, sizeof *r);\n"
    "    else\n"
    "        proj_trk_capture(r, NHEAVY);")
replace(store,
    "    memset(r, 0, sizeof *r);\n    proj_trk_capture(r, TRK_DRUM2);",
    "    memset(r, 0, sizeof *r);\n"
    "    if (scene_extra_write_rec)\n"
    "        memcpy(r, scene_extra_write_rec, sizeof *r);\n"
    "    else\n"
    "        proj_trk_capture(r, TRK_DRUM2);")

insert=r'''static proj_trk_t scene_extra[4][2];
static proj_trk_t song_extra[2];
static uint8_t scene_extra_valid[4];
static uint8_t scene_extra_dirty;

/* fix-26: the original project format has only tracks 1,2,3 and drum 1.
 * LITE and drum 2 need separate RAM copies for live A-D changes: flash reads
 * cannot run inside the audio interrupt at a scene boundary.
 * These are normal BSS; the NOINIT area is full of the original four sections.
 */

UI_SMALL static void scene_extra_capture(uint32_t s)
{
    s &= 3u;
    memset(&scene_extra[s], 0, sizeof scene_extra[s]);
    proj_trk_capture(&scene_extra[s][0], NHEAVY);
    proj_trk_capture(&scene_extra[s][1], TRK_DRUM2);
    drum_tw_pack(scene_extra[s][1].e, &drum_sts[1]);
    scene_extra_valid[s] = 3u;
    scene_extra_dirty |= (uint8_t)(1u << s);
}

UI_SMALL static void scene_extra_apply_pair(const project_t *p,
                                           const proj_trk_t *lite, const proj_trk_t *drum, uint32_t valid)
{
    if (valid & 1u)
        proj_apply_trk(p, NHEAVY, lite);
    if (valid & 2u) {
        proj_apply_trk(p, TRK_DRUM2, drum);
        drum_tw_unpack(drum->e, 1, &drum_sts[1]);
        TDRUM2->p[P_E1] = TDRUM2->p[P_E2] = TDRUM2->p[P_E3] = TDRUM2->p[P_E4] = 0;
        TDRUM2->p[P_E5] = TDRUM2->p[P_E6] = TDRUM2->p[P_E7] = 0;
    }
}
UI_SMALL static void scene_extra_apply(uint32_t s, const project_t *p)
{
    s &= 3u;
    scene_extra_apply_pair(p, &scene_extra[s][0], &scene_extra[s][1], scene_extra_valid[s]);
}


'''
replace(proj,
    '#ifndef PROJ_HOST\n#if FELUCCA_ARRANGER\n#include "arranger_scene.c"',
    insert+'#ifndef PROJ_HOST\n#if FELUCCA_ARRANGER\n#include "arranger_scene.c"')
boot=r'''/* Only at power-on, after persist_boot has read the original sections and
 * before autosave_resume restores the actual working project. */
UI_SMALL static void scene_extra_boot(void)
{
#if FELUCCA_FLASH
    uint32_t s;
    for (s = 0; s < 4u; s++) {
        if (!proj_ok(&proj_slot[s]))
            continue;
        if (ks_apply(s, &proj_slot[s]) == 0) {
            memset(&scene_extra[s][0], 0, sizeof scene_extra[s][0]);
            proj_trk_capture(&scene_extra[s][0], NHEAVY);
            scene_extra_valid[s] |= 1u;
        }
        if (kd_apply(s, &proj_slot[s]) == 0) {
            memset(&scene_extra[s][1], 0, sizeof scene_extra[s][1]);
            proj_trk_capture(&scene_extra[s][1], TRK_DRUM2);
            drum_tw_pack(scene_extra[s][1].e, &drum_sts[1]);
            scene_extra_valid[s] |= 2u;
        }
    }
#endif
}
'''
replace(proj,
    'static const char *const SEC_NAME[4] = {"A", "B", "C", "D"};',
    boot+'static const char *const SEC_NAME[4] = {"A", "B", "C", "D"};')

replace(proj,
    '    proj_capture(p);\n#if FELUCCA_FLASH\n    if (flash_ok) {',
    '    proj_capture(p);\n    scene_extra_capture(slot);\n#if FELUCCA_FLASH\n    if (flash_ok) {')
replace(proj,
    '    memset(&proj_slot[slot], 0, sizeof proj_slot[slot]);\n    sec_dirty &= (uint8_t)~(1u << slot);',
    '    memset(&proj_slot[slot], 0, sizeof proj_slot[slot]);\n'
    '    scene_extra_valid[slot] = 0;\n'
    '    scene_extra_dirty &= (uint8_t)~(1u << slot);\n'
    '    sec_dirty &= (uint8_t)~(1u << slot);')

replace(proj,
    '    proj_capture(&proj_slot[s]);\n    live_sec = (int8_t)s;',
    '    proj_capture(&proj_slot[s]);\n    scene_extra_capture(s);\n    live_sec = (int8_t)s;')
replace(proj,
    '    project_apply(&proj_slot[s]);\n    live_sec = (int8_t)s;',
    '    project_apply(&proj_slot[s]);\n'
    '    fm1_irq_off();\n'
    '    scene_extra_apply(s, &proj_slot[s]);\n'
    '    fm1_irq_on();\n'
    '    live_sec = (int8_t)s;')

replace(proj,
    '''        for (i = 0; i < 4u; i++)
            if (((sec_dirty >> i) & 1u) && st_save(OBJ_PROJECT0 + i, &proj_slot[i], sizeof proj_slot[i]) == 0)
                sec_dirty &= (uint8_t)~(1u << i);       /* (a failed write stays dirty: tried again later) */''',
    '''        for (i = 0; i < 4u; i++)
            if (((sec_dirty >> i) & 1u) && st_save(OBJ_PROJECT0 + i, &proj_slot[i], sizeof proj_slot[i]) == 0) {
                int rc = 0;
                if ((scene_extra_dirty >> i) & 1u) {
                    scene_extra_write_rec = &scene_extra[i][0];
                    rc = ks_write(i);
                    if (!rc) {
                        scene_extra_write_rec = &scene_extra[i][1];
                        rc = kd_write(i);
                    }
                    scene_extra_write_rec = 0;
                    if (!rc)
                        scene_extra_dirty &= (uint8_t)~(1u << i);
                }
                if (!rc)
                    sec_dirty &= (uint8_t)~(1u << i); /* retry full save if any extra part fails */
            }''')

replace(arr,
    '    proj_apply(&proj_slot[scene], 0);\n    sync_reload = 1;',
    '    proj_apply(&proj_slot[scene], 0);\n'
    '    scene_extra_apply(scene, &proj_slot[scene]);\n'
    '    sync_reload = 1;')

replace(arr,
    '    proj_capture(&song_keep);\n    song_kept = 1;',
    '''    proj_capture(&song_keep);
    memset(&song_extra, 0, sizeof song_extra);
    proj_trk_capture(&song_extra[0], NHEAVY);
    proj_trk_capture(&song_extra[1], TRK_DRUM2);
    drum_tw_pack(song_extra[1].e, &drum_sts[1]);
    song_kept = 1;''')

replace(arr,
    '    proj_apply(&song_keep, 1);\n    song.sel =',
    '    proj_apply(&song_keep, 1);\n'
    '    scene_extra_apply_pair(&song_keep, &song_extra[0], &song_extra[1], 3u);\n'
    '    song.sel =')

replace("tests/song_audio_test.c",
    "    printf(\"song audio: 3 synth parts + drums, section at %u, stop at %u, no held sequencer notes PASS\\n\",at_change,at_stop);",
    "    /* Regression: LITE (track 4) and drum 2 (track 6) must have different\n     * steps in A and B. Apply through the real arrangement scene loader. */\n    {\n        trk[NHEAVY].p[P_LEVEL] = 41;\n        trk[NHEAVY].step[0].n = 1;\n        trk[NHEAVY].step[0].time = ST_NOTE;\n        trk[NHEAVY].step[0].note[0] = 61;\n        TDRUM2->p[P_LEVEL] = 31;\n        TDRUM2->dstep[0].on[0] = 0x04u;\n        TDRUM2->dstep[0].on[1] = 0;\n        scene_extra_capture(0);\n\n        trk[NHEAVY].p[P_LEVEL] = 71;\n        trk[NHEAVY].step[0].note[0] = 74;\n        TDRUM2->p[P_LEVEL] = 81;\n        TDRUM2->dstep[0].on[0] = 0x10u;\n        scene_extra_capture(1);\n\n        arrangement_apply(0);\n        assert(trk[NHEAVY].p[P_LEVEL] == 41 &&\n               trk[NHEAVY].step[0].note[0] == 61 &&\n               TDRUM2->p[P_LEVEL] == 31 &&\n               TDRUM2->dstep[0].on[0] == 0x04u);\n\n        arrangement_apply(1);\n        assert(trk[NHEAVY].p[P_LEVEL] == 71 &&\n               trk[NHEAVY].step[0].note[0] == 74 &&\n               TDRUM2->p[P_LEVEL] == 81 &&\n               TDRUM2->dstep[0].on[0] == 0x10u);\n\n        arrangement_apply(0);\n        assert(trk[NHEAVY].step[0].note[0] == 61 &&\n               TDRUM2->dstep[0].on[0] == 0x04u);\n        printf(\"Kitten A/B: independent LITE and DRUM2 patterns PASS\\n\");\n    }\n\n    printf(\"song audio: 3 synth parts + drums, section at %u, stop at %u, no held sequencer notes PASS\\n\",at_change,at_stop);")

replace(main,
    '    song.master_q12 = 2048;\n    autosave_resume();',
    '    song.master_q12 = 2048;\n'
    '    scene_extra_boot();       /* hydrate the live A-D extras before restoring the working loop */\n'
    '    autosave_resume();')

# The program slot is nearly full: omit only the decorative spider web
# behind UI envelope/filter graphs. The graph itself and all controls remain.
gfx_ui = root / "firmware/src/ui_draw.c"
gfx_src = gfx_ui.read_text()
decor = "cv_web(C_LINE);"
if gfx_src.count(decor) < 1:
    raise SystemExit("Expected decorative graph-web call not present")
gfx_src = gfx_src.replace(decor, "/* decorative overlay omitted for scene memory */")
# Decorative skyline, moons and kittens on the header: do not display them.
# The user's actual synth menus, note indicators and 240x320 stretching stay.
# When these calls disappear the C compiler can omit the unused drawing routines.
import re
header_decor = re.compile(r"(?m)^    cv_(?:roofs|cat)\([^;\n]*\);[^\n]*$")
calls = header_decor.findall(gfx_src)
if len(calls) != 6:
    raise SystemExit(f"Expected 3 skyline and 3 cat calls, got {len(calls)}")
gfx_src = header_decor.sub("    /* optional Kitten header art omitted to free program flash */", gfx_src)
gfx_ui.write_text(gfx_src)

print("Scene fix applied to", root)
print("Removed", len(calls), "decorative cat and skyline calls; ST7789 240x320 scaling preserved")

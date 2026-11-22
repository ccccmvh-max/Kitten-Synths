# SLOOP 3.4.1 beta — M-Vave FM-1 con pantalla ST7789 de 2″ (240 × 320)

**Adaptación no oficial de [SLOOP 3.4.1 de isod89](https://github.com/isod89/sloop3-fm1/releases/tag/v3.4.1-beta).** Mantiene las funciones originales de SLOOP 3 y aprovecha toda la altura de una pantalla ST7789 de 2 pulgadas, sustituyendo a la pantalla del FM-1.

**Confirmación de hardware:** la adaptación fue probada en un FM-1 equipado con esa pantalla; su usuario confirmó que funcionaba. Aun así, se publica como *beta / experimental*: no se ha comprobado su compatibilidad con todos los módulos de pantalla o variantes del FM-1.

### Modificaciones

- Interfaz lógica de 240 × 240 ampliada verticalmente a **240 × 320**, duplicando una de cada tres filas.
- Controlador ST7789 corregido para direccionar píxeles por encima de la fila 255.
- Bloques gráficos dibujados a 120 × 12 filas lógicas y ampliados a 120 × 16 **en el mismo búfer**, sin añadir memoria RAM.
- Conservada la transmisión SPI1 DMA, el motor de audio, los cinco canales, ocho patrones por pista, los efectos y los visualizadores.
- Animación gráfica de arranque sustituida por un título sencillo para respetar el espacio reservado a las muestras.

**No es Kitten 3:** esta versión tiene **cuatro sintetizadores y una batería**; no añade la segunda batería ni el motor MUUG de Kitten.

### Archivos adjuntos

- **`instalador-SLOOP3-240x320-EXPERIMENTAL.html`** — instalador autocontenido; abrir localmente con Chrome o Edge.
- **`sloop3-3.4.1-240x320-EXPERIMENTAL.area`** — área de firmware para desarrolladores / herramientas compatibles.
- **`editor-SLOOP3-3.4.1.html`** — editor web de SLOOP 3.
- **`LEEME.md`** — instrucciones y detalles técnicos.

### Instalación — importante

SLOOP 3 utiliza **m-bootloader en MIDI MODE**, no el actualizador `.fwsc` de SLOOP 2/Kitten ni M-UPGRADE. Antes de instalar:

1. Haz una copia de seguridad **completa** del FM-1 (memoria flash, proyectos, presets y muestras), por ejemplo con M-Flasher.
2. Confirma que puedes acceder a m-bootloader / MIDI MODE.
3. Abre el **instalador HTML adjunto** en Chrome o Edge; sigue sus indicaciones.
4. Guarda una copia de tu firmware Kitten anterior y de tu copia de seguridad por si necesitas volver.

**No uses el instalador oficial de SLOOP 3 sin modificar para esta pantalla:** no incluye esta adaptación a 240 × 320.

### Compilación y créditos

Basada en el código original de SLOOP 3.4.1 beta, `isod89/sloop3-fm1`, commit `f48b4c8`.

**[Compilación comprobada en GitHub Actions](https://github.com/ccccmvh-max/Kitten-Synths/actions/runs/44979299063)** · **[Código fuente de la adaptación](https://github.com/ccccmvh-max/Kitten-Synths/tree/sloop3-240x320/sloop3_240x320)**

Superadas las pruebas de geometría de la pantalla, las pruebas de SLOOP 3 en PC y la compilación cruzada pi32v2. Las pruebas con simulación de instalación/editor en Chromium se desactivaron para esa compilación; no se afirma que hayan pasado.

Créditos del firmware original: **isod89 y colaboradores**. Software libre GPL-3.0; esta es una modificación comunitaria independiente, no una actualización oficial ni un producto de M-VAVE.

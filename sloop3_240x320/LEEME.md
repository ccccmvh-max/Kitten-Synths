# SLOOP 3.4.1 beta para pantalla ST7789 de 2 pulgadas

**Versión experimental, no oficial.** Basada en [SLOOP 3 de isod89](https://github.com/isod89/sloop3-fm1), versión `v3.4.1-beta`. Esta rama del repositorio es **independiente de Kitten 2.8** y no modifica su código.

## Qué hace

Adapta el controlador ST7789 del FM-1 para una pantalla física de **240 × 320 píxeles**. La interfaz de SLOOP 3 mantiene las coordenadas lógicas de 240 × 240 y se **estira verticalmente**, tal como la adaptación de Kitten para la misma pantalla: por cada tres filas originales se dibuja una fila adicional.

- La pantalla de arranque y rescate también ocupa los 320 píxeles de alto.
- Se conserva la transmisión por DMA no bloqueante que usa SLOOP 3; los bloques se envían por segmentos, repitiendo las filas necesarias.
- La corrección del registro ST7789 incluye el byte alto de las coordenadas para alcanzar las filas físicas 256–319.
- No se cambia ninguna función de síntesis, secuenciador, MIDI ni guardado.

**SLOOP 3 original tiene cuatro pistas de sintetizador y una batería.** Esta versión **no añade MUUG ni la segunda batería de Kitten**. El objetivo de esta rama es únicamente la pantalla.

## Archivos

- `instalador-SLOOP3-240x320-EXPERIMENTAL.html`: instalador con el firmware integrado para abrir en Chrome o Edge.
- `sloop3-3.4.1-240x320-EXPERIMENTAL.area`: área de aplicación sin encapsular, para herramientas avanzadas compatibles con m-bootloader.
- `editor-SLOOP3-3.4.1.html`: editor web de SLOOP 3.
- `sloop3_240x320/adapt_screen.py`: transforma exclusivamente el controlador `hal/fm1/board.c` de la versión fijada.
- `sloop3_240x320/test_screen.py`: comprueba la correspondencia de filas, la repetición y las coordenadas 0–319.

## Instalación y advertencias

**No instales esta versión hasta que compile y supere las pruebas y tengas una copia completa de seguridad del FM-1.** El resultado aún deberá comprobarse en un dispositivo con la pantalla de 2 pulgadas.

SLOOP 3 se instala con **m-bootloader, modo MIDI MODE**, y **no utiliza el formato `.fwsc` de Kitten/SLOOP 2**. No uses M-UPGRADE ni el instalador anterior de Kitten para el archivo `.area`. Consulta el procedimiento oficial y las medidas de recuperación en [SLOOP 3](https://github.com/isod89/sloop3-fm1/blob/main/README.md) y [m-bootloader](https://github.com/jvitkauskas/m-bootloader).

Antes de sustituir Kitten:

1. Haz una copia completa de la memoria del FM-1 con una herramienta compatible, como M-Flasher, y conserva el firmware Kitten que funciona.
2. Comprueba que **m-bootloader está instalado** y que puedes acceder a MIDI MODE.
3. Usa el archivo HTML del paquete experimental solo después de confirmar la compilación y sus resultados.
4. Si falla el encendido o el cambio de firmware, restaura desde la copia completa con las herramientas correspondientes.

SLOOP 3 puede leer algunos datos heredados de SLOOP 2.8, pero **no se ha comprobado que recupere los proyectos modificados de Kitten con sus pistas adicionales**. No confíes en la importación automática para conservar esos datos.

## Notas técnicas

El controlador de SLOOP 3 usa DMA de SPI1 y tiles de 120 × 16. La función `lcd_tile_busy()` debe seguir devolviendo «ocupado» hasta terminar **todos** los segmentos y duplicaciones de filas: el renderizador reutiliza el mismo búfer inmediatamente después. Por eso no sirve copiar directamente el parche de la pantalla de Kitten 2.8.

La conversión vertical de coordenadas es `Y_física = Y_lógica + floor(Y_lógica / 3)`. Para el origen de la ventana y para su final se usa la misma función, de forma que se alcanzan exactamente 320 filas.

**Créditos:** trabajo original de isod89 y colaboradores, [SLOOP 3](https://github.com/isod89/sloop3-fm1), licencia GPL-3.0. Modificación experimental de pantalla realizada en esta rama con arreglo a esa licencia.

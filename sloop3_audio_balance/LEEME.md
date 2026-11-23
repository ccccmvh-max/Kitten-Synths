# SLOOP 3.4.1 – corrección experimental de mezcla (FM-1, ST7789 de 2″)

Esta versión es **una prueba independiente** de la [adaptación para pantalla 240 × 320 que ya funciona](https://github.com/ccccmvh-max/Kitten-Synths/releases/tag/sloop3-v3.4.1-st7789-240x320-beta1). **No reemplaza esa Release**.

## Problemas que intenta corregir

- Los instrumentos melódicos de las pistas 1–4 suenan demasiado bajos frente a la batería.
- La batería (pista 5) suena mucho más alta y puede distorsionar cuando se sube ligeramente el nivel.

Usuarios del SLOOP 3 original notificaron problemas parecidos en los [issues #16](https://github.com/isod89/sloop3-fm1/issues/16), [#18](https://github.com/isod89/sloop3-fm1/issues/18) y [#26](https://github.com/isod89/sloop3-fm1/issues/26). Estos reportes **no demuestran** por sí solos que toda distorsión tenga el mismo origen.

## Cambios respecto a nuestra versión funcional

1. **Baterías:** `GB_DRUM_GAIN` de 1,50 a **0,75** (−6,02 dB). Se reduce el nivel desde el motor de batería, antes de insertos, mezclador, efectos y limitador.
2. **Bombos:** ganancia extra de 1,41 a **1,10** (−2,16 dB adicionales). Aumenta el margen para los picos más potentes.
3. **Kits de muestras GM/USR:** su coeficiente de ganancia se reduce de 2,43 a **1,80** (−2,61 dB adicionales) para compensar su mayor volumen relativo frente a los kits sintetizados.
4. **Sintetizadores:** la ganancia de tira en la mezcla aumenta moderadamente de 1,00 a **1,05** (+0,42 dB), después de sintetizar y antes del sumador; se mantiene el DUCK.
5. **Sin subir el volumen maestro/DAC:** permanece la ganancia máxima original, el limitador de −1 dBFS, las funciones de audio USB, los efectos, las cinco pistas y el motor de síntesis original.
6. **Pantalla sin cambios:** ST7789 de 2 pulgadas y 240 × 320, con imagen estirada como en nuestra versión confirmada.

Son ajustes conservadores y **no aplican compresión adicional ni recortan las ondas de batería**. Se ha mantenido el código fuente de la versión funcional; los cambios se aplican solo en la compilación de esta rama.

## Validación

GitHub Actions compila SLOOP 3.4.1 beta a partir del código original fijado, compara el volumen de sus sonidos y baterías **antes y después** del ajuste usando el motor real en PC, ejecuta la batería de pruebas y genera un instalador HTML con el firmware modificado.

**No instalar hasta ver la ejecución completamente en verde.** La compilación y las pruebas de PC no sustituyen a escuchar el dispositivo real: puede seguir existiendo distorsión de la etapa de salida del FM-1, del altavoz, de un efecto del proyecto o de muestras previamente saturadas.

## Para probar sin perder el firmware bueno

1. Haz copia de seguridad completa de la memoria del FM-1 y guarda el instalador de la versión estable para ti.
2. En el FM-1, revisa `HOME mantenido → AUDIO → SPEAKER LOWCUT`. Para auriculares/salida de línea, debe estar en **OFF**; en el altavoz interno puede ser útil activarlo. Esta opción cambia el tono y puede cambiar la percepción del grave.
3. Antes de instalar cualquier nueva versión, guarda tus proyectos en el editor de SLOOP 3.
4. Tras instalar, escucha el **mismo patrón** con el mismo nivel de MASTER y pista y sin FX INSERT, DIST ni DUCK, primero con auriculares y luego por el altavoz. Compara especialmente si la batería distorsiona cuando aumentas su nivel.
5. Si el resultado empeora, recupera la versión anterior desde su Release. **Esta prueba no modifica la versión anterior de GitHub.**

Usa m-bootloader (MIDI MODE) y el instalador HTML generado, **no** M-UPGRADE ni un archivo `.fwsc`.

### Autoría

Basado en [SLOOP 3](https://github.com/isod89/sloop3-fm1) por isod89 y colaboradores (GPL-3.0), con nuestra adaptación de pantalla y un experimento independiente de ganancia para investigar el problema de las pistas. No es un parche oficial del autor original.

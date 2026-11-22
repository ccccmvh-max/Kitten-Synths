# Adaptación experimental de Kitten Synths para M-Vave FM-1

Este documento explica **qué cambia en esta bifurcación (fork)** respecto a [Kitten Synths de Black Kitten Devices](https://github.com/BlackKittenDevices/Kitten-Synths), cómo se construye y cuáles son sus limitaciones. **No es una versión oficial de Kitten Synths.**

[Volver al README principal](README.md) · [Ver compilaciones y pruebas](https://github.com/ccccmvh-max/Kitten-Synths/actions/workflows/build.yml)

## 1. ¿Para qué sirve este proyecto?

El **M-Vave FM-1** es un pequeño sintetizador/secuenciador. El firmware libre **SLOOP** amplía sus funciones; **Kitten Synths 2.8**, desarrollado por Black Kitten Devices a partir de SLOOP, añade un cuarto sintetizador ligero (**LITE**), una segunda pista de batería, el motor **MUUG** y otras herramientas.

Esta bifurcación persigue dos objetivos concretos:

1. **Aprovechar una pantalla ST7789 de 2 pulgadas y 240 × 320 píxeles**, instalada en sustitución de la pantalla original. No se rediseñan los menús: la imagen de 240 × 240 se **estira verticalmente** para ocupar la altura adicional, incluso si sus proporciones quedan deformadas.
2. **Conseguir que las pistas 4 (LITE) y 6 (batería 2) mantengan patrones diferentes en las secciones A, B, C y D**, tanto al cargar una sección con la reproducción detenida como al pasar de una a otra mientras suena el secuenciador.

La adaptación de pantalla se ha probado con éxito en un FM-1 real. **La corrección de las secciones sigue siendo experimental**: que el firmware compile no demuestra por sí solo que sus cambios de sección sean fiables en el hardware.

## 2. Qué es Kitten Synths y qué se ha modificado

| Elemento | Kitten Synths original | Esta bifurcación |
| --- | --- | --- |
| Base musical | SLOOP 2.8 y parches de Kitten | Se conserva |
| Pistas | 4 sintes (incluida LITE) y 2 baterías | Se conservan |
| Motor MUUG, MIDI y audio USB | Incluidos en Kitten | Se conservan |
| Pantalla prevista | Interfaz de 240 × 240 | Salida estirada a **240 × 320** para una pantalla ST7789 compatible |
| Secciones A–D | El código de las pistas añadidas usa almacenamiento separado | Se desarrolla una corrección para que **LITE y batería 2** cambien de patrón con cada sección |
| Estado de validación | Depende de las pruebas del proyecto original | La corrección de secciones **no está validada**; consultar Actions |

**Importante:** cambiar el tamaño de la pantalla físicamente no garantiza que cualquier módulo ST7789 funcione; deben coincidir la conexión y la configuración del hardware. Esta adaptación está pensada para el dispositivo concreto ya probado, no para todos los módulos de 2 pulgadas.

## 3. ¿Qué problema tienen las pistas 4 y 6?

El comportamiento comunicado fue el siguiente:

- Se crea un patrón en la **sección A** de la pista **4 (LITE)** o la pista **6 (segunda batería)**.
- Se pasa a **B**, **C** o **D** y se modifica ese patrón.
- Al regresar a otra sección, estas pistas **no recuperan el patrón propio**: los cambios parecen compartirse entre las cuatro secciones.
- Las pistas convencionales utilizan otro mecanismo de almacenamiento y no presentan necesariamente este problema.

### Causa observada en el código

El formato de proyecto heredado de SLOOP guarda directamente **las pistas 1–3 y la batería 1**. Kitten añadió datos para LITE y la segunda batería en objetos separados de la memoria flash: **`OBJ_KITTEN`** y **`OBJ_KITDRUM`**.

Las rutas habituales de guardar/cargar proyectos pueden utilizar **`ks_write()` / `ks_apply()`** y **`kd_write()` / `kd_apply()`**. Sin embargo, el cambio rápido de sección utiliza otras funciones (`section_store()`, `section_load()` y `arrangement_apply()`) que originalmente no restauraban esos dos registros adicionales.

### Enfoque de la corrección experimental

El archivo [`tools/fix26_live_sections.py`](tools/fix26_live_sections.py) aplica cambios después de los parches de Kitten para:

- Mantener en **RAM** una copia del estado de **LITE** y **batería 2** para cada sección A–D.
- Recuperar dichas copias al cambiar de sección, sin hacer lecturas de flash desde la interrupción de audio.
- Mantener una copia temporal de esas pistas al comenzar el modo canción y recuperarlas al terminar.
- Volcar a flash los datos modificados cuando el transporte esté detenido.
- Recuperar los datos guardados al arrancar.
- Incorporar una prueba de regresión al simulador que verifica **patrones diferentes en A y B**, y comprueba el regreso a A.

Este diseño todavía requiere pruebas completas de integración, persistencia, cambios durante la reproducción y uso real. La prueba no cubre por sí sola todas las condiciones de cuatro secciones ni un corte de alimentación durante un guardado.

## 4. Adaptación a la pantalla de 2 pulgadas

La modificación gráfica se encuentra en [`fix-25.patch`](fix-25.patch), aplicado después de los parches originales. Su finalidad es reproducir la misma interfaz de Kitten, pero **escalada verticalmente de 240 a 320 líneas**.

No intenta aumentar la cantidad de controles ni reorganizar páginas. El usuario ha probado satisfactoriamente la adaptación en su FM-1 con una ST7789 de 2 pulgadas.

**La corrección de las pistas 4 y 6 debe conservar este parche.** Una versión de Kitten sin `fix-25.patch` no es equivalente a la compilación adaptada para la pantalla.

## 5. Cómo se construye

La automatización [`.github/workflows/build.yml`](.github/workflows/build.yml):

1. Descarga SLOOP en un commit fijo.
2. Aplica `muug.patch` y los `fix-*.patch` de Kitten en orden, incluido `fix-25.patch`.
3. Aplica `tools/fix26_live_sections.py`, que introduce la corrección de secciones y la prueba correspondiente.
4. Compila el firmware para el FM-1 y comprueba la memoria disponible.
5. Ejecuta las pruebas del firmware y del editor web. **Si falla una prueba, la ejecución debe terminar con error.**
6. Si las fases pertinentes terminan correctamente, genera el paquete `.fwsc` y los demás artefactos.

Se publica un artefacto `kitten-fm1-240x320-fwsc` inmediatamente después de compilar, **antes de que terminen las pruebas**. Por tanto, **que ese archivo exista NO significa que la versión esté validada**. Consultar el resultado completo de GitHub Actions antes de instalar.

### Estado conocido de las pruebas

En la ejecución del **22 de noviembre de 2026**, la compilación del firmware terminó correctamente, pero la batería de pruebas falló porque el test de almacenamiento de Kitten no encontraba la declaración `scene_extra_write_rec`. Este fallo está en la integración de las nuevas modificaciones con el banco de pruebas. **La corrección de pistas 4 y 6 aún no puede considerarse lista** hasta resolverlo y repetir las pruebas.

[Consultar el estado actualizado de Actions](https://github.com/ccccmvh-max/Kitten-Synths/actions/workflows/build.yml). El estado puede cambiar después de publicar este documento.

Además, la última compilación comprobada disponía de un margen muy pequeño en la memoria de programa (72 bytes), por lo que cualquier cambio adicional requiere volver a verificar el tamaño.

## 6. Instalación sin Python (cuando exista una versión validada)

Se puede utilizar un instalador web independiente compatible con archivos `.fwsc`:

**[fm-static: instalador web para M-Vave FM-1](https://seajaysec.github.io/fm-static/)**

En Chrome o Edge, se selecciona el archivo `.fwsc`, se comprueba la identidad del firmware y se conecta el FM-1 por USB. Antes de escribir hay que realizar **una copia de seguridad de proyectos, muestras, presets y ajustes**, y conservar un firmware funcional para recuperación.

No se recomienda instalar las compilaciones experimentales mientras las pruebas generales fallen. No activar opciones de borrado de datos sin conocer sus consecuencias.

El paso automatizado para activar GitHub Pages se eliminó del flujo porque el token de GitHub Actions no disponía de permisos (`403`). **La ausencia de GitHub Pages no impide descargar y comprobar el artefacto `.fwsc` desde Actions**. La publicación de Pages, si se necesita, debe configurarse aparte en **Settings → Pages**, seleccionando la rama `gh-pages`.

## 7. Ayuda para comprobar el problema

Para revisar o reproducir el comportamiento, registrar:

- Firmware exacto y versión, incluida la adaptación 240 × 320.
- Contenido diferente de LITE y batería 2 en A y B; probar también C y D.
- Si el cambio se realizó con la reproducción detenida o en marcha.
- Si el problema aparece al **cambiar de sección**, al **guardar/apagar**, o en ambos casos.
- Avisos de guardado en pantalla, por ejemplo `LITE TOO BIG` o `SAVED, DRUMS 2 NOT`.
- Resultado de las pruebas de GitHub Actions y, en caso de error, el extracto del registro.

No confundir el fallo del secuenciador con la **grabación de las seis pistas por USB al ordenador**: son funciones distintas.

## 8. Créditos y licencia

Esta es una **adaptación experimental no oficial** de [Kitten Synths](https://github.com/BlackKittenDevices/Kitten-Synths), construido sobre [SLOOP](https://github.com/isod89/sloop-fm1), [Felucca](https://github.com/hugelton/Felucca) y el motor procedente de [FMini-1](https://github.com/ruppert/fmini-1).

Se mantienen los créditos y la licencia **GPL-3.0** del proyecto. Véanse [`CREDITOS.md`](CREDITOS.md) y [`LICENSE`](LICENSE). Las modificaciones de esta bifurcación no deben atribuirse a los autores originales como si fueran una actualización oficial.

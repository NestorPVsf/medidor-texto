# medidor-texto

Una skill de Claude Code que mide cuánto suena a máquina un texto en español o inglés, y que **falla con código de salida distinto de 0** si no llega a los umbrales. Sirve para no dar por bueno un post, un correo o un DM sin haberlo medido.

Hecha por Néstor Martínez ([@casi_nestor](https://instagram.com/casi_nestor)). MIT.

## Qué resuelve

Un borrador con tics de IA se nota en tres segundos y casi nadie lo ve al escribirlo. Una lista de reglas en un prompt se olvida a mitad de la sesión. Esto es un script: lo ejecuta el agente, devuelve un número y dice qué check es el más flojo. Todo corre en local, sin red y sin enviar el texto a ningún sitio. Solo usa la librería estándar de Python 3.

Cinco checks, cada uno de 0 a 100:

| Check | Qué mira | Cuenta para |
|---|---|---|
| VARIEDAD | variación de la longitud de las frases | nota total |
| CONCRECION | cifras y nombres propios por 100 palabras (desde 90 palabras) | nota total |
| RELLENO | palabras y frases de relleno de IA, con lista propia por idioma | puerta |
| HUELLA | caracteres invisibles, rayas, comillas curvas, `…`, espacios duros | puerta |
| VOZ | estructuras como «no es X, es Y», cohetes y hashtags, tríos por reflejo, pronombres | puerta |

Pasa si la nota total es 50 o más y RELLENO, HUELLA y VOZ llegan a 55. VARIEDAD y CONCRECION no vetan por sí solos: un mensaje corto y bueno no lleva cifras ni nombres, y un post con frases de la misma longitud puede ser deliberado.

## Instalación

Necesitas Python 3 y Claude Code. Clona el repo dentro de tus skills:

```bash
git clone https://github.com/NestorPVsf/medidor-texto ~/.claude/skills/medidor-texto
bash ~/.claude/skills/medidor-texto/medidor-texto.check.sh
```

La segunda línea ejecuta 12 casos de regresión y debe acabar en `medidor-texto.check: TODO OK`. En Windows funciona desde Git Bash; si solo tienes `python`, el check lo detecta.

Después, en Claude Code, pídele «mide este texto con medidor-texto» o ejecútalo tú:

```bash
python3 -I ~/.claude/skills/medidor-texto/medir.py borrador.txt
cat borrador.txt | python3 -I ~/.claude/skills/medidor-texto/medir.py -
python3 -I ~/.claude/skills/medidor-texto/medir.py borrador.txt --json --lang es
```

Códigos de salida: `0` pasa, `1` no pasa, `2` no se pudo medir (menos de 8 palabras; no es un verde).

## Ejemplo real

Entrada (`tests/es-malo.txt`, las primeras líneas):

```text
En el panorama actual, la inteligencia artificial marca un antes y un después en la forma de trabajar de las empresas.

No se trata de herramientas, sino de una transformación holística. Cabe destacar que las soluciones de última generación, potentes y escalables, permiten optimizar procesos...
```

Salida:

```text
  VARIEDAD    #################.......  69.8   variacion 0.56 en 8 frases (se quiere 0.55+)
  CONCRECION  ........................   0.0   0 marcas concretas, 0.0 por 100 palabras (se quiere 4+)
  RELLENO     ........................   0.0   9 terminos de relleno, 9.8 por 100 palabras (aquí está la clave, cabe destacar, de última generación, holística, ...)
  HUELLA      ######################## 100.0   0 invisibles, 0 rayas, 0 comillas curvas, 0 puntos suspensivos unicode, 0 espacios duros
  VOZ         ###########.............  44.8   0.0 pronombres personales por 100 palabras, 2 patron(es) de estructura [no-es-sino, emoji-cohete]
  NOTA        ######..................  25.8   NO PASA

  Check mas flojo: RELLENO. Arreglalo primero y vuelve a medir.
```

Exit 1. Se reescribe con un caso concreto (el ejemplo es inventado) y se vuelve a medir. La primera versión mejoró el relleno pero todas las frases medían casi lo mismo:

```text
  VARIEDAD    ........................   0.0   variacion 0.10 en 4 frases (se quiere 0.55+)
  NOTA        ##########..............  42.0   NO PASA
```

Se rompió el ritmo con una frase de tres palabras y otra larga:

```text
En una gestoría de cuatro personas tardaban tres días en cuadrar las facturas de cada mes. Probaron un script que lee los PDF y los ordena por proveedor. Una tarde. Eso es lo que tarda ahora, y el viernes ya no se queda nadie hasta las nueve. Tecleaban unos 200 apuntes por semana. Hoy revisan solo los dudosos, que rondan los veinte.
```

```text
  VARIEDAD    ######..................  26.2   variacion 0.35 en 5 frases (se quiere 0.55+)
  RELLENO     ######################## 100.0   0 terminos de relleno, 0.0 por 100 palabras
  NOTA        ##############..........  56.4   PASA
```

## Cómo se probó

`medidor-texto.check.sh` tiene 12 casos: textos buenos en español e inglés que deben pasar, textos con relleno burdo y sutil que deben fallar, el mismo texto bueno con relleno añadido a mano (para comprobar que el rojo es posible), un texto casi vacío que debe dar exit 2 y la entrada por stdin. Para comprobar que el check puede fallar, se vaciaron las listas de relleno y estructuras: salieron 3 casos en rojo. Probado en Windows 11 con Git Bash y Python 3.13.

## Límites

- Un verde dice que el texto no tiene las señales que mide. No dice que sea bueno ni que lo haya escrito una persona.
- Las muestras malas de `tests/` las escribió el autor conociendo las listas, así que prueban que el cableado funciona, no la potencia real contra IA bien editada.
- Los umbrales salen de textos de un solo autor. Si un texto tuyo bueno falla, abre un issue con el texto: es un caso nuevo para el check.

## Origen y licencia

`medir.py` es una adaptación de `detect.py` de [Jakeschincariol/linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill) (MIT, © 2026 Jake Schincariol), y `slop.json` es su lista en inglés con tres estructuras añadidas. Los cambios de Néstor: lectura de fichero y stdin, códigos de salida, detección de idioma, la lista `slop.es.json` en español, números escritos con letra y la separación entre puerta y nota. La lista en español parte de un checklist anti-slop en español y de la traducción de entradas de [blader/humanizer](https://github.com/blader/humanizer) (MIT). Ver `LICENSE`.

## English summary

I built this Claude Code skill so an agent can't call a draft finished without measuring it. It scores how machine-written a Spanish or English text sounds (five checks, 0 to 100) and exits non-zero when the text misses the thresholds. It's local, stdlib-only Python 3, with no network. Install it with `git clone https://github.com/NestorPVsf/medidor-texto ~/.claude/skills/medidor-texto`, then run `bash ~/.claude/skills/medidor-texto/medidor-texto.check.sh` (12 cases, you want `TODO OK`). Exit codes: 0 pass, 1 fail, 2 couldn't measure. I adapted it from an MIT-licensed detector by Jake Schincariol; the Spanish lexicon, the exit codes and the calibration are mine. A green means the text lacks the tells it checks for. It doesn't mean the text is good.

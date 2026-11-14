---
name: medidor-texto
description: Mide de 0 a 100 cuánto suena a máquina un texto en español o inglés (post, correo, DM, comentario) y falla con código de salida distinto de 0 si no llega a los umbrales. Usar antes de dar por bueno un texto que vaya a leer una persona, o cuando un borrador suene genérico, plano o "a IA". No reescribe nada por sí solo.
license: MIT
---

# medidor-texto

Un medidor local, sin red, que puntúa un texto con cinco checks y dice cuál es el más flojo. Lo usas tú, el agente, como puerta: no declaras "listo" un texto sin haberlo medido.

## Cuándo usarlo

- Acabas de escribir o reescribir un texto para una persona (post, correo, DM, comentario).
- El usuario pide "que no suene a IA" o "revisa este borrador".
- Antes de entregar cualquier cosa que se vaya a publicar o enviar.

No sirve para código, tablas ni guiones que se dicen en voz alta (la puntuación y las viñetas pesan distinto al hablar).

## Cómo se ejecuta

Guarda el texto en un fichero temporal y mídelo. La ruta de instalación es `~/.claude/skills/medidor-texto/`.

```bash
python3 -I ~/.claude/skills/medidor-texto/medir.py borrador.txt
cat borrador.txt | python3 -I ~/.claude/skills/medidor-texto/medir.py -
python3 -I ~/.claude/skills/medidor-texto/medir.py borrador.txt --json --lang es
```

En Windows usa `python` en lugar de `python3`. El idioma se detecta solo; `--lang es|en` lo fuerza.

## Códigos de salida

| Exit | Significa | Qué haces |
|---|---|---|
| 0 | pasa | puedes darlo por medido, no por perfecto |
| 1 | no pasa | arregla el check más flojo y mide otra vez |
| 2 | no se pudo medir (menos de 8 palabras) | no es un verde: di que no se midió |

## Qué mide

| Check | Mira | Pesa en |
|---|---|---|
| VARIEDAD | variación de la longitud de las frases | nota total |
| CONCRECION | cifras y nombres propios por 100 palabras (solo desde 90 palabras) | nota total |
| RELLENO | palabras y frases de relleno de IA (lista por idioma) | puerta |
| HUELLA | invisibles, rayas, comillas curvas, `…`, espacios duros | puerta |
| VOZ | estructuras tipo "no es X, es Y", cohetes, tríos por reflejo, pronombres | puerta |

Pasa si la nota total es 50 o más y RELLENO, HUELLA y VOZ llegan a 55.

## Bucle de arreglo

1. Mide. Si sale 0, para.
2. Lee la línea del check más flojo. Arregla ese y solo ese: RELLENO se arregla cambiando la frase por un hecho concreto, no por un sinónimo; VARIEDAD, mezclando frases cortas y largas; VOZ, quitando la estructura que marca.
3. Mide otra vez. Máximo tres rondas. Si sigue en rojo, entrega el texto con el check que falla señalado, sin maquillar el medidor.

## Límites que debes decir

- Un verde no prueba que el texto sea bueno ni que lo haya escrito una persona. Solo dice que no tiene las señales que mide.
- No se debe subir una nota copiando trucos del medidor (quitar rayas, meter cifras inventadas). Una cifra solo entra si es real.
- Los umbrales están calibrados con textos de un solo autor. Si un texto bueno falla de forma clara, es un caso nuevo para el check, no motivo para bajar el umbral a ciegas.

## Comprobar que la instalación funciona

```bash
bash ~/.claude/skills/medidor-texto/medidor-texto.check.sh
```

Debe acabar en `medidor-texto.check: TODO OK` (12 casos). Si algo falla, la instalación está rota.

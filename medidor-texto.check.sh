#!/usr/bin/env bash
# Check de regresion del medidor de texto. Sale 0 SOLO si:
#   - un texto bueno (ES y EN, largo y corto) pasa,
#   - un texto con relleno de IA (ES y EN, burdo y sutil) falla,
#   - el mismo texto bueno, con relleno de IA anadido a mano, falla (el rojo era posible),
#   - un texto vacio da exit 2 ("no se pudo medir" no es verde),
#   - stdin funciona.
# Uso: bash medidor-texto.check.sh
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
export PYTHONIOENCODING=utf-8
fallos=0

esperar() { # esperar <exit esperado> <descripcion> <comando...>
  local want="$1" desc="$2"; shift 2
  local salida got
  salida="$("$@" 2>&1)"; got=$?
  if [ "$got" = "$want" ] && [ -n "$salida" ]; then
    echo "OK    $desc (exit $got, ${#salida} bytes de salida)"
  else
    echo "FALLO $desc (exit $got, esperado $want, ${#salida} bytes)"; fallos=$((fallos+1))
  fi
}

M() { "$PY" -I "$HERE/medir.py" "$@"; }

esperar 0 "ES bueno largo (post con cifras)"       M "$HERE/tests/es-bueno.txt"
esperar 0 "ES bueno corto (comentario corto)" M "$HERE/tests/es-bueno-corto.txt"
esperar 0 "EN bueno (mensaje personal EN)"           M "$HERE/tests/en-bueno.txt"
esperar 1 "ES con relleno de IA"                 M "$HERE/tests/es-malo.txt"
esperar 1 "ES con relleno sutil (ritmo plano)"   M "$HERE/tests/es-malo-sutil.txt"
esperar 1 "EN con relleno de IA"                 M "$HERE/tests/en-malo.txt"
esperar 1 "EN con relleno sutil (ritmo plano)"   M "$HERE/tests/en-malo-sutil.txt"

# El rojo era posible: el texto bueno + una tanda de relleno en cada idioma tiene que caer.
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
cp "$HERE/tests/es-bueno.txt" "$tmp"
printf '\n\nEn el panorama actual, cabe destacar que es una solucion robusta, escalable y de ultima generacion. Seamos honestos: marca un antes y un despues.\n' >> "$tmp"
esperar 1 "ES bueno + relleno anadido a mano" M "$tmp"
cp "$HERE/tests/en-bueno.txt" "$tmp"
printf '\n\nIn today'"'"'s fast-paced landscape, a robust, seamless, cutting-edge solution is a game-changer. Let'"'"'s face it: it'"'"'s not just a tool, it'"'"'s a mindset.\n' >> "$tmp"
esperar 1 "EN bueno + relleno anadido a mano" M "$tmp"

esperar 2 "texto casi vacio = no se pudo medir" bash -c "printf 'hola' | \"$PY\" -I \"$HERE/medir.py\" -"
esperar 1 "stdin: ES malo por tuberia" bash -c "cat \"$HERE/tests/es-malo.txt\" | \"$PY\" -I \"$HERE/medir.py\" -"
esperar 0 "stdin: ES bueno por tuberia" bash -c "cat \"$HERE/tests/es-bueno.txt\" | \"$PY\" -I \"$HERE/medir.py\" -"

if [ "$fallos" = 0 ]; then echo "medidor-texto.check: TODO OK"; exit 0; fi
echo "medidor-texto.check: $fallos FALLO(S)"; exit 1

#!/usr/bin/env python3
"""
medir.py - medidor de texto "escrito por maquina" (ES/EN), de 0 a 100 por check.

Adaptado de li-human/detect.py (Jakeschincariol/linkedin-agent-skill, MIT, ver LICENSE).
Cambios respecto al original:
  - acepta fichero o stdin, y SALE CON CODIGO != 0 por debajo de los umbrales;
  - detecta el idioma (es/en) y usa la lista propia de cada idioma (slop.json / slop.es.json);
  - un check que no puede juzgar (texto corto) NO cuenta (el original le daba 50 y hundia el minimo);
  - texto vacio o casi vacio = exit 2 ("no se pudo medir" no es verde).

Todo se calcula en local con el texto. No hay red, ni subprocesos, ni escritura de ficheros.

Uso
  python3 -I medir.py texto.txt
  cat texto.txt | python3 -I medir.py -
  python3 -I medir.py texto.txt --json --lang es

Salida: exit 0 = PASA, 1 = NO PASA (nota total o un check por debajo del umbral), 2 = no se pudo medir.
"""

import argparse
import json
import os
import re
import statistics
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

# Umbrales calibrados con texto propio publicado (ver README.md, apartado Calibracion).
# Puerta: RELLENO, HUELLA y VOZ (lexico y estructuras: senales inequivocas) deben llegar a MIN_DURO.
# VARIEDAD y CONCRECION solo suman a la nota total: los posts y mensajes buenos ya publicados sacan
# 21 y 27 en ellas (frases de longitud pareja a proposito, mensajes sin cifras por regla), asi que no pueden vetar.
MIN_TOTAL = 50.0
MIN_DURO = 55.0
DUROS = ["RELLENO", "HUELLA", "VOZ"]

LETTERS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")
WORD_RE = re.compile("[" + LETTERS + "']+")
CONTRACTIONS = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
PRONOUNS_EN = re.compile(r"\b(i|me|my|mine|we|us|our|you|your)\b", re.IGNORECASE)
PRONOUNS_ES = re.compile(
    r"\b(yo|me|mi|mis|mí|conmigo|nos|nuestro|nuestra|nuestros|nuestras|tú|te|tu|tus|ti|contigo|"
    r"vosotros|os|vuestro|vuestra|vuestros|vuestras|usted|ustedes)\b", re.IGNORECASE)
NUMBERS = re.compile(r"\b\d[\d,.]*%?|[$€£]\d")
NUMWORDS = re.compile(
    r"\b(?:dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|cuarenta|"
    r"cincuenta|cien|ciento|mil|millón|millones|two|three|four|five|six|seven|eight|nine|ten|twelve|"
    r"twenty|thirty|fifty|hundred|thousand|million)\b", re.IGNORECASE)
SPEC_MIN_WORDS = 90  # por debajo de esto la concrecion no distingue (un DM corto no lleva cifras ni nombres)
PROPER = re.compile(
    r"(?<![.!?¿¡]\s)(?<![¿¡])(?<!^)\b[A-ZÁÉÍÓÚÑ][a-záéíóúüñ]{2,}\b", re.MULTILINE)

ES_STOP = set("de la que el en y a los se del las por un para con no una su al lo como más pero sus le ya o este "
              "sí porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante "
              "tu te es son está vi tengo vuestro vuestra cuál qué cómo".split())
EN_STOP = set("the of and to in is that it for as with was on are be this by at from or have an not but they "
              "which you your we our i my has had were been their what when can will would about more".split())


def clamp(n):
    return max(0.0, min(100.0, n))


def scale(value, human, machine):
    """value -> 0-100 donde `human` = 100 y `machine` = 0."""
    if human == machine:
        return 50.0
    return clamp((value - machine) / (human - machine) * 100)


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]


def words(text):
    return WORD_RE.findall(text)


def detect_lang(text):
    ws = [w.lower() for w in words(text)]
    es = sum(1 for w in ws if w in ES_STOP) + 3 * len(re.findall(r"[¿¡ñ]", text))
    en = sum(1 for w in ws if w in EN_STOP)
    return "es" if es > en else "en"


def load_lex(lang):
    name = "slop.es.json" if lang == "es" else "slop.json"
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def entries(lex):
    return lex.get("words", []) + lex.get("phrases", [])


def pattern_for(find):
    # \b delante y detras; los espacios casan con cualquier blanco. Con acentos usa lookarounds de letra.
    body = re.escape(find).replace(r"\ ", r"\s+")
    return re.compile(r"(?<![" + LETTERS + r"])" + body + r"(?![" + LETTERS + r"])", re.IGNORECASE)


# Cada check devuelve (nota 0-100 o None si no puede juzgar, detalle)

def check_burstiness(text, lang):
    lens = [len(s.split()) for s in sentences(text)]
    if len(lens) < 4:
        return None, "demasiado corto para juzgar"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    return scale(cv, human=0.70, machine=0.22), f"variacion {cv:.2f} en {len(lens)} frases (se quiere 0.55+)"


def check_specificity(text, lang):
    w = words(text)
    if len(w) < SPEC_MIN_WORDS:
        return None, f"menos de {SPEC_MIN_WORDS} palabras: no se juzga"
    hits = len(NUMBERS.findall(text)) + len(NUMWORDS.findall(text)) + len(set(PROPER.findall(text)))
    density = hits * 100 / len(w)
    return scale(density, human=6.0, machine=0.5), f"{hits} marcas concretas, {density:.1f} por 100 palabras (se quiere 4+)"


def check_slop(text, lang, lex):
    w = words(text)
    if not w:
        return None, "vacio"
    hits, found = 0, []
    for e in entries(lex):
        n = len(pattern_for(e["find"]).findall(text))
        if n:
            hits += n
            found.append(e["find"])
    density = hits * 100 / len(w)
    detail = f"{hits} terminos de relleno, {density:.1f} por 100 palabras"
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return scale(density, human=0.0, machine=4.0), detail


def check_fingerprint(text, lang):
    invisible = sum(1 for c in text if unicodedata.category(c) == "Cf")
    em = text.count("—")
    curly = sum(text.count(c) for c in "‘’“”")  # las comillas «» del español NO cuentan
    ellip = text.count("…")
    nbsp = sum(text.count(c) for c in (chr(0xA0), chr(0x202F), chr(0x2009)))
    total = invisible * 4 + em * 2 + curly + ellip + nbsp
    per1k = total * 1000 / max(len(text), 1)
    detail = (f"{invisible} invisibles, {em} rayas, {curly} comillas curvas, "
              f"{ellip} puntos suspensivos unicode, {nbsp} espacios duros")
    return scale(per1k, human=0.0, machine=12.0), detail


def check_voice(text, lang, lex):
    w = words(text)
    if len(w) < 25:
        return None, "demasiado corto para juzgar"
    per100 = 100 / len(w)
    tells, names = 0, []
    for s in lex.get("structures", []):
        try:
            n = len(re.compile(s["regex"], re.MULTILINE).findall(text))
        except re.error:
            continue
        if n:
            tells += n
            names.append(s["id"])
    bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
    uniform = len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6
    if lang == "es":
        person = len(PRONOUNS_ES.findall(text)) * per100
        # En espanol el sujeto se omite: el pronombre pesa poco y su ausencia no castiga.
        score = scale(person, human=3.0, machine=0.0) * 0.2 + clamp(100 - tells * 22) * 0.8
        detail = f"{person:.1f} pronombres personales por 100 palabras, {tells} patron(es) de estructura"
    else:
        contractions = len(CONTRACTIONS.findall(text)) * per100
        person = len(PRONOUNS_EN.findall(text)) * per100
        score = (scale(contractions, human=3.0, machine=0.0) * 0.35
                 + scale(person, human=8.0, machine=1.0) * 0.35
                 + clamp(100 - tells * 22) * 0.30)
        detail = (f"{contractions:.1f} contracciones, {person:.1f} pronombres personales por 100 palabras, "
                  f"{tells} patron(es) de estructura")
    if uniform:
        score -= 12
        names.append("vinetas-uniformes")
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


CHECKS = ["VARIEDAD", "CONCRECION", "RELLENO", "HUELLA", "VOZ"]


def run(text, lang, lex):
    res = {
        "VARIEDAD": check_burstiness(text, lang),
        "CONCRECION": check_specificity(text, lang),
        "RELLENO": check_slop(text, lang, lex),
        "HUELLA": check_fingerprint(text, lang),
        "VOZ": check_voice(text, lang, lex),
    }
    scores = [v[0] for v in res.values() if v[0] is not None]
    # El check mas flojo arrastra la nota: un detector solo necesita una senal.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4
    duros = [res[c][0] for c in DUROS if res[c][0] is not None]
    return res, overall, min(duros)


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def main():
    ap = argparse.ArgumentParser(description="Mide cuanto suena a maquina un texto (ES/EN).")
    ap.add_argument("input", nargs="?", default="-", help="fichero o - para stdin")
    ap.add_argument("--lang", choices=["auto", "es", "en"], default="auto")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-total", type=float, default=MIN_TOTAL)
    ap.add_argument("--min-duro", type=float, default=MIN_DURO,
                    help="minimo de RELLENO, HUELLA y VOZ (la puerta)")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raw = sys.stdin.buffer.read() if args.input == "-" else open(args.input, "rb").read()
    text = raw.decode("utf-8-sig", errors="replace")
    if len(words(text)) < 8:
        print("NO SE PUDO MEDIR: menos de 8 palabras. Esto no es un verde.", file=sys.stderr)
        sys.exit(2)

    lang = detect_lang(text) if args.lang == "auto" else args.lang
    res, overall, weakest = run(text, lang, load_lex(lang))
    ok = overall >= args.min_total and weakest >= args.min_duro
    verdict = "PASA" if ok else "NO PASA"

    if args.json:
        print(json.dumps({
            "lang": lang, "nota": round(overall, 1), "minimo_duro": round(weakest, 1), "veredicto": verdict,
            "checks": {k: {"nota": None if v[0] is None else round(v[0], 1), "detalle": v[1]}
                       for k, v in res.items()},
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\nMEDIDOR DE TEXTO ({lang})  -  umbrales: nota >= {args.min_total:g}; RELLENO, HUELLA y VOZ >= {args.min_duro:g}")
        print("=" * 66)
        for name in CHECKS:
            score, detail = res[name]
            if score is None:
                print(f"  {name:<11} {'(sin juzgar)':<24}   {detail}")
            else:
                print(f"  {name:<11} {bar(score)} {score:5.1f}   {detail}")
        print("-" * 66)
        print(f"  {'NOTA':<11} {bar(overall)} {overall:5.1f}   {verdict}")
        if not ok:
            judged = {k: v for k, v in res.items() if v[0] is not None}
            duros = {k: v for k, v in judged.items() if k in DUROS}
            weak = min(duros, key=lambda c: duros[c][0]) if weakest < args.min_duro else min(judged, key=lambda c: judged[c][0])
            print(f"\n  Check mas flojo: {weak}. Arreglalo primero y vuelve a medir.")
        print()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

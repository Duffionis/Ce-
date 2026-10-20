#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compila ed esegue ogni blocco ```ce del tutorial e confronta con il blocco ```uscita che segue.
Uso: python3 tests/prova_tutorial.py [--mostra]   (--mostra stampa le uscite vere)"""
import os, re, subprocess, sys, tempfile

QUI = os.path.dirname(os.path.abspath(__file__))
CE = os.path.join(QUI, "..", "ce.py")
DOC = os.path.join(QUI, "..", "docs", "TUTORIAL.md")


def blocchi(testo):
    pat = re.compile(r"```(ce|ce-panico)\n(.*?)```(?:\s*\n```uscita\n(.*?)```)?", re.S)
    return [(m.group(2), m.group(3), m.group(1) == "ce-panico") for m in pat.finditer(testo)]


def main():
    mostra = "--mostra" in sys.argv
    testo = open(DOC, encoding="utf-8").read()
    ok = ko = 0
    for i, (codice, atteso, panico) in enumerate(blocchi(testo), 1):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "prova.ce")
            open(p, "w", encoding="utf-8").write(codice)
            r = subprocess.run([sys.executable, CE, "esegui", p], capture_output=True, text=True,
                               cwd=os.path.join(QUI, ".."))
        if mostra:
            print(f"--- blocco {i} (exit {r.returncode})\n{r.stdout}{r.stderr}")
            continue
        if panico:
            giusto = r.returncode == 101 and "fuori dai limiti" in r.stderr
        else:
            giusto = r.returncode == 0 and (atteso is None or r.stdout.rstrip() == atteso.rstrip())
        if giusto:
            ok += 1
            print(f"ok       tutorial, blocco {i}")
        else:
            ko += 1
            print(f"FALLITO  tutorial, blocco {i}: exit {r.returncode}\n  atteso: {atteso!r}\n  ottenuto: {r.stdout!r} {r.stderr[:300]}")
    if not mostra:
        print(f"\n{ok} riusciti, {ko} falliti")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())

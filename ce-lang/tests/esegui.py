#!/usr/bin/env python3
"""Esegue tests/*.ce. Direttive nei commenti:
   //> riga      riga attesa su stdout
   //! testo      deve fallire in compilazione con questo testo
   //# testo      deve andare in 'panico' (exit 101) con questo testo
Uso: python3 tests/esegui.py [filtro]"""
import glob
import os
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
CE = os.path.join(os.path.dirname(QUI), "ce.py")


def attese(path):
    out, err, pan = [], None, None
    with open(path, encoding="utf-8") as f:
        for riga in f:
            r = riga.rstrip("\n")
            if r.startswith("//>"):
                t = r[3:]
                out.append((t[1:] if t.startswith(" ") else t).rstrip())
            elif r.startswith("//!"):
                err = r[3:].strip()
            elif r.startswith("//#"):
                pan = r[3:].strip()
    return out, err, pan


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    ok = ko = 0
    for path in sorted(glob.glob(os.path.join(QUI, "*.ce"))):
        nome = os.path.basename(path)
        if filtro not in nome:
            continue
        out, err, pan = attese(path)
        r = subprocess.run([sys.executable, CE, "run", path],
                           capture_output=True, text=True)
        got = [x.rstrip() for x in r.stdout.splitlines()]
        problema = None
        if err is not None:
            if r.returncode != 1 or err not in r.stderr:
                problema = f"atteso errore '{err}' (exit 1), ottenuto exit {r.returncode}: {r.stderr.strip()[:200]}"
        elif pan is not None:
            if r.returncode != 101 or pan not in r.stderr:
                problema = f"atteso panico '{pan}' (exit 101), ottenuto exit {r.returncode}: {r.stderr.strip()[:200]}"
        else:
            if r.returncode != 0:
                problema = f"exit {r.returncode}: {r.stderr.strip()[:300]}"
            elif got != out:
                problema = f"output diverso\n    atteso: {out}\n    ottenuto: {got}"
        if problema:
            ko += 1
            print(f"FALLITO  {nome}\n    {problema}")
        else:
            ok += 1
            print(f"ok       {nome}")
    print(f"\n{ok} riusciti, {ko} falliti")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())

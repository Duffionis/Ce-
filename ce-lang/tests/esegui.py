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
    out, err, pan, no = [], [], None, []
    with open(path, encoding="utf-8") as f:
        for riga in f:
            r = riga.rstrip("\n")
            if r.startswith("//>"):
                t = r[3:]
                out.append((t[1:] if t.startswith(" ") else t).rstrip())
            elif r.startswith("//!-"):
                no.append(r[4:].strip())
            elif r.startswith("//!"):
                err.append(r[3:].strip())
            elif r.startswith("//#"):
                pan = r[3:].strip()
    return out, err, pan, no


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    ok = ko = 0
    for path in sorted(glob.glob(os.path.join(QUI, "*.ce"))):
        nome = os.path.basename(path)
        if filtro not in nome:
            continue
        out, err, pan, no = attese(path)
        r = subprocess.run([sys.executable, CE, "run", path],
                           capture_output=True, text=True)
        got = [x.rstrip() for x in r.stdout.splitlines()]
        problema = None
        if err:
            mancanti = [x for x in err if x not in r.stderr]
            presenti = [x for x in no if x in r.stderr]
            if r.returncode != 1 or mancanti or presenti:
                problema = (f"atteso errore {err} (exit 1), non deve esserci {no}; ottenuto exit "
                            f"{r.returncode}: {r.stderr.strip()[:400]}")
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
    # --- strumenti: formattatore, --debug, -l ---
    if filtro in ("", "strumenti"):
        sys.path.insert(0, os.path.dirname(QUI))
        from formatta import formatta
        sporco = open(os.path.join(QUI, "formato", "sporco.ce"), encoding="utf-8").read()
        pulito = open(os.path.join(QUI, "formato", "pulito.ce"), encoding="utf-8").read()
        prove = []
        prove.append(("formatta: sporco -> pulito", formatta(sporco) == pulito))
        prove.append(("formatta: e' idempotente", formatta(pulito) == pulito))
        tutti = glob.glob(os.path.join(QUI, "*.ce")) + glob.glob(os.path.join(QUI, "..", "lib", "*.ce"))
        parole = lambda t: "".join(t.split())
        prove.append(("formatta: non cambia le parole",
                      all(parole(formatta(open(f, encoding="utf-8").read())) ==
                          parole(open(f, encoding="utf-8").read()) for f in tutti)))
        r = subprocess.run([sys.executable, CE, "esegui", os.path.join(QUI, "formato", "collegamento.ce"), "-l", "m"],
                           capture_output=True, text=True)
        prove.append(("opzione -l m", r.returncode == 0 and r.stdout.strip() == "9"))
        r = subprocess.run([sys.executable, CE, "esegui", os.path.join(QUI, "t07_funzioni.ce"), "--debug"],
                           capture_output=True, text=True)
        prove.append(("opzione --debug", r.returncode == 0))
        for nome, bene in prove:
            if bene:
                ok += 1
                print(f"ok       {nome}")
            else:
                ko += 1
                print(f"FALLITO  {nome}")
    print(f"\n{ok} riusciti, {ko} falliti")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())

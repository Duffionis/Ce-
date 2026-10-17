#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ce++ - uso:
    ce.py tokens|ast|emit file.ce
    ce.py build file.ce [-o uscita] [--sanitizza]
    ce.py run   file.ce [--sanitizza] [argomenti...]"""
import os
import shutil
import subprocess
import sys
import tempfile
from lessico import ErroreCe, lessico, VERSIONE
from sintassi import analizza, mostra
from genera import genera

FLAG = ["-std=gnu11", "-O2", "-fwrapv", "-fno-strict-aliasing",
        "-fno-delete-null-pointer-checks", "-fstack-protector-strong",
        "-Wall", "-Wno-unused", "-Wno-missing-braces", "-Wno-parentheses"]


def carica(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def a_c(path):
    return genera(analizza(lessico(carica(path))), path)


def cerca_cc():
    if os.environ.get("CC"):
        return os.environ["CC"]
    for c in ("gcc", "clang", "cc"):
        if shutil.which(c):
            return c
    return None


def compila(path, out, san):
    csrc = a_c(path)
    cpath = out + ".c"
    with open(cpath, "w", encoding="utf-8") as f:
        f.write(csrc)
    cc = cerca_cc()
    if not cc:
        print("errore: non trovo un compilatore C (gcc o clang)", file=sys.stderr)
        return 3
    cmd = [cc] + FLAG
    if san:
        cmd += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    cmd += [cpath, "-o", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERRORE INTERNO: il C generato non compila (bug del compilatore Ce++)", file=sys.stderr)
        print(" ".join(cmd), file=sys.stderr)
        print(r.stderr, file=sys.stderr)
        return 3
    if r.stderr.strip():
        sys.stderr.write(r.stderr)
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "--version":
        print("Ce++", VERSIONE)
        return 0
    if len(argv) < 3 or argv[1] not in ("tokens", "ast", "emit", "build", "run"):
        print(__doc__)
        return 2
    cmd, path, resto = argv[1], argv[2], argv[3:]
    san = "--sanitizza" in resto
    resto = [x for x in resto if x != "--sanitizza"]
    try:
        if cmd == "tokens":
            for t in lessico(carica(path)):
                print(t)
        elif cmd == "ast":
            mostra(analizza(lessico(carica(path))))
        elif cmd == "emit":
            sys.stdout.write(a_c(path))
        elif cmd == "build":
            out = resto[resto.index("-o") + 1] if "-o" in resto else "a.out"
            return compila(path, out, san)
        else:
            tmp = tempfile.mkdtemp(prefix="ce_")
            try:
                exe = os.path.join(tmp, "prog")
                rc = compila(path, exe, san)
                if rc:
                    return rc
                sys.stdout.flush()
                return subprocess.call([exe] + resto)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    except ErroreCe as e:
        print(f"{path}:{e.riga}: errore: {e.msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

# -*- coding: utf-8 -*-
"""Ce++: carica un programma e i moduli che importa con  usa "file.ce";

Ogni modulo e' caricato una sola volta. I percorsi sono relativi al file che
scrive 'usa'. Un percorso che comincia con '@' (usa "@testo.ce";) si cerca nella
libreria standard del compilatore (cartella lib/) e poi nelle cartelle elencate
nella variabile d'ambiente CE_PERCORSO (separate da ':'). Tutti i moduli finiscono nello stesso spazio dei nomi: se due
file definiscono lo stesso nome, e' un errore (niente nascondere).
"""
import os
from lessico import ErroreCe, ErroriCe, lessico
from sintassi import analizza


LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")


def risolvi(base, nome):
    """Percorso reale di un modulo, o None se non si trova."""
    if nome.startswith("@"):
        resto = nome[1:]
        cartelle = [LIB] + [d for d in os.environ.get("CE_PERCORSO", "").split(":") if d]
        for d in cartelle:
            c = os.path.join(d, resto)
            if os.path.isfile(c):
                return c
        return None
    c = os.path.join(os.path.dirname(base), nome)
    return c if os.path.isfile(c) else None


def carica_programma(path):
    """Ritorna la lista di tutti gli elementi (funzioni, strutture, costanti)
    del programma, dai moduli importati in su. Ogni elemento sa il suo file."""
    visti, pila, out = set(), [], []

    def vai(p):
        rp = os.path.realpath(p)
        visti.add(rp)
        pila.append(rp)
        with open(p, encoding="utf-8") as f:
            src = f.read()
        try:
            items = analizza(lessico(src))
        except ErroreCe as e:
            if e.file is None:
                e.file = p
            raise
        except ErroriCe as ee:
            for e in ee.errori:
                if e.file is None:
                    e.file = p
            raise
        for it in items:
            if it.k != "usa":
                it.file = p
                out.append(it)
                continue
            sub = risolvi(p, it.path) or os.path.join(os.path.dirname(p), it.path)
            rs = os.path.realpath(sub)
            if rs in pila:
                giro = " -> ".join(os.path.basename(x) for x in pila[pila.index(rs):] + [rs])
                raise ErroreCe(f"dipendenza circolare tra moduli: {giro}", it.line, p)
            if not os.path.isfile(sub):
                raise ErroreCe(f"il modulo '{it.path}' non esiste", it.line, p)
            if rs not in visti:
                vai(sub)
        pila.pop()

    vai(path)
    return out

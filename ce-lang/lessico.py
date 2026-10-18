#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ce++ - piccolo linguaggio di sistema, sicuro e italiano. Compila in C."""
import re
import sys

VERSIONE = "0.1.0"


class ErroreCe(Exception):
    def __init__(self, msg, riga=0, file=None):
        super().__init__(msg)
        self.msg, self.riga, self.file = msg, riga, file


# ===== LESSICO: qui vivono tutte le parole del linguaggio =====
PAROLE_CHIAVE = {
    "funzione", "struttura", "variabile", "costante", "se", "altrimenti",
    "mentre", "per", "in", "ritorna", "interrompi", "continua",
    "vero", "falso", "rischio", "esterna", "come", "usa", "rimanda",
    "impacchettata",
}

# Parole inglesi vietate: danno un errore che spiega come si scrive in Ce++.
INGLESE = {
    "if": "se", "else": "altrimenti", "while": "mentre", "for": "per",
    "return": "ritorna", "break": "interrompi", "continue": "continua",
    "struct": "struttura", "true": "vero", "false": "falso",
    "const": "costante", "let": "variabile", "var": "variabile",
    "fn": "funzione", "defer": "rimanda", "packed": "impacchettata", "func": "funzione", "function": "funzione",
    "extern": "esterna", "unsafe": "rischio", "as": "come",
    "void": "vuoto", "int": "intero", "bool": "booleano",
    "char": "carattere", "float": "decimale", "double": "doppio",
    "string": "testo",
}

TOK = re.compile(r'''
 (?P<ws>[ \t\r]+)
|(?P<nl>\n)
|(?P<lc>//[^\n]*)
|(?P<bc>/\*.*?\*/)
|(?P<num>0[xX][0-9A-Fa-f_]+|0[bB][01_]+|\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d+)?|\d[\d_]*(?:[eE][+-]?\d+)?)
|(?P<str>"(?:\\.|[^"\\\n])*")
|(?P<chr>'(?:\\.|[^'\\\n])+')
|(?P<id>[^\W\d]\w*)
|(?P<op><<=|>>=|\.\.|->|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|%=|&=|\|=|\^=|[-+*/%&|^~!<>=(){}\[\];:,.])
''', re.X | re.S)

ESC = {"n": 10, "t": 9, "r": 13, "0": 0, "\\": 92, '"': 34, "'": 39}


def decodifica(s, riga):
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 1
            if i >= len(s):
                raise ErroreCe("sequenza di escape incompleta", riga)
            e = s[i]
            if e in ESC:
                out.append(ESC[e])
            elif e == "x":
                h = s[i + 1:i + 3]
                if len(h) != 2 or any(x not in "0123456789abcdefABCDEF" for x in h):
                    raise ErroreCe("\\x vuole due cifre esadecimali", riga)
                out.append(int(h, 16))
                i += 2
            else:
                raise ErroreCe(f"escape sconosciuto: \\{e}", riga)
        else:
            out += c.encode("utf-8")
        i += 1
    return bytes(out)


def leggi_numero(t):
    s = t.replace("_", "")
    if s[:2] in ("0x", "0X"):
        return (int(s, 16), False)
    if s[:2] in ("0b", "0B"):
        return (int(s, 2), False)
    if "." in s or "e" in s or "E" in s:
        return (float(s), True)
    return (int(s), False)


def lessico(src):
    """Trasforma il sorgente in token: (tipo, valore, riga)."""
    toks, pos, riga = [], 0, 1
    while pos < len(src):
        m = TOK.match(src, pos)
        if not m:
            raise ErroreCe(f"carattere inatteso {src[pos]!r}", riga)
        k, t = m.lastgroup, m.group()
        pos = m.end()
        if k == "nl":
            riga += 1
        elif k == "bc":
            riga += t.count("\n")
        elif k in ("ws", "lc"):
            pass
        elif k == "num":
            toks.append(("num", leggi_numero(t), riga))
        elif k == "str":
            toks.append(("str", decodifica(t[1:-1], riga), riga))
        elif k == "chr":
            b = decodifica(t[1:-1], riga)
            if len(b) != 1:
                raise ErroreCe("un carattere letterale deve essere un solo byte", riga)
            toks.append(("chr", b[0], riga))
        elif k == "id":
            if t in INGLESE:
                raise ErroreCe(f"'{t}' e' inglese: in Ce++ si scrive '{INGLESE[t]}'", riga)
            toks.append(("kw" if t in PAROLE_CHIAVE else "id", t, riga))
        else:
            toks.append(("op", t, riga))
    toks.append(("eof", "", riga))
    return toks



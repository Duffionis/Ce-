# -*- coding: utf-8 -*-
"""Ce++: formattatore. Rimette in ordine i rientri (4 spazi per livello), toglie gli
spazi a fine riga e riduce le righe vuote consecutive a una. Non cambia le parole:
solo gli spazi all'inizio e alla fine delle righe. Non sposta le parentesi graffe."""

RIENTRO = "    "


def _scansiona(riga, in_blocco):
    """Conta (aperte, chiuse, tonde_nette, in_blocco) ignorando stringhe e commenti.
    'aperte'/'chiuse' sono le { } della riga; 'tonde_nette' = ( [ aperte meno chiuse."""
    aperte = chiuse = tonde = 0
    i, n = 0, len(riga)
    primo_chiude = False       # la riga comincia con una '}'?
    visto_qualcosa = False
    while i < n:
        c = riga[i]
        if in_blocco:
            j = riga.find("*/", i)
            if j < 0:
                return aperte, chiuse, tonde, True, primo_chiude
            i, in_blocco = j + 2, False
            continue
        if c == "/" and i + 1 < n and riga[i + 1] == "/":
            break
        if c == "/" and i + 1 < n and riga[i + 1] == "*":
            in_blocco = True
            i += 2
            continue
        if c in "\"'":
            q, i = c, i + 1
            while i < n and riga[i] != q:
                i += 2 if riga[i] == "\\" else 1
            i += 1
            visto_qualcosa = True
            continue
        if c == "{":
            aperte += 1
        elif c == "}":
            if not visto_qualcosa:
                primo_chiude = True
            chiuse += 1
        elif c in "([":
            tonde += 1
        elif c in ")]":
            tonde -= 1
        if not c.isspace():
            visto_qualcosa = True
        i += 1
    return aperte, chiuse, tonde, in_blocco, primo_chiude


def formatta(testo):
    out, livello, tonde, in_blocco, vuote = [], 0, 0, False, 0
    for grezza in testo.replace("\r\n", "\n").split("\n"):
        riga = grezza.strip()
        if not riga:
            vuote += 1
            if vuote == 1 and out:
                out.append("")
            continue
        vuote = 0
        if in_blocco:
            # dentro un commento /* ... */ si lasciano le righe come sono (meno gli spazi finali)
            out.append(grezza.rstrip())
            _, _, _, in_blocco, _ = _scansiona(riga, True)
            continue
        aperte, chiuse, dt, nuovo_blocco, primo_chiude = _scansiona(riga, False)
        liv = livello - (1 if primo_chiude else 0)
        extra = 1 if tonde > 0 else 0          # continuazione di una parentesi aperta prima
        if tonde < 0:
            tonde = 0
        out.append(RIENTRO * max(liv + extra, 0) + riga)
        livello = max(livello + aperte - chiuse, 0)
        tonde = max(tonde + dt, 0)
        in_blocco = nuovo_blocco
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"

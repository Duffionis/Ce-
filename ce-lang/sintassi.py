# -*- coding: utf-8 -*-
"""Ce++: dal flusso di token all'albero del programma."""
from lessico import ErroreCe, ErroriCe

PRIMS = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize",
         "f32", "f64", "bool", "void"}
ALIAS_TIPI = {"intero": "i32", "lungo": "i64", "corto": "i16", "byte": "u8",
              "carattere": "u8", "decimale": "f32", "doppio": "f64",
              "booleano": "bool", "vuoto": "void", "dimensione": "usize",
              "intero8": "i8", "intero16": "i16", "intero32": "i32", "intero64": "i64",
              "naturale8": "u8", "naturale16": "u16", "naturale32": "u32",
              "naturale64": "u64", "reale32": "f32", "reale64": "f64"}
# nome italiano con cui i tipi interni compaiono nei messaggi
NOME_IT = {"i8": "intero8", "i16": "intero16", "i32": "intero", "i64": "lungo",
           "u8": "byte", "u16": "naturale16", "u32": "naturale32", "u64": "naturale64",
           "usize": "dimensione", "f32": "decimale", "f64": "doppio",
           "bool": "booleano", "void": "vuoto"}
TESTO = ("s", ("p", "u8"))          # testo = fetta di byte

ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}
BINPREC = {"||": 1, "&&": 2, "==": 3, "!=": 3, "<": 4, ">": 4, "<=": 4, ">=": 4,
           "|": 5, "^": 6, "&": 7, "<<": 8, ">>": 8, "+": 9, "-": 9,
           "*": 10, "/": 10, "%": 10}


class N:
    """Nodo dell'albero: tipo k, riga, e attributi liberi."""
    def __init__(s, k, line, **kw):
        s.k, s.line = k, line
        s.__dict__.update(kw)


def mostra(x, ind=0, nome=""):
    p = "  " * ind + (nome + ": " if nome else "")
    if isinstance(x, N):
        print(p + f"{x.k} (riga {x.line})")
        for k, v in x.__dict__.items():
            if k not in ("k", "line"):
                mostra(v, ind + 1, k)
    elif isinstance(x, list):
        print(p + ("[]" if not x else "["))
        for v in x:
            mostra(v, ind + 1)
        if x:
            print("  " * ind + "]")
    else:
        print(p + repr(x))


class Parser:
    def __init__(s, toks):
        s.t, s.i, s.nostruct, s.consts = toks, 0, 0, {}
        s.errs = []        # errori di sintassi trovati finora (si continua a leggere)

    # ----- utilita' -----
    @property
    def tok(s):
        return s.t[s.i]

    def peek(s, o=1):
        return s.t[min(s.i + o, len(s.t) - 1)]

    def desc(s):
        k, v, _ = s.tok
        if k == "eof":
            return "la fine del file"
        if k in ("op", "kw", "id"):
            return f"'{v}'"
        return "un valore"

    def e(s, msg):
        raise ErroreCe(msg, s.tok[2])

    def is_(s, v):
        t = s.tok
        return t[0] in ("op", "kw") and t[1] == v

    def acc(s, v):
        if s.is_(v):
            s.i += 1
            return True
        return False

    def exp(s, v):
        if not s.acc(v):
            s.e(f"atteso '{v}', trovato {s.desc()}")

    def ident(s):
        t = s.tok
        if t[0] != "id":
            s.e(f"atteso un nome, trovato {s.desc()}")
        s.i += 1
        return t[1]

    def seq(s, close, fn):
        ns, s.nostruct, out = s.nostruct, 0, []
        while not s.is_(close):
            out.append(fn())
            if not s.acc(","):
                break
        s.exp(close)
        s.nostruct = ns
        return out

    def const_val(s, n):
        if n.k == "num" and not n.isf:
            return n.val
        if n.k == "un" and n.op == "-" and n.e.k == "num" and not n.e.isf:
            return -n.e.val
        if n.k == "id":
            return s.consts.get(n.name)
        return None

    # ----- livello superiore -----
    INIZI = ("funzione", "struttura", "costante", "variabile", "elenco", "esterna", "usa")

    def programma(s):
        items = []
        while s.tok[0] != "eof":
            i0 = s.i
            try:
                it = s.item()
                items.extend(it if isinstance(it, list) else [it])
            except ErroreCe as e:
                s.errs.append(e)
                s.salta(i0)
        if s.errs:
            if len(s.errs) == 1:
                raise s.errs[0]
            raise ErroriCe(s.errs[:30])
        return items

    def salta_istr(s):
        """Dopo un errore dentro un blocco: riparte dopo il prossimo ';' (o alla '}' che chiude)."""
        depth = 0
        while s.tok[0] != "eof":
            k, v, _ = s.tok
            if k == "op" and v == ";" and depth == 0:
                s.i += 1
                return
            if k == "op" and v == "{":
                depth += 1
            elif k == "op" and v == "}":
                if depth == 0:
                    return
                depth -= 1
            s.i += 1

    def salta(s, i0):
        """Dopo un errore: riparte dal prossimo elemento di primo livello."""
        depth, j = 0, i0
        while s.t[j][0] != "eof":
            k, v, _ = s.t[j]
            if k == "op" and v == "{":
                depth += 1
            elif k == "op" and v == "}":
                depth = max(0, depth - 1)
            elif j > i0 and depth == 0 and k == "kw" and v in s.INIZI:
                break
            j += 1
        s.i = j

    def item(s):
        ln = s.tok[2]
        if s.acc("usa"):
            t = s.tok
            if t[0] != "str":
                s.e(f"dopo 'usa' ci vuole il nome di un file tra virgolette, trovato {s.desc()}")
            s.i += 1
            s.exp(";")
            return N("usa", ln, path=t[1].decode("utf-8", "replace"))
        if s.acc("esterna"):
            s.exp("funzione")
            f = s.firma(ln)
            if f.tparams:
                s.e("una funzione 'esterna' (C) non puo' essere generica")
            f.extern, f.body = True, None
            s.exp(";")
            return f
        if s.acc("funzione"):
            f = s.firma(ln)
            f.extern = False
            f.body = s.blocco()
            return f
        if s.acc("struttura"):
            return s.struttura(ln)
        if s.is_("costante") or s.is_("variabile"):
            return s.vardecl(True)
        if s.acc("elenco"):
            return s.elenco(ln)
        s.e(f"atteso 'funzione', 'struttura', 'costante', 'variabile', 'elenco' o 'usa', trovato {s.desc()}")

    def elenco(s, ln):
        """elenco: naturale16 { A, B, C = 10, D }  ->  costanti numerate (non e' un tipo nuovo)."""
        ty = ("p", "i32")
        if s.acc(":"):
            ty = s.tipo()
        s.exp("{")
        out, prossimo = [], 0
        while not s.is_("}"):
            vl = s.tok[2]
            nome = s.ident()
            if s.acc("="):
                neg = s.acc("-")
                w = s.tok
                if w[0] != "num" or w[1][1]:
                    s.e("il valore di un elemento di 'elenco' deve essere un intero letterale")
                s.i += 1
                prossimo = -w[1][0] if neg else w[1][0]
            num = N("num", vl, val=abs(prossimo), isf=False)
            init = N("un", vl, op="-", e=num) if prossimo < 0 else num
            s.consts[nome] = prossimo
            out.append(N("var", vl, mut=False, name=nome, ty=ty, init=init, glob=True))
            prossimo += 1
            if not s.acc(","):
                break
        s.exp("}")
        if not out:
            raise ErroreCe("un 'elenco' vuoto", ln)
        return out

    def firma(s, ln):
        nome = s.ident()
        tps = []
        if s.acc("<"):
            while True:
                tps.append(s.ident())
                if not s.acc(","):
                    break
            s.chiudi_angolo()
        s.exp("(")
        params = []
        while not s.is_(")"):
            pl = s.tok[2]
            pn = s.ident()
            s.exp(":")
            params.append(N("param", pl, name=pn, ty=s.tipo()))
            if not s.acc(","):
                break
        s.exp(")")
        ret = ("p", "void")
        if s.acc("->"):
            ret = s.tipo()
        return N("fn", ln, name=nome, params=params, ret=ret, tparams=tps)

    def struttura(s, ln):
        nome = s.ident()
        tps = []
        if s.acc("<"):
            while True:
                tps.append(s.ident())
                if not s.acc(","):
                    break
            s.chiudi_angolo()
        packed = s.acc("impacchettata")
        s.exp("{")
        campi = []
        while not s.is_("}"):
            fl = s.tok[2]
            fn = s.ident()
            s.exp(":")
            ty = s.tipo()
            bits = None
            if s.acc(":"):
                w = s.tok
                if w[0] != "num" or w[1][1]:
                    s.e("dopo il secondo ':' ci vuole il numero di bit (un intero)")
                bits = w[1][0]
                s.i += 1
            campi.append(N("campo_def", fl, name=fn, ty=ty, bits=bits))
            if not s.acc(","):
                break
        s.exp("}")
        return N("struct", ln, name=nome, fields=campi, tparams=tps, packed=packed)

    def targs_ahead(s):
        """Siamo su '<': e' 'nome<tipi>(' (chiamata con tipi espliciti) e non un confronto?"""
        d, j = 0, s.i
        while j < len(s.t):
            k, v, _ = s.t[j]
            if k == "op" and v == "<":
                d += 1
            elif k == "op" and v == ">":
                d -= 1
            elif k == "op" and v == ">>":
                d -= 2
            elif k in ("id", "num") or (k == "op" and v in (",", "[", "]", ";", "*", "&")):
                pass
            else:
                return False
            j += 1
            if d <= 0:
                return d == 0 and s.t[j][0] == "op" and s.t[j][1] == "("
        return False

    def chiudi_angolo(s):
        """Chiude '<...>' anche quando il lessico ha letto '>>' (Vettore<Vettore<i32>>)."""
        if s.is_(">>"):
            t = s.tok
            s.t[s.i] = ("op", ">", t[2])
            return
        s.exp(">")

    def tipo(s):
        t = s.tok
        if s.acc("funzione"):
            s.exp("(")
            ps = []
            while not s.is_(")"):
                ps.append(s.tipo())
                if not s.acc(","):
                    break
            s.exp(")")
            ret = ("p", "void")
            if s.acc("->"):
                ret = s.tipo()
            return ("f", tuple(ps), ret)
        if s.acc("*"):
            return ("ptr", s.tipo())
        if s.acc("&"):
            return ("ref", s.tipo())
        if s.acc("["):
            el = s.tipo()
            if s.acc(";"):
                n = s.tok
                if n[0] == "num" and not n[1][1]:
                    val = n[1][0]
                elif n[0] == "id" and n[1] in s.consts:
                    val = s.consts[n[1]]
                else:
                    s.e("la lunghezza dell'array deve essere un numero o una costante")
                if val < 1:
                    s.e("la lunghezza dell'array deve essere almeno 1")
                s.i += 1
                s.exp("]")
                return ("a", el, val)
            s.exp("]")
            return ("s", el)
        if t[0] == "id":
            s.i += 1
            nome = t[1]
            if nome == "testo":
                return TESTO
            if nome in ALIAS_TIPI:
                return ("p", ALIAS_TIPI[nome])
            if s.acc("<"):
                args = []
                while True:
                    args.append(s.tipo())
                    if not s.acc(","):
                        break
                s.chiudi_angolo()
                return ("g", nome, tuple(args))
            return ("st", nome)
        s.e(f"atteso un tipo, trovato {s.desc()}")

    def vardecl(s, glob=False):
        t = s.tok
        ln, mut = t[2], t[1] == "variabile"
        s.i += 1
        nome = s.ident()
        ty = init = None
        if s.acc(":"):
            ty = s.tipo()
        if s.acc("="):
            init = s.expr()
        s.exp(";")
        if glob:
            if init is None and not mut:
                raise ErroreCe("una costante globale ha bisogno di un valore", ln)
            if init is None and ty is None:
                raise ErroreCe("una variabile globale senza valore ha bisogno del tipo", ln)
            v = None if init is None or mut else s.const_val(init)
            if v is not None:
                s.consts[nome] = v
        return N("var", ln, mut=mut, name=nome, ty=ty, init=init, glob=glob)

    # ----- istruzioni -----
    def blocco(s):
        s.exp("{")
        ns, s.nostruct, out = s.nostruct, 0, []
        while not s.is_("}"):
            if s.tok[0] == "eof":
                s.e("blocco non chiuso: manca '}'")
            try:
                out.append(s.stmt())
            except ErroreCe as e:
                s.errs.append(e)
                s.salta_istr()
        s.i += 1
        s.nostruct = ns
        return out

    def cond(s):
        s.nostruct += 1
        e = s.expr()
        s.nostruct -= 1
        return e

    def se(s):
        ln = s.tok[2]
        s.i += 1
        c = s.cond()
        b = s.blocco()
        els = None
        if s.acc("altrimenti"):
            els = [s.se()] if s.is_("se") else s.blocco()
        return N("if", ln, c=c, b=b, els=els)

    def scegli(s):
        """scegli x { caso 1, 2 { ... } caso 3 { ... } altrimenti { ... } }
        Diventa: { costante _scN = x; se _scN == 1 || _scN == 2 {...} altrimenti se ... }"""
        ln = s.tok[2]
        s.i += 1
        val = s.cond()
        s.exp("{")
        s.nsc = getattr(s, "nsc", 0) + 1
        nome = f"_sc{s.nsc}"
        casi, visti, altro = [], {}, None
        while not s.is_("}"):
            lc = s.tok[2]
            if s.acc("caso"):
                conds = []
                while True:
                    e = s.cond()
                    sem = e
                    if sem.k == "un" and sem.op == "-" and sem.e.k == "num":
                        chiave = ("num", -sem.e.val)
                    elif sem.k in ("num", "chr", "bool"):
                        chiave = (sem.k, sem.val)
                    elif sem.k == "id":
                        chiave = ("id", sem.name)
                    else:
                        raise ErroreCe("l'etichetta di 'caso' deve essere un numero, un carattere, "
                                       "vero/falso o una costante", e.line)
                    if chiave in visti:
                        raise ErroreCe(f"caso ripetuto (gia' scritto alla riga {visti[chiave]})", e.line)
                    visti[chiave] = e.line
                    conds.append(N("bin", e.line, op="==", l=N("id", e.line, name=nome), r=e))
                    if not s.acc(","):
                        break
                c = conds[0]
                for x in conds[1:]:
                    c = N("bin", x.line, op="||", l=c, r=x)
                casi.append((lc, c, s.blocco()))
            elif s.acc("altrimenti"):
                if altro is not None:
                    raise ErroreCe("'altrimenti' ripetuto in 'scegli'", lc)
                altro = s.blocco()
            else:
                s.e(f"in 'scegli' atteso 'caso' o 'altrimenti', trovato {s.desc()}")
        s.i += 1
        if not casi and altro is None:
            raise ErroreCe("'scegli' senza casi", ln)
        catena = altro
        for lc, c, b in reversed(casi):
            catena = [N("if", lc, c=c, b=b, els=catena)]
        decl = N("var", ln, mut=False, name=nome, ty=None, init=val, glob=False)
        return N("blk", ln, b=[decl] + (catena or []))

    def stmt(s):
        ln = s.tok[2]
        if s.is_("scegli"):
            return s.scegli()
        if s.is_("variabile") or s.is_("costante"):
            return s.vardecl()
        if s.is_("se"):
            return s.se()
        if s.acc("mentre"):
            c = s.cond()
            return N("while", ln, c=c, b=s.blocco())
        if s.acc("per"):
            v = s.ident()
            tv = s.tipo() if s.acc(":") else None
            s.exp("in")
            s.nostruct += 1
            a = s.expr()
            if s.acc(".."):
                b = s.expr()
                s.nostruct -= 1
                return N("range", ln, v=v, a=a, b=b, body=s.blocco(), ty=tv)
            s.nostruct -= 1
            if tv is not None:
                raise ErroreCe("il tipo dopo il nome si puo' scrivere solo nei cicli su un intervallo (a..b)", ln)
            return N("each", ln, v=v, e=a, body=s.blocco())
        if s.acc("ritorna"):
            e = None if s.is_(";") else s.expr()
            s.exp(";")
            return N("ret", ln, e=e)
        if s.acc("interrompi"):
            s.exp(";")
            return N("break", ln)
        if s.acc("continua"):
            s.exp(";")
            return N("continue", ln)
        if s.acc("rimanda"):
            return N("defer", ln, istr=s.stmt())
        if s.acc("rischio"):
            return N("risk", ln, b=s.blocco())
        if s.is_("{"):
            return N("blk", ln, b=s.blocco())
        e = s.expr()
        if s.tok[0] == "op" and s.tok[1] in ASSIGN_OPS:
            op = s.tok[1]
            s.i += 1
            v = s.expr()
            s.exp(";")
            return N("assign", ln, op=op, t=e, v=v)
        s.exp(";")
        return N("expr", ln, e=e)

    # ----- espressioni -----
    def expr(s, minp=1):
        l = s.cast()
        while True:
            t = s.tok
            op = t[1] if t[0] == "op" else None
            p = BINPREC.get(op)
            if p is None or p < minp:
                return l
            s.i += 1
            r = s.expr(p + 1)
            l = N("bin", t[2], op=op, l=l, r=r)

    def cast(s):
        u = s.unary()
        while s.is_("come"):
            ln = s.tok[2]
            s.i += 1
            u = N("cast", ln, e=u, ty=s.tipo())
        return u

    def unary(s):
        t = s.tok
        if t[0] == "op" and t[1] in ("-", "!", "~", "*", "&"):
            s.i += 1
            return N("un", t[2], op=t[1], e=s.unary())
        return s.postfix()

    def postfix(s):
        e = s.primary()
        while True:
            t = s.tok
            if e.k == "id" and s.is_("<") and s.targs_ahead():
                s.i += 1
                targs = []
                while True:
                    targs.append(s.tipo())
                    if not s.acc(","):
                        break
                s.chiudi_angolo()
                s.exp("(")
                args = s.seq(")", s.expr)
                e = N("call", t[2], name=e.name, args=args, targs=targs)
            elif s.is_("("):
                s.i += 1
                args = s.seq(")", s.expr)
                if e.k == "id":
                    e = N("call", t[2], name=e.name, args=args)
                else:
                    e = N("callx", t[2], fn=e, args=args)
            elif s.is_("["):
                s.i += 1
                ns, s.nostruct = s.nostruct, 0
                lo = None
                if not s.is_(".."):
                    lo = s.expr()
                if s.acc(".."):
                    hi = None
                    if not s.is_("]"):
                        hi = s.expr()
                    s.exp("]")
                    e = N("subs", t[2], e=e, lo=lo, hi=hi)
                else:
                    s.exp("]")
                    e = N("idx", t[2], e=e, i=lo)
                s.nostruct = ns
            elif s.is_("."):
                s.i += 1
                nome = s.ident()
                if s.is_("("):      # v.f(x)  e'  f(v, x)
                    s.i += 1
                    e = N("call", t[2], name=nome, args=[e] + s.seq(")", s.expr))
                else:
                    e = N("field", t[2], e=e, name=nome)
            else:
                return e

    def struct_ahead(s):
        if s.nostruct:
            return False
        a, b, c = s.peek(1), s.peek(2), s.peek(3)
        if not (a[0] == "op" and a[1] == "{"):
            return False
        return (b[0] == "op" and b[1] == "}") or \
               (b[0] == "id" and c[0] == "op" and c[1] == ":")

    def struct_lit(s):
        ln = s.tok[2]
        nome = s.ident()
        s.exp("{")
        ns, s.nostruct, campi = s.nostruct, 0, []
        while not s.is_("}"):
            fl = s.tok[2]
            fn = s.ident()
            s.exp(":")
            campi.append(N("campo", fl, name=fn, e=s.expr()))
            if not s.acc(","):
                break
        s.exp("}")
        s.nostruct = ns
        return N("slit", ln, name=nome, fields=campi)

    def array(s):
        ln = s.tok[2]
        s.i += 1
        ns, s.nostruct = s.nostruct, 0
        try:
            if s.acc("]"):
                return N("arr", ln, elems=[])
            first = s.expr()
            if s.acc(";"):
                n = s.expr()
                s.exp("]")
                return N("rep", ln, v=first, n=n)
            elems = [first]
            while s.acc(","):
                if s.is_("]"):
                    break
                elems.append(s.expr())
            s.exp("]")
            return N("arr", ln, elems=elems)
        finally:
            s.nostruct = ns

    def primary(s):
        k, v, ln = s.tok
        if k == "num":
            s.i += 1
            return N("num", ln, val=v[0], isf=v[1])
        if k == "str":
            s.i += 1
            return N("str", ln, val=v)
        if k == "chr":
            s.i += 1
            return N("chr", ln, val=v)
        if s.acc("vero"):
            return N("bool", ln, val=True)
        if s.acc("falso"):
            return N("bool", ln, val=False)
        if s.is_("("):
            s.i += 1
            ns, s.nostruct = s.nostruct, 0
            e = s.expr()
            s.nostruct = ns
            s.exp(")")
            return e
        if s.is_("["):
            return s.array()
        if k == "id":
            if s.struct_ahead():
                return s.struct_lit()
            s.i += 1
            return N("id", ln, name=v)
        s.e(f"atteso un'espressione, trovato {s.desc()}")


def analizza(toks):
    return Parser(toks).programma()

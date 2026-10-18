# -*- coding: utf-8 -*-
"""Ce++: dal flusso di token all'albero del programma."""
from lessico import ErroreCe

PRIMS = {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "usize",
         "f32", "f64", "bool", "void"}
ALIAS_TIPI = {"intero": "i32", "lungo": "i64", "corto": "i16", "byte": "u8",
              "carattere": "u8", "decimale": "f32", "doppio": "f64",
              "booleano": "bool", "vuoto": "void", "dimensione": "usize"}
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
    def programma(s):
        items = []
        while s.tok[0] != "eof":
            items.append(s.item())
        return items

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
        if s.is_("costante"):
            return s.vardecl(True)
        s.e(f"atteso 'funzione', 'struttura', 'costante' o 'usa', trovato {s.desc()}")

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

    def chiudi_angolo(s):
        """Chiude '<...>' anche quando il lessico ha letto '>>' (Vettore<Vettore<i32>>)."""
        if s.is_(">>"):
            t = s.tok
            s.t[s.i] = ("op", ">", t[2])
            return
        s.exp(">")

    def tipo(s):
        t = s.tok
        if s.acc("*"):
            return ("ptr", s.tipo())
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
            nome = ALIAS_TIPI.get(nome, nome)
            if nome in PRIMS:
                return ("p", nome)
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
            if init is None:
                raise ErroreCe("una costante globale ha bisogno di un valore", ln)
            v = s.const_val(init)
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
            out.append(s.stmt())
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

    def stmt(s):
        ln = s.tok[2]
        if s.is_("variabile") or s.is_("costante"):
            return s.vardecl()
        if s.is_("se"):
            return s.se()
        if s.acc("mentre"):
            c = s.cond()
            return N("while", ln, c=c, b=s.blocco())
        if s.acc("per"):
            v = s.ident()
            s.exp("in")
            s.nostruct += 1
            a = s.expr()
            if s.acc(".."):
                b = s.expr()
                s.nostruct -= 1
                return N("range", ln, v=v, a=a, b=b, body=s.blocco())
            s.nostruct -= 1
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
            if s.is_("("):
                if e.k != "id":
                    s.e("si possono chiamare solo funzioni per nome")
                s.i += 1
                args = s.seq(")", s.expr)
                e = N("call", t[2], name=e.name, args=args)
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
                e = N("field", t[2], e=e, name=s.ident())
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

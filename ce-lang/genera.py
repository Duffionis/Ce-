# -*- coding: utf-8 -*-
"""Ce++: controllo dei tipi e generazione del C."""
import copy
from lessico import ErroreCe
from sintassi import N, TESTO, PRIMS, ALIAS_TIPI

SIGNED = {"i8", "i16", "i32", "i64"}
UNSIGNED = {"u8", "u16", "u32", "u64", "usize"}
INTS = SIGNED | UNSIGNED
FLOATS = {"f32", "f64"}
BITS = {"i8": 8, "u8": 8, "i16": 16, "u16": 16, "i32": 32, "u32": 32,
        "i64": 64, "u64": 64, "usize": 64}
CT = {"i8": "int8_t", "i16": "int16_t", "i32": "int32_t", "i64": "int64_t",
      "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
      "usize": "size_t", "f32": "float", "f64": "double", "bool": "bool",
      "void": "void"}
UTYPE = {"i8": "uint8_t", "i16": "uint16_t", "i32": "uint32_t", "i64": "uint64_t",
         "u8": "uint8_t", "u16": "uint16_t", "u32": "uint32_t", "u64": "uint64_t",
         "usize": "size_t"}
LIM = {"i8": ("INT8_MIN", "INT8_MAX"), "i16": ("INT16_MIN", "INT16_MAX"),
       "i32": ("INT32_MIN", "INT32_MAX"), "i64": ("INT64_MIN", "INT64_MAX"),
       "u8": ("0", "UINT8_MAX"), "u16": ("0", "UINT16_MAX"),
       "u32": ("0", "UINT32_MAX"), "u64": ("0", "UINT64_MAX"),
       "usize": ("0", "SIZE_MAX")}
RANGE = {k: ((-(1 << (BITS[k] - 1)), (1 << (BITS[k] - 1)) - 1) if k in SIGNED
             else (0, (1 << BITS[k]) - 1)) for k in INTS}

VOID, BOOL = ("p", "void"), ("p", "bool")
I32, F64, USIZE = ("p", "i32"), ("p", "f64"), ("p", "usize")
BUILTIN = ("stampa", "scrivi", "panico", "afferma", "riserva", "libera", "misura")


def is_int(t):
    return bool(t) and t[0] == "p" and t[1] in INTS


def tstr(t):
    if t == TESTO:
        return "testo"
    k = t[0]
    if k in ("p", "st"):
        return t[1]
    if k == "ptr":
        return "*" + tstr(t[1])
    if k == "s":
        return "[" + tstr(t[1]) + "]"
    return f"[{tstr(t[1])}; {t[2]}]"


def es_tipo(x):
    k = x[0] if x else None
    if k == "g":
        return (len(x) == 3 and isinstance(x[1], str) and isinstance(x[2], tuple)
                and all(isinstance(a, tuple) and es_tipo(a) for a in x[2]))
    if k in ("p", "st"):
        return len(x) == 2 and isinstance(x[1], str)
    if k in ("s", "ptr"):
        return len(x) == 2 and isinstance(x[1], tuple) and es_tipo(x[1])
    if k == "a":
        return len(x) == 3 and isinstance(x[1], tuple) and es_tipo(x[1]) and isinstance(x[2], int)
    return False


def sost(t, b):
    """Sostituisce i parametri di tipo (nomi in b) dentro il tipo t."""
    k = t[0]
    if k == "st":
        return b.get(t[1], t)
    if k == "p":
        return t
    if k == "g":
        return ("g", t[1], tuple(sost(a, b) for a in t[2]))
    if k in ("s", "ptr"):
        return (k, sost(t[1], b))
    return ("a", sost(t[1], b), t[2])


def ha_param(t, tps):
    k = t[0]
    if k == "st":
        return t[1] in tps
    if k == "p":
        return False
    if k == "g":
        return any(ha_param(a, tps) for a in t[2])
    return ha_param(t[1], tps)


def nome_di(t):
    if t == TESTO:
        return "testo"
    return t[1] if t[0] in ("p", "st") else None


def riscrivi(x, b):
    """Copia di un albero con i parametri di tipo sostituiti dai tipi veri."""
    if isinstance(x, N):
        y = copy.copy(x)
        for k, v in x.__dict__.items():
            if k not in ("k", "line", "file"):
                setattr(y, k, riscrivi(v, b))
        if x.k == "id" and x.name in b and nome_di(b[x.name]):
            y.name = nome_di(b[x.name])
        return y
    if isinstance(x, list):
        return [riscrivi(v, b) for v in x]
    if isinstance(x, tuple):
        if x and isinstance(x[0], str) and es_tipo(x):
            return sost(x, b)
        return tuple(riscrivi(v, b) for v in x)
    return x


class E:
    """Espressione generata: codice C, tipo Ce, e se e' assegnabile."""
    __slots__ = ("c", "t", "lv")

    def __init__(s, c, t, lv=False):
        s.c, s.t, s.lv = c, t, lv


class Var:
    # depth: livello di blocco in cui e' dichiarata la variabile.
    # org: per i tipi che contengono fette, il livello di blocco piu' interno
    #      dei dati a cui puo' puntare (0 = dati del chiamante o stringhe letterali).
    __slots__ = ("c", "t", "mut", "depth", "org")

    def __init__(s, c, t, mut, depth, org=0):
        s.c, s.t, s.mut, s.depth, s.org = c, t, mut, depth, org


# ---------- analisi dei percorsi di ritorno ----------
def has_break(stmts):
    for x in stmts:
        if x.k == "break":
            return True
        if x.k in ("blk", "risk") and has_break(x.b):
            return True
        if x.k == "if" and (has_break(x.b) or (x.els and has_break(x.els))):
            return True
    return False


def term(x):
    k = x.k
    if k == "ret":
        return True
    if k == "expr" and x.e.k == "call" and x.e.name == "panico":
        return True
    if k in ("blk", "risk"):
        return ends(x.b)
    if k == "if":
        return x.els is not None and ends(x.b) and ends(x.els)
    if k == "while":
        return x.c.k == "bool" and x.c.val and not has_break(x.b)
    return False


def ends(stmts):
    return any(term(x) for x in stmts)


RUNTIME = r'''/* generato da Ce++ */
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#define CE_NORET __attribute__((noreturn))
#define CE_UNUSED __attribute__((unused))
static CE_NORET CE_UNUSED void ce_panic_idx_(size_t i, size_t n, long line, const char* CE_FILE) {
    fflush(stdout);
    fprintf(stderr, "panico: indice %zu fuori dai limiti (lunghezza %zu) [%s:%ld]\n", i, n, CE_FILE, line);
    exit(101);
}
static CE_NORET CE_UNUSED void ce_panic_sub_(size_t lo, size_t hi, size_t n, long line, const char* CE_FILE) {
    fflush(stdout);
    fprintf(stderr, "panico: fetta %zu..%zu non valida (lunghezza %zu) [%s:%ld]\n", lo, hi, n, CE_FILE, line);
    exit(101);
}
static CE_NORET CE_UNUSED void ce_panic_div_(long line, const char* CE_FILE) {
    fflush(stdout);
    fprintf(stderr, "panico: divisione per zero [%s:%ld]\n", CE_FILE, line);
    exit(101);
}
static CE_NORET CE_UNUSED void ce_panic_shift_(long line, const char* CE_FILE) {
    fflush(stdout);
    fprintf(stderr, "panico: scorrimento oltre la larghezza del tipo [%s:%ld]\n", CE_FILE, line);
    exit(101);
}
static CE_NORET CE_UNUSED void ce_panic_lit_(const char* m, long line, const char* CE_FILE) {
    fflush(stdout);
    fprintf(stderr, "panico: %s [%s:%ld]\n", m, CE_FILE, line);
    exit(101);
}
static CE_NORET CE_UNUSED void ce_panic_msg_(const uint8_t* p, size_t n, long line, const char* CE_FILE) {
    fflush(stdout);
    fprintf(stderr, "panico: %.*s [%s:%ld]\n", (int)n, (const char*)p, CE_FILE, line);
    exit(101);
}
#define ce_panic_idx(...) ce_panic_idx_(__VA_ARGS__, __FILE__)
#define ce_panic_sub(...) ce_panic_sub_(__VA_ARGS__, __FILE__)
#define ce_panic_div(...) ce_panic_div_(__VA_ARGS__, __FILE__)
#define ce_panic_shift(...) ce_panic_shift_(__VA_ARGS__, __FILE__)
#define ce_panic_lit(...) ce_panic_lit_(__VA_ARGS__, __FILE__)
#define ce_panic_msg(...) ce_panic_msg_(__VA_ARGS__, __FILE__)
'''

PRINTERS = r'''
static CE_UNUSED void* ce_riserva(size_t n, size_t size, long line) {
    if (n == 0) return NULL;
    void* p = calloc(n, size);
    if (!p) ce_panic_lit("memoria esaurita", line);
    return p;
}
static CE_UNUSED void ce_pi(int64_t x) { printf("%lld", (long long)x); }
static CE_UNUSED void ce_pu(uint64_t x) { printf("%llu", (unsigned long long)x); }
static CE_UNUSED void ce_pf(double x) { printf("%g", x); }
static CE_UNUSED void ce_pb(bool b) { fputs(b ? "vero" : "falso", stdout); }
static CE_UNUSED void ce_ps(ce_s_u8 s) { fwrite(s.ptr, 1, s.len, stdout); }
static CE_UNUSED void ce_nl(void) { putchar('\n'); }
'''


class _Nessuno:
    file = None


N0 = _Nessuno()


class Gen:
    def __init__(s, fname):
        s.fname = fname
        s.main = fname
        s.generics = {}   # nome -> funzione generica (nodo)
        s.bits = {}       # (struttura, campo) -> larghezza in bit (campi a bit)
        s.gstructs = {}   # nome -> struttura generica (nodo)
        s.ginst = {}      # istanza concreta -> (nome generico, argomenti)
        s.pending = []    # istanze generiche da generare
        s.ninst = 0
        s.dframes = []   # un blocco per ogni '{': codice C dei 'rimanda' in attesa
        s.cur = None   # file del nodo in lavorazione (None = file principale)
        s.cfile = s.cesc(fname)
        s.structs, s.defined, s.funcs, s.cvals = {}, set(), {}, {}
        s.tdecl, s.tdone = [], set()
        s.scopes = [{}]
        s.n = 0
        s.risk = s.loops = 0
        s.ret = VOID
        s.L, s.glob_lines, s.proto, s.corpi = [], [], [], []
        s.ctype(TESTO)

    # ----- utilita' -----
    @staticmethod
    def cesc(p):
        return p.replace("\\", "\\\\").replace('"', '\\"')

    def entra(s, it):
        """Da qui in poi gli errori e le righe #line riguardano il file di 'it'."""
        s.cur = getattr(it, "file", None)
        s.cfile = s.cesc(s.cur or s.main)

    def err(s, msg, line):
        raise ErroreCe(msg, line, s.cur)

    def uid(s):
        s.n += 1
        return s.n

    def put(s, ind, t):
        s.L.append("  " * ind + t)

    def cid(s, name):
        return "".join(ch if (ch.isascii() and (ch.isalnum() or ch == "_"))
                       else f"_u{ord(ch):x}_" for ch in name)

    def mangle(s, t):
        k = t[0]
        if k == "p":
            return t[1]
        if k == "st":
            return s.cid(t[1])
        if k == "ptr":
            return "P" + s.mangle(t[1])
        if k == "s":
            return "S" + s.mangle(t[1])
        return f"A{t[2]}_" + s.mangle(t[1])

    def ctype(s, t):
        k = t[0]
        if k == "p":
            return CT[t[1]]
        if k == "st":
            return "S_" + s.cid(t[1])
        if k == "ptr":
            return s.ctype(t[1]) + "*"
        if k == "s":
            name = "ce_s_" + s.mangle(t[1])
            if name not in s.tdone:
                s.tdone.add(name)
                et = s.ctype(t[1])
                s.tdecl.append(f"typedef struct {{ {et}* ptr; size_t len; }} {name};")
            return name
        name = f"ce_a{t[2]}_" + s.mangle(t[1])
        if name not in s.tdone:
            s.tdone.add(name)
            et = s.ctype(t[1])
            s.tdecl.append(f"typedef struct {{ {et} d[{t[2]}]; }} {name};")
        return name

    def check_type(s, t, line, val):
        k = t[0]
        if k == "p":
            if val and t == VOID:
                s.err("'vuoto' non e' un tipo di valore", line)
        elif k == "st":
            if t[1] not in s.structs:
                s.err(f"tipo sconosciuto '{t[1]}'", line)
            if val and t[1] not in s.defined:
                s.err(f"la struttura '{t[1]}' va definita prima di usarla per valore", line)
        elif k == "ptr":
            s.check_type(t[1], line, False)
        elif k == "s":
            if t[1] == VOID:
                s.err("non esiste una fetta di 'vuoto'", line)
            s.check_type(t[1], line, False)
        elif k == "a":
            s.check_type(t[1], line, True)

    def lookup(s, name, line):
        for sc in reversed(s.scopes):
            if name in sc:
                return sc[name]
        s.err(f"nome sconosciuto '{name}'", line)

    def declare(s, name, t, mut, line, org=0):
        for sc in s.scopes:
            if name in sc:
                s.err(f"'{name}' esiste gia': in Ce++ i nomi non si possono nascondere", line)
        c = "v_" + s.cid(name)
        s.scopes[-1][name] = Var(c, t, mut, len(s.scopes), org)
        return c

    def const_int(s, n):
        if n.k == "num" and not n.isf:
            return n.val
        if n.k == "un" and n.op == "-" and n.e.k == "num" and not n.e.isf:
            return -n.e.val
        if n.k == "id":
            return s.cvals.get(n.name)
        return None

    def is_lit(s, n):
        if n.k == "num":
            return True
        if n.k == "un" and n.op == "-":
            return s.is_lit(n.e)
        if n.k == "bin":
            return s.is_lit(n.l) and s.is_lit(n.r)
        return False

    def pure(s, n):
        if n.k in ("num", "id", "bool", "chr"):
            return True
        if n.k in ("field", "un", "cast"):
            return s.pure(n.e)
        if n.k == "idx":
            return s.pure(n.e) and s.pure(n.i)
        if n.k == "bin":
            return s.pure(n.l) and s.pure(n.r)
        return False

    def nome_tipo(s, n):
        """Il tipo scritto come argomento di 'riserva' (solo nomi: i32, intero, Punto, testo)."""
        if n.k == "id":
            nm = n.name
            if nm == "testo":
                return TESTO
            if nm in ALIAS_TIPI:
                nm = ALIAS_TIPI[nm]
            if nm in PRIMS and nm not in ("void", "bool"):
                return ("p", nm)
            if nm == "bool":
                return ("p", "bool")
            if nm in s.structs:
                return ("st", nm)
        s.err("il primo argomento di 'riserva' deve essere il nome di un tipo (i32, intero, Punto...)", n.line)

    # ----- durata dei dati a cui puntano le fette -----
    # Ogni blocco ha un livello (len(s.scopes)); i dati di una variabile vivono
    # fino alla fine del suo blocco. Una fetta e' valida solo se i dati a cui
    # punta vivono almeno quanto chi la tiene. Livello 0 = parametri e stringhe.
    def holds(s, t, seen=()):
        if t[0] == "s":
            return True
        if t[0] == "a":
            return s.holds(t[1], seen)
        if t[0] == "st" and t[1] not in seen:
            return any(s.holds(ft, seen + (t[1],)) for _, ft in s.structs[t[1]])
        return False

    def borrow(s, n):
        """Livello dei dati a cui puntera' 'n' se diventa (o e') una fetta."""
        if n.T[0] == "a":
            d = s.rootdepth(n)
            return max(d, s.org(n)) if s.holds(n.T) else d
        return s.org(n) if s.holds(n.T) else 0

    def rootdepth(s, n):
        k = n.k
        if k == "id":
            return s.lookup(n.name, n.line).depth
        if k in ("field", "idx"):
            if n.e.T[0] == "s":
                return s.org(n.e)
            return s.rootdepth(n.e)
        if k == "un":
            return 0          # attraverso un puntatore grezzo: territorio 'rischio'
        return len(s.scopes)  # temporaneo di questo blocco

    def org(s, n):
        k = n.k
        if k == "str":
            return 0
        if k == "id":
            return s.lookup(n.name, n.line).org
        if k in ("field", "idx"):
            return s.org(n.e) if s.holds(n.e.T) else 0
        if k == "subs":
            return s.borrow(n.e)
        if k == "call":
            if n.name == "riserva":
                return 0          # memoria dell'heap: vive finche' non la liberi
            return max([s.borrow(a) for a in n.args if a.T[0] in ("a", "s", "st")
                        and (a.T[0] == "a" or s.holds(a.T))] or [0])
        if k == "slit":
            return max([s.borrow(f.e) for f in n.fields if f.e.T[0] in ("a", "s", "st")
                        and (f.e.T[0] == "a" or s.holds(f.e.T))] or [0])
        if k in ("arr", "rep"):
            el = n.elems if k == "arr" else [n.v]
            return max([s.borrow(x) for x in el if x.T[0] in ("a", "s", "st")
                        and (x.T[0] == "a" or s.holds(x.T))] or [0])
        return 0

    def holder(s, n):
        """(livello dei dati dove vive il bersaglio, variabile radice) di un'assegnazione."""
        k = n.k
        if k == "id":
            v = s.lookup(n.name, n.line)
            return v.depth, v
        if k == "field":
            return s.holder(n.e)
        if k == "idx":
            if n.e.T[0] == "s":
                return s.org(n.e), None
            return s.holder(n.e)
        return None, None

    # ----- espressioni -----
    def ex(s, n, hint=None):
        e = getattr(s, "x_" + n.k)(n, hint)
        n.T = e.t
        return e

    def coerce(s, node, want, tmp_ok):
        e = s.ex(node, want)
        if e.t == want:
            return e.c
        if want[0] == "s" and e.t[0] == "a" and e.t[1] == want[1]:
            return s.as_slice(e, node, tmp_ok)[0]
        s.err(f"tipo diverso: atteso {tstr(want)}, trovato {tstr(e.t)}", node.line)

    def as_slice(s, e, node, tmp_ok):
        t = e.t
        if t[0] == "s":
            return e.c, t
        if t[0] == "a":
            if not (e.lv or (tmp_ok and node.k in ("arr", "rep"))):
                s.err("per usare un array come fetta serve una variabile", node.line)
            st = ("s", t[1])
            return f"(({s.ctype(st)}){{ ({e.c}).d, {t[2]} }})", st
        s.err(f"serve un array o una fetta, non {tstr(t)}", node.line)

    def x_num(s, n, hint):
        v = n.val
        if hint and hint[0] == "p" and hint[1] in FLOATS:
            return E(repr(float(v)) + ("f" if hint[1] == "f32" else ""), hint)
        if n.isf:
            return E(repr(float(v)), F64)
        t = hint if is_int(hint) else I32
        lo, hi = RANGE[t[1]]
        if not lo <= v <= hi:
            s.err(f"il numero {v} non sta in {t[1]} (da {lo} a {hi})", n.line)
        if t[1] == "i64" and v == lo:
            return E("INT64_MIN", t)
        suf = "ULL" if t[1] in ("u64", "usize") else "LL" if t[1] == "i64" else ""
        return E(f"(({CT[t[1]]}){v}{suf})", t)

    def x_str(s, n, hint):
        b = n.val
        lit = "".join(chr(c) if 32 <= c < 127 and chr(c) not in '"\\?'
                      else f"\\{c:03o}" for c in b)
        return E(f'(({s.ctype(TESTO)}){{(uint8_t*)"{lit}", {len(b)}}})', TESTO)

    def x_chr(s, n, hint):
        return E(f"((uint8_t){n.val})", ("p", "u8"))

    def x_bool(s, n, hint):
        return E("true" if n.val else "false", BOOL)

    def x_id(s, n, hint):
        v = s.lookup(n.name, n.line)
        return E(v.c, v.t, True)

    def x_field(s, n, hint):
        o = s.ex(n.e)
        t = o.t
        if t[0] in ("a", "s") and n.name == "lunghezza":
            if t[0] == "s":
                return E(f"({o.c}).len", USIZE)
            return E(f"((void)({o.c}), (size_t){t[2]})", USIZE)
        if t[0] == "st":
            for fn, ft in s.structs[t[1]]:
                if fn == n.name:
                    return E(f"({o.c}).m_{s.cid(fn)}", ft, o.lv)
            s.err(f"la struttura '{t[1]}' non ha il campo '{n.name}'", n.line)
        s.err(f"il tipo {tstr(t)} non ha campi", n.line)

    def x_idx(s, n, hint):
        o = s.ex(n.e)
        t = o.t
        if t[0] not in ("a", "s"):
            s.err(f"si puo' indicizzare solo un array o una fetta, non {tstr(t)}", n.line)
        i = s.ex(n.i, USIZE)
        if not is_int(i.t):
            s.err("l'indice deve essere un intero", n.line)
        u = s.uid()
        if t[0] == "a":
            c = (f"(*({{ size_t _i{u} = (size_t)({i.c}); "
                 f"if (_i{u} >= {t[2]}) ce_panic_idx(_i{u}, {t[2]}, {n.line}); "
                 f"&({o.c}).d[_i{u}]; }}))")
        else:
            sc = s.ctype(t)
            c = (f"(*({{ {sc} _s{u} = {o.c}; size_t _i{u} = (size_t)({i.c}); "
                 f"if (_i{u} >= _s{u}.len) ce_panic_idx(_i{u}, _s{u}.len, {n.line}); "
                 f"&_s{u}.ptr[_i{u}]; }}))")
        return E(c, t[1], True)

    def x_subs(s, n, hint):
        o = s.ex(n.e)
        code, st = s.as_slice(o, n.e, False)
        u = s.uid()
        lo = hi = None
        if n.lo is not None:
            lo = s.ex(n.lo, USIZE)
            if not is_int(lo.t):
                s.err("gli estremi della fetta devono essere interi", n.line)
        if n.hi is not None:
            hi = s.ex(n.hi, USIZE)
            if not is_int(hi.t):
                s.err("gli estremi della fetta devono essere interi", n.line)
        los = lo.c if lo else "0"
        his = hi.c if hi else f"_s{u}.len"
        sc = s.ctype(st)
        c = (f"({{ {sc} _s{u} = {code}; size_t _lo{u} = (size_t)({los}); "
             f"size_t _hi{u} = (size_t)({his}); "
             f"if (_lo{u} > _hi{u} || _hi{u} > _s{u}.len) ce_panic_sub(_lo{u}, _hi{u}, _s{u}.len, {n.line}); "
             f"({sc}){{ _s{u}.ptr + _lo{u}, _hi{u} - _lo{u} }}; }})")
        return E(c, st)

    def x_arr(s, n, hint):
        eh = hint[1] if hint and hint[0] in ("a", "s") else None
        if not n.elems:
            s.err("un array deve avere almeno un elemento", n.line)
        first = s.ex(n.elems[0], eh)
        t = first.t
        codes = [first.c] + [s.coerce(x, t, False) for x in n.elems[1:]]
        at = ("a", t, len(n.elems))
        return E(f"(({s.ctype(at)}){{{{ {', '.join(codes)} }}}})", at)

    def x_rep(s, n, hint):
        eh = hint[1] if hint and hint[0] in ("a", "s") else None
        v = s.ex(n.v, eh)
        cnt = s.const_int(n.n)
        if cnt is None or cnt < 1:
            s.err("la lunghezza deve essere un numero o una costante positiva", n.line)
        at = ("a", v.t, cnt)
        u = s.uid()
        c = (f"({{ {s.ctype(at)} _a{u}; {s.ctype(v.t)} _v{u} = {v.c}; "
             f"for (size_t _k{u} = 0; _k{u} < {cnt}; _k{u}++) _a{u}.d[_k{u}] = _v{u}; _a{u}; }})")
        return E(c, at)

    def x_slit(s, n, hint):
        if n.name in s.gstructs:
            n.name = s.slit_istanza(n, hint)
        if n.name not in s.structs:
            s.err(f"struttura sconosciuta '{n.name}'", n.line)
        defs = dict(s.structs[n.name])
        seen, parts = set(), []
        for f in n.fields:
            if f.name not in defs:
                s.err(f"la struttura '{n.name}' non ha il campo '{f.name}'", f.line)
            if f.name in seen:
                s.err(f"il campo '{f.name}' e' ripetuto", f.line)
            seen.add(f.name)
            s.check_bits(n.name, f.name, f.e)
            parts.append(f".m_{s.cid(f.name)} = {s.coerce(f.e, defs[f.name], False)}")
        t = ("st", n.name)
        body = ", ".join(parts) if parts else "0"
        return E(f"(({s.ctype(t)}){{ {body} }})", t)

    def x_un(s, n, hint):
        op = n.op
        if op == "-" and n.e.k == "num" and not n.e.isf:
            return s.x_num(N("num", n.line, val=-n.e.val, isf=False), hint)
        if op == "&":
            if not s.risk:
                s.err("'&' si puo' usare solo dentro un blocco 'rischio'", n.line)
            o = s.ex(n.e)
            if not o.lv:
                s.err("'&' vuole una variabile, un campo o un elemento", n.line)
            if n.e.k == "field" and n.e.e.T[0] == "st" and (n.e.e.T[1], n.e.name) in s.bits:
                s.err("un campo a bit non ha un indirizzo: non si puo' usare '&'", n.line)
            return E(f"(&({o.c}))", ("ptr", o.t))
        if op == "*":
            if not s.risk:
                s.err("'*' (dereferenziare) si puo' usare solo dentro un blocco 'rischio'", n.line)
            o = s.ex(n.e)
            if o.t[0] != "ptr" or o.t[1] == VOID:
                s.err("'*' vuole un puntatore", n.line)
            return E(f"(*({o.c}))", o.t[1], True)
        o = s.ex(n.e, hint)
        t = o.t
        if op == "-":
            if t[0] == "p" and t[1] in FLOATS:
                return E(f"(-({o.c}))", t)
            if t[0] == "p" and t[1] in SIGNED:
                return E(f"(({CT[t[1]]})(-({o.c})))", t)
            s.err(f"'-' non vale per il tipo {tstr(t)}", n.line)
        if op == "!":
            if t != BOOL:
                s.err("'!' vuole un booleano", n.line)
            return E(f"(!({o.c}))", BOOL)
        if not is_int(t):
            s.err("'~' vuole un intero", n.line)
        return E(f"(({CT[t[1]]})(~({o.c})))", t)

    def x_cast(s, n, hint):
        s.check_type(n.ty, n.line, False)
        o = s.ex(n.e)
        f, t = o.t, n.ty
        if f == t:
            return E(o.c, t)
        if f[0] == "p" and t[0] == "p":
            fn_, tn = f[1], t[1]
            if fn_ == "void" or tn == "void":
                s.err("conversione non ammessa", n.line)
            if tn == "bool":
                s.err("per ottenere un booleano usa un confronto, ad esempio x != 0", n.line)
            if fn_ in FLOATS and tn in INTS:
                lo, hi = LIM[tn]
                u = s.uid()
                c = (f"({{ double _f{u} = (double)({o.c}); "
                     f"_f{u} != _f{u} ? ({CT[tn]})0 : "
                     f"_f{u} >= (double){hi} ? ({CT[tn]}){hi} : "
                     f"_f{u} <= (double){lo} ? ({CT[tn]}){lo} : ({CT[tn]})_f{u}; }})")
                return E(c, t)
            return E(f"(({CT[tn]})({o.c}))", t)
        if s.risk:
            if f[0] == "ptr" and (t[0] == "ptr" or t in (USIZE, ("p", "u64"))):
                return E(f"(({s.ctype(t)})({o.c}))", t)
            if t[0] == "ptr" and f in (USIZE, ("p", "u64")):
                return E(f"(({s.ctype(t)})({o.c}))", t)
            if f[0] == "s" and t[0] == "ptr":
                return E(f"(({s.ctype(t)})(({o.c}).ptr))", t)
        extra = "" if s.risk else " (le conversioni di puntatori vogliono 'rischio')"
        s.err(f"conversione non ammessa da {tstr(f)} a {tstr(t)}{extra}", n.line)

    def x_bin(s, n, hint):
        op = n.op
        if op in ("&&", "||"):
            a, b = s.ex(n.l), s.ex(n.r)
            if a.t != BOOL or b.t != BOOL:
                s.err(f"'{op}' vuole due valori booleani", n.line)
            return E(f"({a.c} {op} {b.c})", BOOL)
        cmp_ = op in ("==", "!=", "<", ">", "<=", ">=")
        h = None if cmp_ else hint
        if op in ("<<", ">>"):
            a = s.ex(n.l, h)
            b = s.ex(n.r)
            if not (is_int(a.t) and is_int(b.t)):
                s.err(f"'{op}' vuole due interi", n.line)
            T = a.t[1]
            cT, u = CT[T], s.uid()
            if op == "<<":
                val = f"({cT})(({UTYPE[T]})_a{u} << _c{u})"
            else:
                val = f"({cT})(_a{u} >> _c{u})"
            c = (f"({{ {cT} _a{u} = {a.c}; uint64_t _c{u} = (uint64_t)({b.c}); "
                 f"if (_c{u} >= {BITS[T]}) ce_panic_shift({n.line}); {val}; }})")
            return E(c, a.t)
        if s.is_lit(n.l) and not s.is_lit(n.r):
            b = s.ex(n.r, h)
            a = s.ex(n.l, b.t)
        else:
            a = s.ex(n.l, h)
            b = s.ex(n.r, a.t)
        if a.t != b.t:
            s.err(f"tipi diversi: {tstr(a.t)} e {tstr(b.t)} (usa 'come' per convertire)", n.line)
        t = a.t
        num = t[0] == "p" and (t[1] in INTS or t[1] in FLOATS)
        ints = is_int(t)
        if cmp_:
            ok = num or (op in ("==", "!=") and (t == BOOL or t[0] == "ptr"))
            if not ok:
                s.err(f"non posso confrontare valori di tipo {tstr(t)} con '{op}'", n.line)
            return E(f"({a.c} {op} {b.c})", BOOL)
        if op in ("+", "-", "*"):
            if not num:
                s.err(f"'{op}' non vale per il tipo {tstr(t)}", n.line)
            if ints:
                return E(f"(({CT[t[1]]})({a.c} {op} {b.c}))", t)
            return E(f"({a.c} {op} {b.c})", t)
        if op in ("/", "%"):
            if not num or (op == "%" and not ints):
                s.err(f"'{op}' non vale per il tipo {tstr(t)}", n.line)
            if not ints:
                return E(f"({a.c} / {b.c})", t)
            T, u = CT[t[1]], s.uid()
            if t[1] in SIGNED:
                ut = UTYPE[t[1]]
                if op == "/":
                    r = f"(_b{u} == -1 ? ({T})(0 - ({ut})_a{u}) : _a{u} / _b{u})"
                else:
                    r = f"(_b{u} == -1 ? ({T})0 : _a{u} % _b{u})"
            else:
                r = f"(_a{u} {op} _b{u})"
            c = (f"({{ {T} _a{u} = {a.c}; {T} _b{u} = {b.c}; "
                 f"if (_b{u} == 0) ce_panic_div({n.line}); ({T})({r}); }})")
            return E(c, t)
        if op in ("&", "|", "^"):
            if not ints:
                s.err(f"'{op}' vuole interi", n.line)
            return E(f"(({CT[t[1]]})({a.c} {op} {b.c}))", t)
        s.err(f"operatore sconosciuto '{op}'", n.line)

    def c_print(s, n, nl):
        parts = []
        for a in n.args:
            e = s.ex(a)
            t = e.t
            if t == TESTO:
                parts.append(f"ce_ps({e.c})")
            elif t == BOOL:
                parts.append(f"ce_pb({e.c})")
            elif t[0] == "p" and t[1] in SIGNED:
                parts.append(f"ce_pi((int64_t)({e.c}))")
            elif t[0] == "p" and t[1] in UNSIGNED:
                parts.append(f"ce_pu((uint64_t)({e.c}))")
            elif t[0] == "p" and t[1] in FLOATS:
                parts.append(f"ce_pf((double)({e.c}))")
            else:
                s.err(f"non so stampare un valore di tipo {tstr(t)}", a.line)
        if nl:
            parts.append("ce_nl()")
        parts.append("(void)0")
        return E("(" + ", ".join(parts) + ")", VOID)

    def x_call(s, n, hint):
        nm = n.name
        if nm in ("stampa", "scrivi"):
            return s.c_print(n, nm == "stampa")
        if nm == "panico":
            if len(n.args) != 1:
                s.err("'panico' vuole un messaggio (testo)", n.line)
            m = s.coerce(n.args[0], TESTO, False)
            u = s.uid()
            return E(f"({{ ce_s_u8 _m{u} = {m}; ce_panic_msg(_m{u}.ptr, _m{u}.len, {n.line}); }})", VOID)
        if nm == "afferma":
            if len(n.args) not in (1, 2):
                s.err("'afferma' vuole una condizione e, se vuoi, un messaggio", n.line)
            c = s.ex(n.args[0])
            if c.t != BOOL:
                s.err("la condizione di 'afferma' deve essere un booleano", n.line)
            if len(n.args) == 1:
                return E(f'(!({c.c}) ? ce_panic_lit("asserzione fallita", {n.line}) : (void)0)', VOID)
            m = s.coerce(n.args[1], TESTO, False)
            u = s.uid()
            return E(f"({{ ce_s_u8 _m{u} = {m}; if (!({c.c})) ce_panic_msg(_m{u}.ptr, _m{u}.len, {n.line}); }})", VOID)
        if nm == "riserva":
            if len(n.args) != 2:
                s.err("'riserva' vuole un tipo e una quantita': riserva(i32, 10)", n.line)
            t = s.nome_tipo(n.args[0])
            st = ("s", t)
            cnt = s.coerce(n.args[1], USIZE, False)
            u = s.uid()
            return E(f"({{ size_t _n{u} = (size_t)({cnt}); "
                     f"({s.ctype(st)}){{ ({s.ctype(t)}*)ce_riserva(_n{u}, sizeof({s.ctype(t)}), {n.line}), _n{u} }}; }})", st)
        if nm == "misura":
            if len(n.args) != 1:
                s.err("'misura' vuole un tipo: misura(Registro)", n.line)
            t = s.nome_tipo(n.args[0])
            return E(f"((size_t)sizeof({s.ctype(t)}))", USIZE)
        if nm == "libera":
            if not s.risk:
                s.err("'libera' e' pericolosa (la fetta deve venire da 'riserva'): usala dentro un blocco 'rischio'", n.line)
            if len(n.args) != 1:
                s.err("'libera' vuole una fetta: libera(v)", n.line)
            a = s.ex(n.args[0])
            if a.t[0] != "s" or n.args[0].k != "id":
                s.err("'libera' vuole il nome di una variabile di tipo fetta", n.line)
            s.check_mut(n.args[0])
            return E(f"({{ free((void*)({a.c}).ptr); {a.c} = ({s.ctype(a.t)}){{0}}; }})", VOID)
        if nm in s.generics:
            nm = n.name = s.istanzia(n)
        if nm not in s.funcs:
            s.err(f"funzione sconosciuta '{nm}'", n.line)
        params, ret, ext = s.funcs[nm]
        if ext and not s.risk:
            s.err(f"'{nm}' e' una funzione C: chiamala dentro un blocco 'rischio'", n.line)
        if len(n.args) != len(params):
            s.err(f"'{nm}' vuole {len(params)} argomenti, ne ha ricevuti {len(n.args)}", n.line)
        args = [s.coerce(a, pt, True) for a, (pn, pt) in zip(n.args, params)]
        cn = ("x_" if ext else "f_") + s.cid(nm)
        return E(f"{cn}({', '.join(args)})", ret)

    # ----- istruzioni -----
    def st(s, n, ind):
        s.L.append(f'#line {n.line} "{s.cfile}"')
        getattr(s, "st_" + n.k)(n, ind)

    def cond_code(s, node):
        c = s.ex(node)
        if c.t != BOOL:
            s.err(f"la condizione deve essere un booleano, non {tstr(c.t)}", node.line)
        return c.c

    def body(s, stmts, ind, loop=False):
        s.scopes.append({})
        s.stmts(stmts, ind, loop)
        s.scopes.pop()

    def stmts(s, stmts, ind, loop=False):
        """Un blocco: esegue le istruzioni e, a fine blocco, i 'rimanda' (in ordine inverso)."""
        s.dframes.append({"code": [], "loop": loop})
        for x in stmts:
            s.st(x, ind)
        fr = s.dframes.pop()
        if fr["code"] and not ends(stmts):
            for code in reversed(fr["code"]):
                s.L.extend(code)

    def uscita(s, solo_ciclo):
        """C dei 'rimanda' da eseguire uscendo: tutti (ritorna) o fino al ciclo (interrompi/continua)."""
        out = []
        for fr in reversed(s.dframes):
            for code in reversed(fr["code"]):
                out.extend(code)
            if solo_ciclo and fr["loop"]:
                break
        return out

    def check_defer(s, n, loops):
        if n.k == "ret":
            s.err("'ritorna' non e' permesso dentro 'rimanda'", n.line)
        if n.k == "defer":
            s.err("'rimanda' dentro 'rimanda' non e' permesso", n.line)
        if n.k in ("break", "continue") and not loops:
            s.err(f"'{'interrompi' if n.k == 'break' else 'continua'}' non puo' uscire da un 'rimanda'", n.line)
        inner = loops + (n.k in ("while", "range", "each"))
        for v in n.__dict__.values():
            for c in (v if isinstance(v, list) else [v]):
                if isinstance(c, N):
                    s.check_defer(c, inner)

    def st_defer(s, n, ind):
        s.check_defer(n.istr, 0)
        saved, s.L = s.L, []
        s.scopes.append({})
        s.put(ind, "{")
        s.st(n.istr, ind + 1)
        s.put(ind, "}")
        s.scopes.pop()
        code, s.L = s.L, saved
        s.dframes[-1]["code"].append(code)

    def st_var(s, n, ind):
        if n.ty is not None:
            s.check_type(n.ty, n.line, True)
        if n.init is None:
            if n.ty is None:
                s.err("serve un tipo oppure un valore iniziale", n.line)
            if not n.mut:
                s.err("una costante ha bisogno di un valore", n.line)
            t, code = n.ty, "{0}"
        elif n.ty is None:
            e = s.ex(n.init)
            t, code = e.t, e.c
            if t == VOID:
                s.err("questo valore non ha un tipo (vuoto)", n.line)
        else:
            t, code = n.ty, s.coerce(n.init, n.ty, True)
        org = s.borrow(n.init) if (n.init is not None and s.holds(t)) else 0
        cv = s.declare(n.name, t, n.mut, n.line, org)
        s.put(ind, f"{s.ctype(t)} {cv} = {code};")

    def st_if(s, n, ind):
        s.put(ind, f"if ({s.cond_code(n.c)}) {{")
        s.body(n.b, ind + 1)
        if n.els is not None:
            s.put(ind, "} else {")
            s.body(n.els, ind + 1)
        s.put(ind, "}")

    def st_while(s, n, ind):
        s.put(ind, f"while ({s.cond_code(n.c)}) {{")
        s.loops += 1
        s.body(n.b, ind + 1, True)
        s.loops -= 1
        s.put(ind, "}")

    def st_range(s, n, ind):
        if s.is_lit(n.a) and not s.is_lit(n.b):
            b = s.ex(n.b)
            a = s.ex(n.a, b.t)
        else:
            a = s.ex(n.a)
            b = s.ex(n.b, a.t)
        if a.t != b.t or not is_int(a.t):
            s.err("gli estremi di 'per' devono essere interi dello stesso tipo", n.line)
        u = s.uid()
        s.scopes.append({})
        cv = s.declare(n.v, a.t, False, n.line)
        s.put(ind, f"for ({s.ctype(a.t)} {cv} = {a.c}, _e{u} = {b.c}; {cv} < _e{u}; {cv}++) {{")
        s.loops += 1
        s.stmts(n.body, ind + 1, True)
        s.loops -= 1
        s.put(ind, "}")
        s.scopes.pop()

    def st_each(s, n, ind):
        e = s.ex(n.e)
        code, st = s.as_slice(e, n.e, True)
        u = s.uid()
        s.scopes.append({})
        cv = s.declare(n.v, st[1], False, n.line, s.borrow(n.e) if s.holds(st[1]) else 0)
        s.put(ind, "{")
        s.put(ind + 1, f"{s.ctype(st)} _s{u} = {code};")
        s.put(ind + 1, f"for (size_t _k{u} = 0; _k{u} < _s{u}.len; _k{u}++) {{")
        s.put(ind + 2, f"{s.ctype(st[1])} {cv} = _s{u}.ptr[_k{u}];")
        s.loops += 1
        s.stmts(n.body, ind + 2, True)
        s.loops -= 1
        s.put(ind + 1, "}")
        s.put(ind, "}")
        s.scopes.pop()

    def st_ret(s, n, ind):
        if n.e is None:
            if s.ret != VOID:
                s.err("manca il valore da ritornare", n.line)
            pend = s.uscita(False)
            if pend:
                s.put(ind, "{")
                s.L.extend(pend)
                s.put(ind + 1, "return;")
                s.put(ind, "}")
            else:
                s.put(ind, "return;")
            return
        if s.ret == VOID:
            s.err("questa funzione non ritorna valori", n.line)
        code = s.coerce(n.e, s.ret, False)
        if s.holds(s.ret) and s.borrow(n.e) > 0:
            s.err("il valore ritornato potrebbe puntare a dati locali: ritorna un "
                  "parametro-fetta, una sua sotto-fetta o una stringa letterale", n.line)
        pend = s.uscita(False)
        if pend:
            s.put(ind, "{")
            s.put(ind + 1, f"{s.ctype(s.ret)} _rv = {code};")
            s.L.extend(pend)
            s.put(ind + 1, "return _rv;")
            s.put(ind, "}")
        else:
            s.put(ind, f"return {code};")

    def st_break(s, n, ind):
        if not s.loops:
            s.err("'interrompi' fuori da un ciclo", n.line)
        pend = s.uscita(True)
        if pend:
            s.put(ind, "{")
            s.L.extend(pend)
            s.put(ind + 1, "break;")
            s.put(ind, "}")
        else:
            s.put(ind, "break;")

    def st_continue(s, n, ind):
        if not s.loops:
            s.err("'continua' fuori da un ciclo", n.line)
        pend = s.uscita(True)
        if pend:
            s.put(ind, "{")
            s.L.extend(pend)
            s.put(ind + 1, "continue;")
            s.put(ind, "}")
        else:
            s.put(ind, "continue;")

    def st_risk(s, n, ind):
        s.risk += 1
        s.put(ind, "{")
        s.body(n.b, ind + 1)
        s.put(ind, "}")
        s.risk -= 1

    def st_blk(s, n, ind):
        s.put(ind, "{")
        s.body(n.b, ind + 1)
        s.put(ind, "}")

    def check_mut(s, n):
        if n.k == "id":
            if not s.lookup(n.name, n.line).mut:
                s.err(f"'{n.name}' non e' modificabile: dichiaralo con 'variabile'", n.line)
        elif n.k == "field":
            s.check_mut(n.e)
        elif n.k == "idx":
            if n.e.T[0] != "s":
                s.check_mut(n.e)
        elif n.k != "un":
            s.err("questa espressione non e' assegnabile", n.line)

    def st_assign(s, n, ind):
        t = s.ex(n.t)
        if not t.lv:
            s.err("a sinistra serve una variabile, un campo o un elemento", n.line)
        s.check_mut(n.t)
        if n.op == "=":
            v = s.coerce(n.v, t.t, False)
            if n.t.k == "field" and n.t.e.T[0] == "st":
                s.check_bits(n.t.e.T[1], n.t.name, n.v)
            if s.holds(t.t):
                o = s.borrow(n.v)
                hd, root = s.holder(n.t)
                if hd is not None and o > hd:
                    s.err("la fetta sopravvivrebbe ai dati a cui punta (dichiarati in un "
                          "blocco piu' interno): i dati devono vivere almeno quanto la fetta", n.line)
                if root is not None:
                    root.org = max(root.org, o)
        else:
            if not s.pure(n.t):
                s.err("in '+=', '-=', ... la parte sinistra non puo' contenere chiamate", n.line)
            b = N("bin", n.line, op=n.op[:-1], l=n.t, r=n.v)
            e = s.ex(b, t.t)
            if e.t != t.t:
                s.err(f"tipo diverso: atteso {tstr(t.t)}, trovato {tstr(e.t)}", n.line)
            v = e.c
        s.put(ind, f"{t.c} = {v};")

    def st_expr(s, n, ind):
        if n.e.k != "call":
            s.err("questa espressione non fa nulla", n.line)
        s.put(ind, f"{s.ex(n.e).c};")

    # ----- livello superiore -----
    def def_struct(s, it):
        if not it.fields:
            s.err(f"la struttura '{it.name}' deve avere almeno un campo", it.line)
        fields, seen, parts = [], set(), []
        for f in it.fields:
            if f.name in seen:
                s.err(f"il campo '{f.name}' e' ripetuto", f.line)
            seen.add(f.name)
            s.check_type(f.ty, f.line, True)
            fields.append((f.name, f.ty))
            w = getattr(f, "bits", None)
            if w is None:
                parts.append(f"{s.ctype(f.ty)} m_{s.cid(f.name)};")
            else:
                if f.ty[0] != "p" or f.ty[1] not in ("u8", "u16", "u32", "u64", "bool"):
                    s.err("i campi a bit possono essere solo u8, u16, u32, u64 o booleano", f.line)
                lim = 1 if f.ty[1] == "bool" else BITS[f.ty[1]]
                if not 1 <= w <= lim:
                    s.err(f"un campo {tstr(f.ty)} puo' avere da 1 a {lim} bit, non {w}", f.line)
                s.bits[(it.name, f.name)] = w
                parts.append(f"{s.ctype(f.ty)} m_{s.cid(f.name)} : {w};")
        s.structs[it.name] = fields
        s.defined.add(it.name)
        attr = " __attribute__((packed))" if getattr(it, "packed", False) else ""
        s.tdecl.append(f"struct{attr} S_{s.cid(it.name)} {{ {' '.join(parts)} }};")

    def check_bits(s, sname, fname, node):
        w = s.bits.get((sname, fname))
        if w is None:
            return
        v = s.const_int(node)
        if v is None and node.k == "bool":
            v = int(node.val)
        if v is not None and not 0 <= v < (1 << w):
            s.err(f"il valore {v} non sta in {w} bit (il campo '{fname}' va da 0 a {(1 << w) - 1})", node.line)

    def reg_gstruct(s, it):
        if it.name in s.structs or it.name in s.gstructs:
            s.err(f"la struttura '{it.name}' e' gia' definita", it.line)
        for i, tp in enumerate(it.tparams):
            if tp in it.tparams[:i]:
                s.err(f"il parametro di tipo '{tp}' e' ripetuto", it.line)
            if tp in s.structs or tp in PRIMS or tp in ALIAS_TIPI or tp == "testo":
                s.err(f"'{tp}' e' gia' un tipo: scegli un altro nome per il parametro", it.line)
        s.gstructs[it.name] = it

    def inst_struct(s, gname, args, line):
        g = s.gstructs[gname]
        if len(args) != len(g.tparams):
            s.err(f"'{gname}' vuole {len(g.tparams)} tipi tra < >, ne ha ricevuti {len(args)}", line)
        nome = gname + "__" + "_".join(s.mangle(a) for a in args)
        if nome not in s.structs:
            s.ninst += 1
            if s.ninst > 200:
                s.err("troppe istanze generiche (ricorsione infinita sui tipi?)", line)
            s.structs[nome] = []
            s.ginst[nome] = (gname, args)
            b = dict(zip(g.tparams, args))
            campi = [N("campo_def", f.line, name=f.name, ty=s.norm_tipo(sost(f.ty, b), f.line),
                       bits=getattr(f, "bits", None)) for f in g.fields]
            s.def_struct(N("struct", g.line, name=nome, fields=campi, tparams=[],
                           packed=getattr(g, "packed", False)))
        return nome

    def norm_tipo(s, t, line):
        """Trasforma i tipi generici concreti (Vettore<i32>) nelle strutture vere."""
        k = t[0]
        if k == "g":
            if t[1] not in s.gstructs:
                s.err(f"'{t[1]}' non e' una struttura generica", line)
            return ("st", s.inst_struct(t[1], tuple(s.norm_tipo(a, line) for a in t[2]), line))
        if k in ("s", "ptr"):
            return (k, s.norm_tipo(t[1], line))
        if k == "a":
            return ("a", s.norm_tipo(t[1], line), t[2])
        return t

    def norm(s, x, line=0):
        if isinstance(x, N):
            y = copy.copy(x)
            for k, v in x.__dict__.items():
                if k not in ("k", "line", "file"):
                    setattr(y, k, s.norm(v, x.line))
            return y
        if isinstance(x, list):
            return [s.norm(v, line) for v in x]
        if isinstance(x, tuple):
            if x and isinstance(x[0], str) and es_tipo(x):
                return s.norm_tipo(x, line)
            return tuple(s.norm(v, line) for v in x)
        return x

    def slit_istanza(s, n, hint):
        g = s.gstructs[n.name]
        if hint and hint[0] == "st" and s.ginst.get(hint[1], (None,))[0] == n.name:
            return hint[1]
        defs = {f.name: f.ty for f in g.fields}
        b = {}
        for f in n.fields:
            if f.name not in defs:
                s.err(f"la struttura '{n.name}' non ha il campo '{f.name}'", f.line)
        ordine = [f for f in n.fields if not s.is_lit(f.e)] + [f for f in n.fields if s.is_lit(f.e)]
        for f in ordine:
            pt = defs[f.name]
            pronto = sost(pt, b)
            e = s.ex(f.e, None if ha_param(pronto, g.tparams) else s.norm_tipo(pronto, f.line))
            s.unifica(pt, e.t, g.tparams, b, f.line)
        for tp in g.tparams:
            if tp not in b:
                s.err(f"non riesco a capire il tipo '{tp}' di '{n.name}': scrivi il tipo, "
                      f"ad esempio variabile v: {n.name}<...> = ...", n.line)
        return s.inst_struct(n.name, tuple(b[tp] for tp in g.tparams), n.line)

    def reg_generic(s, f):
        if f.name in s.funcs or f.name in s.generics or f.name in BUILTIN:
            s.err(f"la funzione '{f.name}' e' gia' definita", f.line)
        if f.name == "principale":
            s.err("'principale' non puo' essere generica", f.line)
        for i, tp in enumerate(f.tparams):
            if tp in f.tparams[:i]:
                s.err(f"il parametro di tipo '{tp}' e' ripetuto", f.line)
            if tp in s.structs or tp in PRIMS or tp in ALIAS_TIPI or tp == "testo":
                s.err(f"'{tp}' e' gia' un tipo: scegli un altro nome per il parametro", f.line)
        s.generics[f.name] = f

    def unifica(s, pt, at, tps, b, line):
        if pt[0] == "st" and pt[1] in tps:
            old = b.get(pt[1])
            if old is None:
                b[pt[1]] = at
            elif old != at:
                s.err(f"il tipo generico '{pt[1]}' vale sia {tstr(old)} sia {tstr(at)}", line)
        elif pt[0] == "g" and at[0] == "st" and at[1] in s.ginst:
            gn, args = s.ginst[at[1]]
            if gn == pt[1]:
                for p2, a2 in zip(pt[2], args):
                    s.unifica(p2, a2, tps, b, line)
        elif pt[0] in ("s", "ptr", "a") and at[0] in ("s", "ptr", "a"):
            s.unifica(pt[1], at[1], tps, b, line)

    def istanzia(s, n):
        """Chiamata a funzione generica: capisce i tipi dagli argomenti e ritorna il nome dell'istanza."""
        g = s.generics[n.name]
        if len(n.args) != len(g.params):
            s.err(f"'{n.name}' vuole {len(g.params)} argomenti, ne ha ricevuti {len(n.args)}", n.line)
        tps, b = g.tparams, {}
        ordine = [i for i, a in enumerate(n.args) if not s.is_lit(a)]
        ordine += [i for i, a in enumerate(n.args) if s.is_lit(a)]
        for i in ordine:
            pt = g.params[i].ty
            pronto = sost(pt, b)
            hint = None if ha_param(pronto, tps) else pronto
            e = s.ex(n.args[i], hint)
            s.unifica(pt, e.t, tps, b, n.line)
        for tp in tps:
            if tp not in b:
                s.err(f"non riesco a capire il tipo generico '{tp}' dagli argomenti di '{n.name}'", n.line)
        nome = n.name + "__" + "_".join(s.mangle(b[tp]) for tp in tps)
        if nome not in s.funcs:
            s.ninst += 1
            if s.ninst > 200:
                s.err("troppe istanze di funzioni generiche (ricorsione infinita sui tipi?)", n.line)
            inst = s.norm(riscrivi(g, b), g.line)
            inst.name, inst.tparams, inst.file = nome, [], getattr(g, "file", None)
            inst.desc = f"{g.name} con " + ", ".join(f"{tp} = {tstr(b[tp])}" for tp in tps)
            s.reg_fn(inst)
            s.pending.append(inst)
        return nome

    def reg_fn(s, f):
        if f.name in s.funcs or f.name in BUILTIN:
            s.err(f"la funzione '{f.name}' e' gia' definita", f.line)
        params = []
        for p in f.params:
            s.check_type(p.ty, p.line, True)
            params.append((p.name, p.ty))
        s.check_type(f.ret, f.line, False)
        if f.name == "principale":
            if params or f.ret not in (I32, VOID):
                s.err("'principale' deve essere: funzione principale() -> i32", f.line)
        s.funcs[f.name] = (params, f.ret, f.extern)
        ct = ", ".join(s.ctype(pt) for _, pt in params) or "void"
        if f.extern:
            s.proto.append(f'extern {s.ctype(f.ret)} x_{s.cid(f.name)}({ct}) __asm__("{f.name}");')
        else:
            s.proto.append(f"static {s.ctype(f.ret)} f_{s.cid(f.name)}({ct});")

    def glob_const(s, n):
        if n.ty is not None:
            s.check_type(n.ty, n.line, True)
        e = s.ex(n.init, n.ty)
        t = n.ty or e.t
        if e.t != t:
            s.err(f"tipo diverso: atteso {tstr(t)}, trovato {tstr(e.t)}", n.line)
        if t[0] != "p" or t == VOID:
            s.err("una costante globale puo' essere solo un numero o un booleano", n.line)
        ok = n.init.k in ("num", "bool") or (
            n.init.k == "un" and n.init.op == "-" and n.init.e.k == "num")
        if not ok:
            s.err("il valore di una costante globale deve essere un letterale", n.line)
        cv = s.declare(n.name, t, False, n.line)
        if is_int(t):
            s.cvals[n.name] = s.const_int(n.init)
        s.glob_lines.append(f"static const {s.ctype(t)} {cv} = {e.c};")

    def gen_fn(s, f):
        params, ret, _ = s.funcs[f.name]
        s.ret, s.loops, s.risk = ret, 0, 0
        s.scopes.append({})
        plist = []
        for pn, pt in params:
            cv = s.declare(pn, pt, False, f.line)
            plist.append(f"{s.ctype(pt)} {cv}")
        s.L = [f'#line {f.line} "{s.cfile}"',
               f"static {s.ctype(ret)} f_{s.cid(f.name)}({', '.join(plist) or 'void'}) {{"]
        s.scopes.append({})
        s.dframes = []
        s.stmts(f.body, 1)
        s.scopes.pop()
        if ret != VOID and not ends(f.body):
            s.err(f"la funzione '{f.name}' non ritorna un valore su tutti i percorsi", f.line)
        s.L.append("}")
        s.scopes.pop()
        s.corpi += s.L

    def programma(s, items):
        for it in items:
            if it.k == "struct" and it.tparams:
                s.entra(it)
                s.reg_gstruct(it)
        items = [it for it in items if not (it.k == "struct" and it.tparams)]
        for it in items:
            if it.k == "struct":
                s.entra(it)
                if it.name in s.structs or it.name in s.gstructs:
                    s.err(f"la struttura '{it.name}' e' gia' definita", it.line)
                s.structs[it.name] = []
        for it in items:
            if it.k == "struct":
                s.entra(it)
                it.fields = s.norm(it.fields, it.line)
                s.def_struct(it)
        for i, it in enumerate(items):
            if (it.k == "fn" and not it.tparams) or it.k == "var":
                s.entra(it)
                items[i] = s.norm(it, it.line)
        for it in items:
            if it.k == "fn":
                s.entra(it)
                if it.tparams:
                    s.reg_generic(it)
                else:
                    s.reg_fn(it)
        for it in items:
            if it.k == "var":
                s.entra(it)
                s.glob_const(it)
        for it in items:
            if it.k == "fn" and not it.extern and not it.tparams:
                s.entra(it)
                s.gen_fn(it)
        while s.pending:
            f = s.pending.pop(0)
            s.entra(f)
            try:
                s.gen_fn(f)
            except ErroreCe as e:
                if " (nell'istanza " not in e.msg:
                    e.msg += f" (nell'istanza {f.desc})"
                raise
        s.entra(N0)
        if "principale" not in s.funcs or s.funcs["principale"][2]:
            s.err("manca la funzione 'principale'", 1)

    def salida(s):
        out = [RUNTIME]
        out += [f"typedef struct S_{s.cid(n)} S_{s.cid(n)};" for n in s.structs]
        out += s.tdecl
        out.append(PRINTERS)
        out += s.glob_lines + s.proto + s.corpi
        if s.funcs["principale"][1] == VOID:
            out.append("int main(void) { f_principale(); return 0; }")
        else:
            out.append("int main(void) { return (int)f_principale(); }")
        return "\n".join(out) + "\n"


def genera(items, fname):
    g = Gen(fname)
    g.programma(items)
    return g.salida()

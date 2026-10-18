# Ce++

A small, safe, all-Italian systems language. It keeps the one good idea of C++
(your code becomes fast native machine code) and drops the 40 years of baggage.
Ce++ compiles to C, then gcc/clang optimize it. The whole compiler is a few
Python files, so it is easy to read, change and fork.

    funzione principale() -> i32 {
        variabile v: [i32; 3] = [10, 20, 30];
        per x in v {
            stampa("valore: ", x);
        }
        ritorna 0;
    }

## Try it

    python3 ce.py run esempi/ciao.ce          # compile and run
    python3 ce.py build prog.ce -o prog       # produce an executable
    python3 ce.py emit prog.ce                # show the generated C
    python3 ce.py ast prog.ce                 # show the parse tree
    python3 tests/esegui.py                   # run the test suite

Needs Python 3 and gcc or clang (GNU C extensions are used).
Set `CC=clang` to pick a compiler. Add `--sanitizza` to build with
AddressSanitizer + UBSan (useful once you use `rischio`).

## The language

Keywords: `funzione struttura variabile costante se altrimenti mentre per in
ritorna interrompi continua vero falso rischio esterna come usa rimanda`.
English keywords (`if`, `while`, `return`, ...) are rejected with a hint
("'if' e' inglese: in Ce++ si scrive 'se'").

Types: `i8 i16 i32 i64 u8 u16 u32 u64 f32 f64` plus Italian aliases
`intero`(i32) `lungo`(i64) `corto`(i16) `byte`/`carattere`(u8) `decimale`(f32)
`doppio`(f64) `booleano` `vuoto` `dimensione`(usize) and `testo` (a slice of
bytes). Arrays are `[T; N]`, slices are `[T]`, raw pointers are `*T`.

Built-ins: `stampa(...)` (with newline), `scrivi(...)`, `panico("msg")`,
`afferma(cond, "msg")`, and `.lunghezza` on arrays and slices.
`riserva(T, n)` allocates `n` zeroed values of type `T` on the heap and gives
a slice (`variabile v: [i32] = riserva(i32, 10);`; it panics if memory runs
out). `libera(v)` frees it and empties `v`; it only works inside `rischio`,
because the compiler cannot check that the slice came from `riserva` or that
nothing else still points to it. Pair them with `rimanda`:

    variabile v: [i32] = riserva(i32, 10);
    rimanda { rischio { libera(v); } }

Heap slices can be returned from functions. Use after `libera` through a copy
of the slice is not detected (known limit below).

## What is enforced today

- Variables are always initialized (to zero if you give no value).
- Integer overflow is defined: it wraps (never undefined behavior).
- Array and slice indexing is always bounds-checked; failures are a clean
  `panico` (exit code 101), not memory corruption.
- Division by zero and over-wide shifts are checked.
- No implicit numeric conversions: use `come`. Float to int saturates.
- Names cannot be shadowed. Loop variables cannot be modified.
- `costante` and function parameters are immutable.
- Every code path of a non-void function must return.
- Raw pointers (`&`, `*`) and calling C functions (`esterna`) only work
  inside a `rischio { }` block.
- Slices cannot outlive the data they point to. Every slice (also inside a
  struct) remembers the block its data lives in: assigning it to something
  that lives longer is an error, and a function can only return slices (or
  structs holding slices) that point to its parameters or to string literals.

## Modules

    usa "geometria.ce";      // at the top level, path relative to this file

Each file is loaded once (diamond imports are fine), imports can nest, and
circular imports are an error. All modules share one namespace: two files
defining the same name is an error (no shadowing, as everywhere in Ce++).
Errors and `panico` messages name the file and line of the module they come from.

## Cleanup with `rimanda`

    variabile f: *Fle = apri(...);
    rimanda chiudi(f);        // runs when the enclosing block exits

`rimanda <statement>` (or `rimanda { ... }`) runs when the enclosing block
ends: at the closing `}`, or earlier through `ritorna`, `interrompi` or
`continua`. Several `rimanda` in one block run in reverse order (last first).
Rules:

- Only the `rimanda` already reached at the exit point run (an early `ritorna`
  before a `rimanda` line does not run it).
- A returned value is computed before the deferred code runs.
- Deferred code reads variables when it runs, not when it was written.
- It cannot contain `ritorna`, or `interrompi`/`continua` that would leave it,
  and cannot contain another `rimanda`.
- `panico` stops the program immediately (exit 101) and does not run them.

## Generic functions

    funzione massimo<T>(a: T, b: T) -> T {
        se a > b { ritorna a; }
        ritorna b;
    }
    stampa(massimo(3, 7));        // T = i32
    stampa(massimo(x, 7));        // x: i64 -> T = i64

Write the function once, use it for any type. The compiler works out `T` from
the arguments (typed values first, then number literals, which take the type
already found) and generates one real function per type, so there is no
runtime cost. `T` can also be used inside the body (`variabile s: T`,
`riserva(T, n)`). Errors inside an instance say which types caused them.

- A generic function is only checked when it is used: an unused one is not
  type-checked.
- If `T` cannot be worked out from the arguments, the compiler tries the type
  you declared for the result (`variabile v: [i32] = crea(3);`). Otherwise
  write it: `crea<i32>(3)`.

## Generic structs and `lib/vettore.ce`

    struttura Coppia<A, B> { primo: A, secondo: B }
    variabile c: Coppia<i32, f64> = Coppia { primo: 1, secondo: 2.5 };

`Coppia<i32, f64>` is a real struct generated for those types. In a literal
the compiler takes the types from the declared type, or from the fields
(`Coppia { primo: 1, secondo: 2.5 }` inside `apri(...)`). Generic structs can
be passed to generic functions (`funzione scambia<A, B>(c: Coppia<A, B>) ->
Coppia<B, A>`) and nested (`Coppia<i32, Coppia<i32, i32>>`).

`lib/vettore.ce` is a growable vector written in Ce++ itself on top of
`riserva`/`libera`:

    usa "lib/vettore.ce";
    variabile v: Vettore<i32> = Vettore { dati: riserva(i32, 0), n: 0 };
    v.aggiungi(5);                 // same as aggiungi(v, 5)
    stampa(v.valore(0));           // bounds-checked
    v.libera_vettore();

Struct fields used by value must still be defined before they are used
(put the plain structs first).

## Reference parameters and `v.f(x)`

    funzione incrementa(x: &i32) { x = x + 1; }
    variabile a: i32 = 10;
    incrementa(a);                 // a is now 11

A parameter of type `&T` receives the caller's variable itself, so the
function can change it. Calling is plain (`incrementa(a)`): the argument must
be a mutable variable, field or element. References are only allowed as
function parameters: they cannot be stored, returned or kept in variables, so
they can never outlive what they point to. Extra checks: the same variable
cannot be passed twice by reference, and a short-lived slice cannot be passed
alongside a reference to something that lives longer (the function could store
it there).

`x.f(y)` is another way to write `f(x, y)`, for any function. That is how
`v.aggiungi(5)` works: there are no classes or `impl` blocks, only functions.

## Standard library (`lib/`, written in Ce++)

| file | gives you |
|---|---|
| `vettore.ce` | `Vettore<T>`: growable array (`aggiungi`, `valore`, `libera_vettore`) |
| `opzione.ce` | `Opzione<T>`: a value that may be missing (`qualcuno`, `nessuno`, `valore_o`, `valore_certo`) |
| `risultato.ce` | `Risultato<T, E>`: a value or an error, no panic (`bene`, `male`) |
| `mappa.ce` | `Mappa<K, V>`: hash map, integer keys (`nuova_mappa`, `inserisci`, `cerca`, `contiene`, `libera_mappa`) |

    usa "lib/mappa.ce";
    variabile m: Mappa<i32, i32> = nuova_mappa();
    m.inserisci(7, 70);
    stampa(m.cerca(7).valore_o(-1));    // 70
    m.libera_mappa();

`Mappa` has no removal yet and only integer keys (it hashes `k come u64`).

## Exact layouts: `impacchettata`, bit fields, `misura`

    struttura Registro impacchettata {
        modo: u8 : 3,          // 3 bits
        attivo: booleano : 1,  // 1 bit
        dato: u16 : 12,        // 12 bits  -> the whole struct is 2 bytes
    }
    stampa(misura(Registro));  // size in bytes: 2

- `: N` after a field type makes it an `N`-bit field. Allowed types: `u8 u16
  u32 u64 booleano` (unsigned only, so there is no implementation-defined
  sign handling). Writing a constant that does not fit is a compile error;
  other values wrap to `N` bits like all Ce++ integers.
- A bit field has no address: `&campo` is an error.
- `impacchettata` removes the padding between fields. Without it the struct
  is laid out like C. Bit order inside a byte follows gcc/clang (first field =
  lowest bits on little-endian machines such as x86 and ARM).
- `misura(T)` gives `sizeof` for a struct or basic type, to check layouts.
- Fields of a packed struct may be unaligned; reading and writing them is
  fine, but handing them to C code through pointers may not be.

## Error messages

The compiler reports every error it can find in one run (each as
`file:line: errore: message`, then `N errori`), not just the first one. A
variable whose declaration failed does not cause a second "unknown name" error
every time it is used. Errors inside a module name the module's file.

## Known limits (v0.1, be honest about them)

- Slice lifetime checking is by block level and conservative: it may reject
  some code that would be safe, and it does not follow raw pointers (`rischio`).
- Heap memory is manual: forgetting `libera` leaks, and using a copy of a slice
  after `libera` is not caught. `riserva` takes only a plain type name.
- Modules are flat (one shared namespace, no `pubblico`/private yet) and the
  map has no removal and only integer keys.
- Global values can only be numeric/boolean constants.
- Error recovery is simple: after a syntax error the compiler skips to the next
  `;` or `}`, so a second error right after a first one can occasionally be a
  consequence of it. At most 30 errors are shown.
- External C functions use asm labels: tested on Linux.

## Where things live (and where forks plug in)

    lessico.py   words, keywords, lexer          -> change the vocabulary here
    sintassi.py  grammar and parse tree           -> change the syntax here
    genera.py    type rules, safety checks, C     -> change semantics/backend here
    ce.py        command line driver
    tests/       one .ce file per rule, expectations in comments

## Ideas for later

Private names / `pubblico`, explicit endianness, map removal and text keys,
a direct backend instead of C.

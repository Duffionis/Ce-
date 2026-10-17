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

## Known limits (v0.1, be honest about them)

- Slice lifetime checking is by block level and conservative: it may reject
  some code that would be safe, and it does not follow raw pointers (`rischio`).
- Heap memory is manual: forgetting `libera` leaks, and using a copy of a slice
  after `libera` is not caught. `riserva` takes only a plain type name.
- Modules are flat (one shared namespace, no `pubblico`/private yet) and there
  are no generics, so no ready-made vector or map yet.
- Global values can only be numeric/boolean constants.
- The compiler reports the first error only.
- External C functions use asm labels: tested on Linux.

## Where things live (and where forks plug in)

    lessico.py   words, keywords, lexer          -> change the vocabulary here
    sintassi.py  grammar and parse tree           -> change the syntax here
    genera.py    type rules, safety checks, C     -> change semantics/backend here
    ce.py        command line driver
    tests/       one .ce file per rule, expectations in comments

## Ideas for later

Private names / `pubblico`, option/result types, generics (vector, map), packed structs and bit fields (emulator work),
a direct backend instead of C.

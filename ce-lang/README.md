# Ce++

Un linguaggio di sistema piccolo, sicuro e tutto italiano. Tiene l'unica buona
idea del C++ (il codice diventa veloce codice macchina nativo) e lascia
indietro 40 anni di bagaglio. Ce++ compila in C, poi gcc/clang lo ottimizzano.
L'intero compilatore sono pochi file Python: facile da leggere, modificare e
fare fork.

    funzione principale() -> intero {
        variabile v: [intero; 3] = [10, 20, 30];
        per x in v {
            stampa("valore: ", x);
        }
        ritorna 0;
    }

## Provalo

    python3 ce.py esegui esempi/ciao.ce       # compila ed esegue
    python3 ce.py compila prog.ce -o prog     # produce un eseguibile
    python3 ce.py emetti prog.ce              # mostra il C generato
    python3 ce.py albero prog.ce              # mostra l'albero sintattico
    python3 tests/esegui.py                   # esegue i test

Servono Python 3 e gcc o clang (si usano estensioni GNU C).
Imposta `CC=clang` per scegliere il compilatore. Aggiungi `--sanitizza` per
compilare con AddressSanitizer + UBSan (utile quando usi `rischio`).
I vecchi nomi dei comandi (`run`, `build`, `emit`, `ast`, `tokens`) funzionano
ancora.

## Il linguaggio

Parole chiave: `funzione struttura variabile costante se altrimenti mentre per
in ritorna interrompi continua vero falso rischio esterna come usa rimanda
impacchettata scegli caso elenco`. Le parole inglesi (`if`, `while`, `return`, ...) vengono
rifiutate con un suggerimento ("'if' non e' Ce++: si scrive 'se'").

Tipi, tutti con nome italiano:

| tipo | significato | sinonimi |
|---|---|---|
| `intero8` `intero16` `intero32` `intero64` | interi con segno | `corto` = `intero16`, `intero` = `intero32`, `lungo` = `intero64` |
| `naturale8` `naturale16` `naturale32` `naturale64` | interi senza segno | `byte` e `carattere` = `naturale8` |
| `dimensione` | dimensione di un oggetto (come `size_t`) | |
| `reale32` `reale64` | numeri in virgola mobile | `decimale` = `reale32`, `doppio` = `reale64` |
| `booleano` `vuoto` | vero/falso, nessun valore | |
| `testo` | fetta di byte | |

Le vecchie sigle in stile Rust (`i32`, `u8`, `f64`, `usize`...) non esistono:
il compilatore le rifiuta e dice quale nome usare. Gli array sono `[T; N]`, le
fette `[T]`, i puntatori grezzi `*T`.

Funzioni integrate: `stampa(...)` (con a capo), `scrivi(...)`,
`panico("msg")`, `afferma(cond, "msg")`, e `.lunghezza` su array e fette.
`riserva(T, n)` alloca `n` valori azzerati di tipo `T` sull'heap e restituisce
una fetta (`variabile v: [intero] = riserva(intero, 10);`; va in panico se la
memoria finisce). `libera(v)` la libera e svuota `v`; funziona solo dentro
`rischio`, perche' il compilatore non puo' verificare che la fetta venga da
`riserva` o che nient'altro la usi ancora. Abbinale a `rimanda`:

    variabile v: [intero] = riserva(intero, 10);
    rimanda { rischio { libera(v); } }

Le fette dell'heap si possono restituire dalle funzioni. L'uso dopo `libera`
tramite una copia della fetta non viene rilevato (vedi i limiti).

## Cosa viene garantito oggi

- Le variabili sono sempre inizializzate (a zero se non dai un valore).
- L'overflow degli interi e' definito: va a capo (mai comportamento indefinito).
- L'indicizzazione di array e fette controlla sempre i limiti; un errore e'
  un `panico` pulito (codice di uscita 101), non corruzione della memoria.
- Divisione per zero e scorrimenti troppo larghi sono controllati.
- Nessuna conversione numerica implicita: usa `come`. Da reale a intero satura.
- I nomi non si possono nascondere (niente shadowing). Le variabili dei cicli
  non si modificano.
- `costante` e i parametri delle funzioni sono immutabili.
- Ogni percorso di una funzione non `vuoto` deve ritornare.
- I puntatori grezzi (`&`, `*`) e le chiamate a funzioni C (`esterna`)
  funzionano solo dentro un blocco `rischio { }`.
- Le fette non possono sopravvivere ai dati a cui puntano. Ogni fetta (anche
  dentro una struttura) ricorda il blocco in cui vivono i suoi dati:
  assegnarla a qualcosa che vive di piu' e' un errore, e una funzione puo'
  restituire solo fette (o strutture con fette) che puntano ai suoi parametri
  o a letterali di testo.

## Scelta multipla con `scegli`

    scegli n {
        caso 1 { stampa("uno"); }
        caso 2, 3 { stampa("due o tre"); }
        altrimenti { stampa("altro"); }
    }

Il valore si calcola una volta sola e si confronta con ogni `caso`, in ordine.
Non c'e' "caduta" da un caso al successivo (niente `break` dimenticato come in C),
un caso ripetuto e' un errore, e `interrompi`/`continua` dentro un `caso`
riguardano il ciclo che lo contiene. Con `altrimenti` che ritorna in tutti i
rami, la funzione conta come "ritorna su tutti i percorsi". Le etichette devono
essere numeri, caratteri, `vero`/`falso` o nomi; usa `costante` per i nomi
(il compilatore ancora non controlla che lo siano).

## Variabili globali e `elenco`

    variabile contatore: naturale32;        // parte da zero
    variabile passo: intero = -2;           // valore iniziale: solo un letterale
    variabile memoria: [byte; 65536];       // array e strutture partono azzerati

    elenco: naturale16 { NOP, LDI, ADD = 10, SUB, XOR }   // 0, 1, 10, 11, 12

Una `variabile` al livello alto e' condivisa da tutte le funzioni (e dai moduli).
Puo' essere un numero, un booleano, un array o una struttura, ma senza fette (una
fetta potrebbe puntare a dati che muoiono). Come ogni nome in Ce++, non si puo'
nascondere con una variabile locale. `elenco` numera delle costanti
(`: tipo` e' facoltativo, di base `intero`); non crea un tipo nuovo, quindi il
compilatore non impedisce di mescolare numeri e nomi dell'elenco.

## Operazioni sui bit: `lib/bit.ce`

    usa "lib/bit.ce";
    ruota_sx(x, 3)   ruota_dx(x, 3)   conta_bit(x)   bit(x, i)   imposta_bit(x, i, vero)

Funzionano per qualsiasi intero senza segno (`byte`, `naturale16`...).

## Puntatori a funzione

    funzione raddoppia(x: intero) -> intero { ritorna x * 2; }
    variabile h: funzione(intero) -> intero = raddoppia;
    stampa(h(21));                                       // 42
    variabile tabella: [funzione(intero) -> intero; 4];  // per esempio una tabella di istruzioni
    tabella[0] = raddoppia;  stampa(tabella[0](5));

Il tipo si scrive `funzione(tipi...) -> tipo`. Il nome di una funzione e' un valore di quel tipo.
Un puntatore non impostato e' nullo, e chiamarlo e' un `panico` pulito ("puntatore a funzione nullo"),
non un crash. Limiti: niente funzioni generiche, `esterna` o con parametri `&` come valori, e il
risultato non puo' essere una fetta.

## File: `lib/file.ce`

    usa "lib/file.ce";
    variabile r: Risultato<[byte], testo> = leggi_file("rom.bin");
    se r.riuscito { stampa(r.valore.lunghezza); } altrimenti { stampa(r.errore); }
    scrivi_file("salvataggio.bin", dati);

`leggi_file` legge tutto il file in memoria dell'heap (libera la fetta con `libera` dentro
`rischio`), `scrivi_file` crea o sovrascrive. Gli errori tornano come `Risultato`, senza panico.
La libreria usa `fopen`/`fread`/... del C, quindi quei nomi sono riservati.

## Cicli con il tipo scelto

    per i: dimensione in 0..80 { memoria[i] = 0; }

Di base gli estremi letterali di `per` sono `intero`; con `: tipo` scegli un altro tipo intero
(comodo per gli indici, che sono `dimensione`). Solo nei cicli su un intervallo.

## Argomenti da riga di comando

    per i in 1..numero_argomenti() { stampa(argomento(i)); }   // ./prog uno due

`numero_argomenti()` conta anche il nome del programma (argomento 0), come `argc` in C.
`argomento(i)` ritorna un `testo`; un numero troppo grande e' un `panico`.
Con il compilatore: `python3 ce.py esegui prog.ce uno due`.

## Strumenti

    python3 ce.py formatta prog.ce            # stampa il file con i rientri a posto
    python3 ce.py formatta prog.ce --scrivi   # lo riscrive
    python3 ce.py esegui prog.ce --debug      # senza ottimizzazioni e con simboli: si puo' usare gdb
    python3 ce.py compila prog.ce -o prog -l m -L /percorso    # collega librerie C (-lm ...)

Il formattatore cambia solo gli spazi (rientri di 4, niente spazi a fine riga, al massimo una riga vuota
di seguito): mai le parole, e non sposta le graffe. Con `--debug` i messaggi di gdb mostrano le righe
del tuo file `.ce`, non quelle del C. Per i colori in VS Code vedi `editor/vscode/README.md`.

Librerie condivise: `usa "@testo.ce";` cerca `testo.ce` nella libreria standard del compilatore
(la cartella `lib/`), poi nelle cartelle di `CE_PERCORSO` (separate da `:`), cosi' non servono percorsi
relativi come `../lib/testo.ce`. E' il minimo che serve oggi al posto di un gestore di pacchetti.

## Moduli

    usa "geometria.ce";      // al livello alto, percorso relativo a questo file

Ogni file viene caricato una volta sola (gli import a diamante vanno bene), gli
import possono annidarsi e quelli circolari sono un errore. Tutti i moduli
condividono un solo spazio dei nomi: due file che definiscono lo stesso nome
sono un errore (niente shadowing, come ovunque in Ce++). Errori e messaggi di
`panico` indicano file e riga del modulo di origine.

## Pulizia con `rimanda`

    variabile f: *Fle = apri(...);
    rimanda chiudi(f);        // gira quando il blocco che lo contiene finisce

`rimanda <istruzione>` (o `rimanda { ... }`) gira quando il blocco che lo
contiene termina: alla `}` finale, o prima con `ritorna`, `interrompi` o
`continua`. Piu' `rimanda` nello stesso blocco girano in ordine inverso
(l'ultimo per primo). Regole:

- Girano solo i `rimanda` gia' raggiunti nel punto di uscita (un `ritorna`
  anticipato prima di una riga `rimanda` non la esegue).
- Il valore restituito viene calcolato prima del codice rimandato.
- Il codice rimandato legge le variabili quando gira, non quando e' scritto.
- Non puo' contenere `ritorna`, ne' `interrompi`/`continua` che lo
  abbandonerebbero, ne' un altro `rimanda`.
- `panico` ferma subito il programma (uscita 101) e non li esegue.

## Funzioni generiche

    funzione massimo<T>(a: T, b: T) -> T {
        se a > b { ritorna a; }
        ritorna b;
    }
    stampa(massimo(3, 7));        // T = intero
    stampa(massimo(x, 7));        // x: lungo -> T = lungo

Scrivi la funzione una volta, usala per qualsiasi tipo. Il compilatore ricava
`T` dagli argomenti (prima i valori con tipo, poi i numeri letterali, che
prendono il tipo gia' trovato) e genera una funzione vera per ogni tipo,
quindi nessun costo a runtime. `T` si puo' usare anche nel corpo
(`variabile s: T`, `riserva(T, n)`). Gli errori dentro un'istanza dicono
quali tipi li hanno causati.

- Una funzione generica viene controllata solo quando e' usata.
- Se `T` non si ricava dagli argomenti, il compilatore prova con il tipo
  dichiarato per il risultato (`variabile v: [intero] = crea(3);`). Altrimenti
  scrivilo: `crea<intero>(3)`.

## Strutture generiche e `lib/vettore.ce`

    struttura Coppia<A, B> { primo: A, secondo: B }
    variabile c: Coppia<intero, doppio> = Coppia { primo: 1, secondo: 2.5 };

`Coppia<intero, doppio>` e' una struttura vera generata per quei tipi. In un
letterale il compilatore prende i tipi dal tipo dichiarato o dai campi. Le
strutture generiche si passano a funzioni generiche
(`funzione scambia<A, B>(c: Coppia<A, B>) -> Coppia<B, A>`) e si annidano
(`Coppia<intero, Coppia<intero, intero>>`).

`lib/vettore.ce` e' un vettore dinamico scritto in Ce++ stesso sopra
`riserva`/`libera`:

    usa "lib/vettore.ce";
    variabile v: Vettore<intero> = Vettore { dati: riserva(intero, 0), n: 0 };
    v.aggiungi(5);                 // come aggiungi(v, 5)
    stampa(v.valore(0));           // con controllo dei limiti
    v.libera_vettore();

I campi struttura usati per valore devono comunque essere definiti prima di
essere usati (metti prima le strutture semplici).

## Parametri per riferimento e `v.f(x)`

    funzione incrementa(x: &intero) { x = x + 1; }
    variabile a: intero = 10;
    incrementa(a);                 // ora a vale 11

Un parametro di tipo `&T` riceve la variabile stessa di chi chiama, quindi la
funzione puo' modificarla. La chiamata e' semplice (`incrementa(a)`): l'argomento
deve essere una variabile, un campo o un elemento modificabile. I riferimenti
sono ammessi solo come parametri: non si possono memorizzare, restituire o
tenere in variabili, quindi non sopravvivono mai a cio' a cui puntano. Altri
controlli: la stessa variabile non si passa due volte per riferimento, e una
fetta di vita breve non si passa insieme a un riferimento a qualcosa che vive
di piu' (la funzione potrebbe salvarcela).

`x.f(y)` e' un altro modo di scrivere `f(x, y)`, per qualsiasi funzione. Cosi'
funziona `v.aggiungi(5)`: niente classi o blocchi `impl`, solo funzioni.

## Libreria standard (`lib/`, scritta in Ce++)

| file | cosa offre |
|---|---|
| `vettore.ce` | `Vettore<T>`: array dinamico (`aggiungi`, `valore`, `libera_vettore`) |
| `opzione.ce` | `Opzione<T>`: un valore che puo' mancare (`qualcuno`, `nessuno`, `valore_o`, `valore_certo`) |
| `risultato.ce` | `Risultato<T, E>`: un valore o un errore, senza panico (`bene`, `male`) |
| `mappa.ce` | `Mappa<K, V>`: tabella hash, chiavi intere (`nuova_mappa`, `inserisci`, `cerca`, `contiene`, `rimuovi`, `libera_mappa`) |
| `mappa_testo.ce` | `MappaTesto<V>`: tabella hash con chiavi `testo` copiate (`nuova_mappa_testo`, `inserisci_t`, `cerca_t`, `contiene_t`, `rimuovi_t`, `libera_mappa_testo`) |
| `testo.ce` | `Stringa` che cresce (`aggiungi_testo`, `aggiungi_numero`, `come_testo`), `numero_da_testo`, `testo_uguale`, `inizia_con`, `finisce_con`, `cerca_testo`, `taglia` |
| `ordina.ce` | `ordina(v)` (heapsort, ogni tipo con `<`), `e_ordinata(v)` |
| `bit.ce` | rotazioni, `conta_bit`, `bit`, `imposta_bit` |
| `file.ce` | `leggi_file`, `scrivi_file` |

    usa "lib/mappa.ce";
    variabile m: Mappa<intero, intero> = nuova_mappa();
    m.inserisci(7, 70);
    stampa(m.cerca(7).valore_o(-1));    // 70
    m.libera_mappa();

`Mappa` accetta solo chiavi intere (calcola l'hash di `k come naturale64`); per le chiavi
di testo usa `MappaTesto`.

## Disposizione esatta: `impacchettata`, campi a bit, `misura`

    struttura Registro impacchettata {
        modo: byte : 3,          // 3 bit
        attivo: booleano : 1,    // 1 bit
        dato: naturale16 : 12,   // 12 bit -> tutta la struttura e' di 2 byte
    }
    stampa(misura(Registro));    // dimensione in byte: 2

- `: N` dopo il tipo di un campo lo rende un campo di `N` bit. Tipi ammessi:
  `byte naturale16 naturale32 naturale64 booleano` (solo senza segno, cosi'
  non c'e' gestione del segno dipendente dall'implementazione). Scrivere una
  costante che non ci sta e' un errore di compilazione; gli altri valori
  vanno a capo su `N` bit come tutti gli interi di Ce++.
- Un campo a bit non ha indirizzo: `&campo` e' un errore.
- `impacchettata` toglie il riempimento tra i campi. Senza, la struttura e'
  disposta come in C. L'ordine dei bit in un byte segue gcc/clang (primo campo
  = bit piu' bassi su macchine little-endian come x86 e ARM).
- `misura(T)` da' `sizeof` di una struttura o di un tipo base.
- I campi di una struttura impacchettata possono essere non allineati; leggerli
  e scriverli va bene, ma passarli a codice C tramite puntatori potrebbe no.

## Messaggi di errore

Il compilatore segnala tutti gli errori che trova in una sola esecuzione
(ognuno come `file:riga: errore: messaggio`, poi `N errori`), non solo il
primo. Una variabile la cui dichiarazione e' fallita non causa un secondo
errore "nome sconosciuto" a ogni uso. Per i segni mancanti il messaggio indica la riga giusta
("manca ';' alla fine di questa riga"), e una `}` mancante o in piu' viene segnalata subito
invece di produrre una valanga di errori. Gli errori dentro un modulo indicano il
file del modulo. I tipi nei messaggi hanno nomi italiani.

## Limiti noti (v0.1, onesti)

- Il controllo della vita delle fette e' a livello di blocco e prudente: puo'
  rifiutare codice che sarebbe sicuro, e non segue i puntatori grezzi (`rischio`).
- La memoria dell'heap e' manuale: dimenticare `libera` perde memoria, e usare
  una copia di una fetta dopo `libera` non viene rilevato. `riserva` accetta
  solo un semplice nome di tipo.
- I moduli sono piatti (un solo spazio dei nomi, ancora niente `pubblico`/privato)
  e la mappa `Mappa` ha solo chiavi intere.
- Le variabili globali non possono contenere fette e il valore iniziale e' solo un letterale.
- Il recupero dopo gli errori e' semplice: dopo un errore di sintassi il
  compilatore salta al prossimo `;` o `}`, quindi un secondo errore subito dopo
  il primo puo' a volte esserne una conseguenza. Si mostrano al massimo 30 errori.
- Le funzioni C esterne usano etichette asm: provato su Linux.

## Dove sta cosa (e dove si agganciano i fork)

    lessico.py   parole, parole chiave, lessico   -> cambia qui il vocabolario
    sintassi.py  grammatica e albero              -> cambia qui la sintassi
    genera.py    regole dei tipi, controlli, C    -> cambia qui semantica/backend
    ce.py        programma da riga di comando
    tests/       un file .ce per regola, attese nei commenti

## Idee per dopo

Nomi privati / `pubblico`, endianness esplicita, un backend diretto al posto del C.

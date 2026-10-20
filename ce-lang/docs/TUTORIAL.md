# Ce++ in 15 minuti

Ce++ e' un linguaggio di sistema piccolo, veloce e sicuro, tutto in italiano. Questo tutorial parte
da zero. Ogni esempio qui sotto viene compilato ed eseguito dai test: se lo copi, funziona.

Ti serve solo Python 3 e `gcc` o `clang`. Salva gli esempi in un file `prova.ce` ed eseguili con

    python3 ce.py esegui prova.ce

## 1. Il primo programma

```ce
funzione principale() -> intero {
    stampa("Ciao, mondo!");
    ritorna 0;
}
```
```uscita
Ciao, mondo!
```

Ogni programma comincia da `principale`. `ritorna 0` dice al sistema che e' andato tutto bene.
`stampa` scrive e va a capo; `scrivi` scrive senza andare a capo.

## 2. Variabili e tipi

```ce
funzione principale() -> intero {
    variabile eta: intero = 30;
    costante pi: doppio = 3.14159;
    variabile nome: testo = "Ram";
    eta = eta + 1;
    stampa(nome, " ha ", eta, " anni; pi = ", pi);
    ritorna 0;
}
```
```uscita
Ram ha 31 anni; pi = 3.14159
```

- `variabile` si puo' cambiare, `costante` no.
- I tipi hanno nomi italiani: `intero`, `lungo`, `byte`, `doppio`, `booleano`, `testo`. Per le
  dimensioni esatte ci sono `intero8`, `naturale16`, `reale32`... (vedi il README).
- Una variabile senza valore parte sempre da zero: niente "valori a caso" come in C.
- Non ci sono conversioni nascoste: per passare da un tipo a un altro scrivi `come`:

```ce
funzione principale() -> intero {
    variabile grande: lungo = 300;
    variabile piccolo: byte = grande come byte;
    stampa(piccolo);
    ritorna 0;
}
```
```uscita
44
```

Gli interi non vanno mai in "comportamento indefinito": se superano il massimo, ricominciano da
capo (qui 300 diventa 300 - 256 = 44).

## 3. Decisioni e cicli

```ce
funzione principale() -> intero {
    per i in 1..6 {
        se i % 2 == 0 {
            stampa(i, " e' pari");
        } altrimenti {
            stampa(i, " e' dispari");
        }
    }
    variabile n: intero = 3;
    mentre n > 0 {
        scrivi(n, " ");
        n = n - 1;
    }
    stampa("via!");
    ritorna 0;
}
```
```uscita
1 e' dispari
2 e' pari
3 e' dispari
4 e' pari
5 e' dispari
3 2 1 via!
```

`1..6` va da 1 a 5 (il 6 e' escluso). Usa `interrompi` per uscire da un ciclo e `continua` per
passare al giro dopo.

## 4. Funzioni

```ce
funzione quadrato(x: intero) -> intero {
    ritorna x * x;
}

funzione saluta(nome: testo) {
    stampa("Ciao, ", nome, "!");
}

funzione principale() -> intero {
    saluta("mondo");
    stampa(quadrato(7));
    ritorna 0;
}
```
```uscita
Ciao, mondo!
49
```

Una funzione senza `->` non restituisce niente. I parametri non si possono modificare; se vuoi che
la funzione cambi la tua variabile, scrivi `&` davanti al tipo:

```ce
funzione raddoppia(x: &intero) {
    x = x * 2;
}

funzione principale() -> intero {
    variabile a: intero = 21;
    raddoppia(a);
    stampa(a);
    ritorna 0;
}
```
```uscita
42
```

## 5. Array e fette: i limiti sono sempre controllati

```ce
funzione somma(numeri: [intero]) -> intero {
    variabile totale: intero = 0;
    per x in numeri {
        totale = totale + x;
    }
    ritorna totale;
}

funzione principale() -> intero {
    variabile v: [intero; 4] = [10, 20, 30, 40];
    stampa(somma(v));
    stampa(v.lunghezza);
    stampa(somma(v[1..3]));
    ritorna 0;
}
```
```uscita
100
4
50
```

`[intero; 4]` e' un array di 4 elementi; `[intero]` e' una "fetta": una vista su un pezzo di
array (`v[1..3]` sono gli elementi 1 e 2). Se scrivi un indice sbagliato, il programma si ferma subito
con un messaggio chiaro invece di rovinare la memoria:

```ce-panico
funzione principale() -> intero {
    variabile v: [intero; 3] = [1, 2, 3];
    variabile i: dimensione = 5;
    stampa(v[i]);
    ritorna 0;
}
```

Questo programma finisce con `panico: indice 5 fuori dai limiti (lunghezza 3)` (codice di uscita 101).
In C sarebbe stato un bug silenzioso.

## 6. Strutture

```ce
struttura Punto {
    x: intero,
    y: intero,
}

funzione distanza_quadra(a: Punto, b: Punto) -> intero {
    costante dx: intero = a.x - b.x;
    costante dy: intero = a.y - b.y;
    ritorna dx * dx + dy * dy;
}

funzione principale() -> intero {
    variabile p: Punto = Punto { x: 0, y: 0 };
    variabile q: Punto = Punto { x: 3, y: 4 };
    stampa(distanza_quadra(p, q));
    ritorna 0;
}
```
```uscita
25
```

## 7. Scelte multiple con `scegli`

```ce
funzione nome_del_giorno(g: intero) -> testo {
    scegli g {
        caso 1 { ritorna "lunedi'"; }
        caso 2 { ritorna "martedi'"; }
        caso 6, 7 { ritorna "fine settimana"; }
        altrimenti { ritorna "un altro giorno"; }
    }
}

funzione principale() -> intero {
    stampa(nome_del_giorno(1));
    stampa(nome_del_giorno(7));
    stampa(nome_del_giorno(4));
    ritorna 0;
}
```
```uscita
lunedi'
fine settimana
un altro giorno
```

Non c'e' "caduta" da un caso al successivo: niente `break` dimenticato come in C.

## 8. Errori senza far crollare il programma

Per le cose che possono andare male (un file che non c'e', un numero scritto male) si usa
`Risultato`: o un valore o un messaggio d'errore.

```ce
usa "@testo.ce";

funzione leggi_eta(t: testo) -> Risultato<lungo, testo> {
    costante r: Risultato<lungo, testo> = numero_da_testo(t);
    se !r.riuscito { ritorna male(r.errore); }
    se r.valore < 0 || r.valore > 150 { ritorna male("eta' impossibile"); }
    ritorna bene(r.valore);
}

funzione prova(t: testo) {
    costante r: Risultato<lungo, testo> = leggi_eta(t);
    se r.riuscito { stampa(t, ": ok, ", r.valore); }
    altrimenti { stampa(t, ": errore, ", r.errore); }
}

funzione principale() -> intero {
    prova("42");
    prova("abc");
    prova("-5");
    ritorna 0;
}
```
```uscita
42: ok, 42
abc: errore, non e' un numero
-5: errore, eta' impossibile
```

`@testo.ce` e' un file della libreria standard (cartella `lib/`). Con `usa "@nome.ce";` lo importi
senza scrivere percorsi.

## 9. Memoria a mano, ma con le cinture

```ce
funzione principale() -> intero {
    variabile dati: [intero] = riserva(intero, 5);
    rimanda { rischio { libera(dati); } }
    per i: dimensione in 0..dati.lunghezza {
        dati[i] = (i * i) come intero;
    }
    stampa(dati[4]);
    ritorna 0;
}
```
```uscita
16
```

`riserva(tipo, quanti)` prende memoria (gia' azzerata). `libera` la restituisce, ma e' pericolosa
(il compilatore non puo' sapere se ne hai ancora una copia), quindi si scrive solo dentro `rischio`.
`rimanda` rimanda un'istruzione alla fine del blocco: cosi' la `libera` parte da sola, anche se
esci prima con `ritorna`.

## 10. Funzioni e tipi generici

Scrivi una funzione una volta, usala con qualsiasi tipo:

```ce
funzione massimo<T>(a: T, b: T) -> T {
    se a > b { ritorna a; }
    ritorna b;
}

struttura Coppia<A, B> {
    primo: A,
    secondo: B,
}

funzione principale() -> intero {
    stampa(massimo(3, 9));
    stampa(massimo(2.5, 1.5));
    variabile c: Coppia<intero, testo> = Coppia { primo: 7, secondo: "sette" };
    stampa(c.primo, " ", c.secondo);
    ritorna 0;
}
```
```uscita
9
2.5
7 sette
```

Il compilatore crea una versione vera della funzione per ogni tipo usato, quindi non costa niente
a runtime.

## 11. Un programma piu' vero: contare le parole

```ce
usa "@testo.ce";
usa "@mappa_testo.ce";

funzione principale() -> intero {
    costante frase: testo = "il gatto e il cane e il topo";
    variabile conta: MappaTesto<intero> = nuova_mappa_testo();
    variabile inizio: dimensione = 0;
    per i: dimensione in 0..(frase.lunghezza + 1) {
        se i == frase.lunghezza || frase[i] == 32 {
            costante parola: testo = frase[inizio..i];
            conta.inserisci_t(parola, conta.cerca_t(parola).valore_o(0) + 1);
            inizio = i + 1;
        }
    }
    stampa("il: ", conta.cerca_t("il").valore_o(0));
    stampa("e: ", conta.cerca_t("e").valore_o(0));
    stampa("gatto: ", conta.cerca_t("gatto").valore_o(0));
    stampa("elefante: ", conta.cerca_t("elefante").valore_o(0));
    conta.libera_mappa_testo();
    ritorna 0;
}
```
```uscita
il: 3
e: 2
gatto: 1
elefante: 0
```

## Dove andare adesso

- `README.md`: tutte le regole e i limiti noti.
- `lib/`: la libreria standard, scritta in Ce++ (si legge bene).
- Il repository `ce-cpu`: una piccola CPU emulata. Il repository `ce-chip8` (in arrivo): un emulatore
  CHIP-8 completo.
- `python3 ce.py formatta file.ce --scrivi` per sistemare i rientri.

Quando trovi un errore del compilatore o un messaggio poco chiaro, aprilo come "issue" su GitHub:
e' esattamente cosi' che il linguaggio migliora.

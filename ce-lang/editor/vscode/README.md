# Ce++ per VS Code

Colori, commenti, parentesi automatiche e rientri per i file `.ce`.

## Installare (senza pubblicare nulla)

Copia questa cartella dentro la cartella delle estensioni di VS Code e riavvia:

- Linux/Mac: `~/.vscode/extensions/ce-lang`
- Windows: `%USERPROFILE%\.vscode\extensions\ce-lang`

(In un Codespace: `cp -r ce-lang/editor/vscode ~/.vscode-remote/extensions/ce-lang` e ricarica la finestra.)

## Cosa fa e cosa no

Fa la colorazione e le parentesi. Non fa ancora controllo degli errori mentre scrivi:
per quello lancia `python3 ce.py emetti file.ce`. Per sistemare i rientri: `python3 ce.py formatta file.ce --scrivi`.

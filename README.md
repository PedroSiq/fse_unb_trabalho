# Trabalho 1 — Semáforo (FSE)

Python 3.9+. GPIO com **RPi.GPIO**.

## Instalação

```bash
cd /caminho/do/projeto
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

Na Pi: `python3 -c "import RPi.GPIO; print('OK')"` deve retornar OK.

## Execução

```bash
source .venv/bin/activate
python3 main.py distribuido --host 0.0.0.0 --port 8765 --modelo ambos
```

| Modo | Comando |
|------|---------|
| Ambos os modelos, só GPIO | `python3 main.py local --modelo ambos` |
| Só modelo 1 ou 2 | `python3 main.py local --modelo 1` ou `--modelo 2` |
| Pi: GPIO + TCP (aguarda clientes) | `python3 main.py distribuido --host 0.0.0.0 --port 8765 --modelo ambos` |

`Ctrl+C` para sair do programa.

Pinos BCM: `semaforo/pins.py`.

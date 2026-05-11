# Trabalho 1 — Entrega 1: Controle de Semáforo (FSE 2026/1)

Programa em **Python** para Raspberry Pi que controla, em **paralelo**, o **Modelo 1** (três LEDs no Cruzamento 1) e o **Modelo 2** (código de 3 bits no Cruzamento 2), com **dois botões de pedestre por modelo**, debounce e **mensagem imediata no terminal** a cada acionamento.

## Requisitos

- Raspberry Pi com GPIO acessível (testado com a pilha `gpiozero`).
- Python 3.9 ou superior.
- Ligações conforme as tabelas da especificação (BCM).

## Instalação

Na Raspberry Pi (recomenda-se ambiente virtual):

```bash
cd /caminho/para/trab1
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

No Cursor/VS Code, use o interpretador **`trab1/.venv/bin/python`** (o repositório inclui `.vscode/settings.json` para isso) para o analisador resolver `gpiozero`.

Instalação editável (opcional, usa `pyproject.toml`):

```bash
pip install -e .
```

## Execução

A partir da raiz do repositório (com o `venv` ativado):

```bash
# Ambos os modelos em paralelo (padrão)
python3 main.py

# Apenas Modelo 1 (3 LEDs: GPIO 17, 18, 23)
python3 main.py --modelo 1

# Apenas Modelo 2 (bits: GPIO 24, 8, 7)
python3 main.py --modelo 2
```

Encerramento: `Ctrl+C` (libera pinos GPIO).

## Estrutura do repositório

| Caminho | Descrição |
|--------|-----------|
| `main.py` | Entrada: threads, argumentos `--modelo`, sinais |
| `semaforo/pins.py` | Constantes BCM dos pinos |
| `semaforo/botoes.py` | `gpiozero.Button`, debounce + impressão imediata |
| `semaforo/model1.py` | Máquina de estados Verde → Amarelo → Vermelho |
| `semaforo/model2.py` | Ciclo S1→S2→S4→S5→S6→S4 com códigos 1,2,4,5,6 |
| `requirements.txt` | Dependência `gpiozero` |
| `pyproject.toml` | Metadados do pacote `semaforo` |

## Comportamento resumido

- **Modelo 1:** verde 10 s (mínimo 5 s antes do pedestre antecipar amarelo), amarelo 2 s, vermelho 10 s. Botões GPIO **1** e **12** (efeito só com semáforo **verde**; impressão sempre que o hardware acionar o pino).
- **Modelo 2:** sequência e tempos conforme tabelas (verde principal 10–20 s, verde cruzamento 5–10 s, amarelos e vermelho total 2 s). Botões GPIO **25** (via principal em verde) e **22** (via de cruzamento em verde).
- **Saída 3 bits:** bit 0 → GPIO 24, bit 1 → GPIO 8, bit 2 → GPIO 7; nível alto = bit 1.

## Observações de hardware

- Botões: sinal **normalmente baixo**, pulso **alto** (~200 ms). Use resistor de pull-down externo se o circuito exigir; o código usa `pull_up=False` no `gpiozero`.
- O GPIO **1** (Modelo 1) pode ter particularidades em algumas placas; confira o esquema do seu kit.

## Referências sugeridas pela disciplina

- [gpiozero](https://gpiozero.readthedocs.io/)
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/) (alternativa; este projeto usa `gpiozero`)

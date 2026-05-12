# Trabalho 1 — Controle de Semáforo (FSE 2026/1)

Programa em **Python** com arquitetura **servidor central** (interface de utilizador + TCP/IP) e **servidor distribuído** (GPIO: semáforos, botões de pedestre, sensores, buzzer), além do modo **local** só com GPIO.

## Arquitetura

```text
[ Interface de utilizador ]  ←→  [ Servidor central ]  ←TCP/IP→  [ Servidor distribuído ]
                                                                    ├ Buzzer
                                                                    └ GPIO
                                                                         ├ Sinais 1 e 3 (Modelo 1)
                                                                         ├ Sinais 2 e 4 (Modelo 2)
                                                                         ├ Botões pedestre
                                                                         └ Sensores (presença/passagem; velocidade/…)
```

Diagrama de referência: [`docs/arquitetura.png`](docs/arquitetura.png).

- **central** — consola no PC (ou na Pi); envia comandos (`ping`, `buzzer`, `status`) e mostra eventos JSON vindos do distribuído.
- **distribuido** — corre na **Raspberry Pi**; escuta TCP, corre as máquinas de semáforo, lê sensores e aciona o buzzer.
- **local** — sem rede; apenas os dois modelos de semáforo na mesma máquina (útil para testes só de GPIO).

Mensagens: **JSON uma linha por mensagem**, campo `"v": 1`.

## Requisitos

- Raspberry Pi com GPIO (`gpiozero`) no **distribuído**; no **central** basta Python e rede até à Pi.
- Python 3.9+.
- Pinos BCM conforme `semaforo/pins.py` (semáforos da entrega 1 + buzzer e sensores documentados lá).

## Raspberry Pi: backend GPIO e BCM 1 (pedestre M1)

Sem **`lgpio`** ou **`RPi.GPIO`** instalados **no mesmo venv** que corre o `python3`, o `gpiozero` cai no *NativeFactory* (sysfs). Em Pi OS recente o sysfs GPIO **nem existe** → aparecem `Falling back…` e depois `OSError: [Errno 22]` / `FileNotFoundError` em `/sys/class/gpio/...` **para qualquer BCM** (ex.: 27).

1. Na Pi (venv ativado):

   ```bash
   pip install -r requirements-pi.txt
   ```

   Em **Pi 5** basta normalmente o **`lgpio`**; se `RPi.GPIO` falhar a instalar, usa `pip install lgpio`.

2. **BCM 1** (tabela da entrega): muitas Pi reservam esse pino. O defeito no código é **27**; para forçar BCM 1:

   ```bash
   export FSE_PIN_M1_PED_PRINCIPAL=1
   ```

## Instalação

```bash
cd /caminho/do/projeto
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
# Na Raspberry Pi (modo local/distribuido), também:
pip install -r requirements-pi.txt
```

## Execução

Na **Raspberry Pi** (distribuído):

```bash
python3 main.py distribuido --host 0.0.0.0 --port 8765 --modelo ambos
```

No **PC** (central), com o IP da Pi:

```bash
python3 main.py central --host 192.168.1.10 --port 8765
```

Só **GPIO**, sem TCP (comportamento antigo da entrega 1):

```bash
python3 main.py local --modelo ambos
python3 main.py local --modelo 1
python3 main.py local --modelo 2
```

No modo **central**, na consola: `ping`, `buzzer 300`, `status`, `sair` (ver ajuda ao iniciar).

Encerramento: `Ctrl+C` nos modos local e distribuído; no central use `sair` ou `Ctrl+C`.

## Estrutura do repositório

| Caminho | Descrição |
|--------|-----------|
| `main.py` | Subcomandos `local`, `distribuido`, `central` |
| `semaforo/pins.py` | BCM: semáforos, pedestres, buzzer, sensores |
| `semaforo/protocolo.py` | Serialização JSON/TCP |
| `semaforo/botoes.py` | Pedestres + notificação opcional para o distribuído |
| `semaforo/sensores.py` | Entradas digitais → eventos |
| `semaforo/model1.py` / `model2.py` | Máquinas de estados dos semáforos |
| `semaforo/servidor_distribuido.py` | TCP + GPIO + buzzer |
| `semaforo/servidor_central.py` | Consola + cliente TCP |
| `requirements.txt` | `gpiozero` |
| `requirements-pi.txt` | `lgpio`, `RPi.GPIO` (só na Pi, no mesmo venv) |

## Comportamento resumido (semáforos)

- **Modelo 1:** verde 10 s (mín. 5 s para pedestre antecipar amarelo), amarelo 2 s, vermelho 10 s. LEDs GPIO **17, 18, 23**; botões: tabela **BCM 1** e **12** — se BCM 1 falhar na Pi, ver secção acima (`FSE_PIN_M1_PED_PRINCIPAL`, defeito **27** no código).
- **Modelo 2:** ciclo S1→S2→S4→S5→S6→S4; bits GPIO **24, 8, 7**; botões **25** e **22**.

## Referências

- [gpiozero](https://gpiozero.readthedocs.io/)
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/)

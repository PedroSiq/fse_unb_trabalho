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

O `main.py` escolhe o backend nesta ordem: **RPi.GPIO** → **lgpio** → **pigpio** (evita o *NativeFactory*/sysfs, que em Pi OS recente costuma falhar).

Sem nenhum destes no interpretador que corre o programa, aparece erro antes de abrir pinos.

### Caminho principal: **RPi.GPIO** (preferido)

No venv da Pi (muitas vezes há *wheel* ARM no [piwheels](https://www.piwheels.org/)):

```bash
source .venv/bin/activate
pip install "RPi.GPIO>=0.7.1" --extra-index-url https://www.piwheels.org/simple
python3 -c "import RPi.GPIO; print('RPi.GPIO OK')"
```

**Nota:** em **Raspberry Pi 5** / Python muito recente, o `RPi.GPIO` pode **não** instalar ou não suportar a placa — aí usa **lgpio** ou **pigpio** abaixo.

### Secundário: **lgpio** (Pi OS moderno, sem sysfs)

Com `sudo`: `sudo apt install python3-lgpio` e venv com `--system-site-packages`, ou `pip install lgpio` com piwheels / toolchain (ver secções antigas no histórico do README se precisares).

```bash
python3 -c "import lgpio; print('lgpio OK')"
```

### Terceiro: **pigpio** (precisa de `pigpiod` activo)

```bash
pip install pigpio --extra-index-url https://www.piwheels.org/simple
python3 -c "import pigpio; p=pigpio.pi(); print('pigpiod:', p.connected); p.stop()"
```

O `main.py` só usa **pigpio** se `RPi.GPIO` e `lgpio` não estiverem disponíveis **e** `p.connected` for `True`.

### Sem permissão `sudo`

1. Testa `import RPi.GPIO` e `import lgpio` com `/usr/bin/python3` — se algum funcionar, recria o venv com `python3 -m venv .venv --system-site-packages` e volta a instalar `requirements.txt` + `requirements-pi.txt`.
2. **piwheels:** `pip install RPi.GPIO ... --extra-index-url https://www.piwheels.org/simple`
3. Falhando tudo: **coordenação do FSE**.

### BCM 1 (tabela da entrega)

Muitas Pi reservam o BCM 1. O defeito no código é **27**; para forçar BCM 1: `export FSE_PIN_M1_PED_PRINCIPAL=1`.

## Instalação

```bash
cd /caminho/do/projeto
# No Mac/PC (só desenvolvimento): sem --system-site-packages
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Na **Raspberry Pi** para GPIO real, segue a secção **“Raspberry Pi: backend GPIO”** (com `sudo` **ou** o bloco **“Sem permissão sudo”**).

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
| `requirements-pi.txt` | `RPi.GPIO` (preferido), `pigpio`; `lgpio` opcional (README) |

## Comportamento resumido (semáforos)

- **Modelo 1:** verde 10 s (mín. 5 s para pedestre antecipar amarelo), amarelo 2 s, vermelho 10 s. LEDs GPIO **17, 18, 23**; botões: tabela **BCM 1** e **12** — se BCM 1 falhar na Pi, ver secção acima (`FSE_PIN_M1_PED_PRINCIPAL`, defeito **27** no código).
- **Modelo 2:** ciclo S1→S2→S4→S5→S6→S4; bits GPIO **24, 8, 7**; botões **25** e **22**.

## Referências

- [gpiozero](https://gpiozero.readthedocs.io/)
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/)

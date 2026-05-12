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

Sem **`lgpio`** ou **`RPi.GPIO`**, o `gpiozero` cai no *NativeFactory* (sysfs) e em Pi OS recente **quebra** (`OSError` / `FileNotFound` em `/sys/class/gpio/...`).

### Caminho recomendado (evita `Failed building wheel for lgpio`)

O pacote **`python3-lgpio`** vem pronto no `apt` — **não** depende de compilar com `pip`.

```bash
sudo apt update
sudo apt install -y python3-lgpio
cd ~/fse_unb_trabalho   # pasta do projeto
deactivate 2>/dev/null || true
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-pi.txt   # opcional: RPi.GPIO em Pi 3/4
python3 -c "import lgpio; print('lgpio OK')"
```

O truque é **`--system-site-packages`**: o venv passa a “ver” o `lgpio` instalado pelo sistema. O `main.py` escolhe automaticamente o backend `lgpio` quando `import lgpio` funciona.

### Sem permissão `sudo` (laboratório)

1. **Ver se o `lgpio` já vem na imagem** (sem instalar nada com apt):

   ```bash
   /usr/bin/python3 -c "import lgpio; print('OK')"
   ```

   Se imprimir `OK`, **não precisas de sudo**: apaga o venv e recria-o só com pacotes do sistema visíveis:

   ```bash
   cd ~/fse_unb_trabalho
   rm -rf .venv
   python3 -m venv .venv --system-site-packages
   source .venv/bin/activate
   pip install -r requirements.txt
   python3 -c "import lgpio; print('OK no venv')"
   ```

2. **Se o passo 1 falhar**, tenta **wheel pré-compilado** (muitas vezes evita compilar; não usa `sudo`):

   ```bash
   source .venv/bin/activate
   pip install "lgpio>=0.2.0.0" --extra-index-url https://www.piwheels.org/simple
   ```

3. Ainda assim a falhar: **coordenação do FSE** — pedir `python3-lgpio` na imagem da Pi ou permissão pontual para `apt install`.

### Alternativa sem `lgpio`: **pigpio**

O `gpiozero` pode usar o backend **`pigpio`**, que fala com o daemon **`pigpiod`** (muitas vezes já activo na imagem; **não** precisa de `sudo` para `pip`).

```bash
source .venv/bin/activate
pip install pigpio --extra-index-url https://www.piwheels.org/simple
python3 -c "import pigpio; p=pigpio.pi(); print('pigpiod OK:', p.connected); p.stop()"
```

Se `p.connected` for `False`, o daemon não está a correr — aí só **quem gere a Pi** pode arrancar o serviço (normalmente com `sudo`).

O `main.py` escolhe **pigpio** automaticamente se `lgpio` e `RPi.GPIO` não existirem mas o `pigpiod` estiver disponível.

### Se quiseres mesmo compilar o `lgpio` com pip

```bash
sudo apt install -y python3-dev swig liblgpio-dev build-essential
pip install lgpio
```

(Em muitas máquinas do laboratório isto falha ou demora — preferir o bloco com `apt` acima.)

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
| `requirements-pi.txt` | Opcional: `RPi.GPIO` (Pi 3/4); na Pi 5 use `apt install python3-lgpio` + venv `--system-site-packages` |

## Comportamento resumido (semáforos)

- **Modelo 1:** verde 10 s (mín. 5 s para pedestre antecipar amarelo), amarelo 2 s, vermelho 10 s. LEDs GPIO **17, 18, 23**; botões: tabela **BCM 1** e **12** — se BCM 1 falhar na Pi, ver secção acima (`FSE_PIN_M1_PED_PRINCIPAL`, defeito **27** no código).
- **Modelo 2:** ciclo S1→S2→S4→S5→S6→S4; bits GPIO **24, 8, 7**; botões **25** e **22**.

## Referências

- [gpiozero](https://gpiozero.readthedocs.io/)
- [RPi.GPIO](https://pypi.org/project/RPi.GPIO/)

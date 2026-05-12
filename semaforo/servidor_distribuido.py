"""
Servidor distribuído: executa na Raspberry Pi.

Integra semáforos, botões, sensores, buzzer e servidor TCP; recebe comandos do central
e envia eventos (pedestre, sensor, respostas a ping/status) em JSON por linha.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from queue import Empty, Full, Queue
from typing import Any, Callable, Optional

from semaforo import pins
from semaforo import rpi_io
from semaforo.protocolo import PROTO_VERSAO, iter_mensagens, serializar
from semaforo.sensores import SensorDigital


class ServidorDistribuido:
    """
    Coordena threads de semáforo, sensores, fila de saída TCP e aceitação de conexões.

    O buzzer executa em thread separada para não bloquear o tratamento de comandos.
    """

    def __init__(
        self,
        bind_host: str = "0.0.0.0",
        port: int = 8765,
        modelo: str = "ambos",
    ) -> None:
        self._bind_host = bind_host
        self._port = port
        self._modelo = modelo
        self._stop = threading.Event()
        self._fila_saida: Queue[dict[str, Any]] = Queue(maxsize=512)
        self._clientes: list[socket.socket] = []
        self._clientes_lock = threading.Lock()
        self._buf_por_sock: dict[socket.socket, bytearray] = {}

        rpi_io.init()
        self._buzzer_pin = pins.BUZZER
        rpi_io.setup_output_low(self._buzzer_pin)
        self._m1: Any = None
        self._m2: Any = None
        self._sensores: list[SensorDigital] = []
        self._workers: list[threading.Thread] = []
        self._sock_srv: Optional[socket.socket] = None

    # Fila de saída — enfileira eventos e replica aos clientes TCP conectados.

    def _enqueue(self, msg: dict[str, Any]) -> None:
        msg.setdefault("v", PROTO_VERSAO)
        msg.setdefault("no", "distribuido-1")
        try:
            self._fila_saida.put_nowait(msg)
        except Full:
            pass

    def _wrap_evt(self, modelo: Optional[int]) -> Callable[[dict[str, Any]], None]:
        def _fn(evt: dict[str, Any]) -> None:
            e = dict(evt)
            if modelo is not None:
                e["modelo_semaforo"] = modelo
            self._enqueue(e)

        return _fn

    # Buzzer — emite pulso de duração limitada (mínimo e máximo em milissegundos).

    def _beep(self, ms: int) -> None:
        ms = max(10, min(ms, 5000))
        try:
            rpi_io.write_output(self._buzzer_pin, True)
            time.sleep(ms / 1000.0)
        finally:
            rpi_io.write_output(self._buzzer_pin, False)

    # Rede TCP — envio assíncrono, leitura por cliente e ciclo de accept.

    def _loop_envio(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self._fila_saida.get(timeout=0.35)
            except Empty:
                continue
            data = serializar(msg)
            with self._clientes_lock:
                mortos: list[socket.socket] = []
                for cli in self._clientes:
                    try:
                        cli.sendall(data)
                    except OSError:
                        mortos.append(cli)
                for cli in mortos:
                    self._clientes.remove(cli)
                    self._buf_por_sock.pop(cli, None)
                    try:
                        cli.close()
                    except OSError:
                        pass

    # Comandos do central — interpreta ping, buzzer e status em JSON.

    def _processar_comando(self, obj: dict[str, Any], _origem: socket.socket) -> None:
        if not isinstance(obj, dict) or obj.get("v") != PROTO_VERSAO:
            return
        cmd = obj.get("cmd")
        if cmd == "ping":
            self._enqueue({"evt": "pong"})
        elif cmd == "buzzer":
            ms = int(obj.get("ms", 200))
            threading.Thread(target=self._beep, args=(ms,), daemon=True).start()
        elif cmd == "status":
            self._enqueue({"evt": "status", "msg": "distribuido ativo"})

    def _loop_cliente(self, conn: socket.socket) -> None:
        conn.settimeout(1.0)
        self._buf_por_sock[conn] = bytearray()
        try:
            while not self._stop.is_set():
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buf = self._buf_por_sock[conn]
                try:
                    for obj in iter_mensagens(buf, chunk):
                        self._processar_comando(obj, conn)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._enqueue({"evt": "erro", "msg": "json_invalido"})
        finally:
            with self._clientes_lock:
                if conn in self._clientes:
                    self._clientes.remove(conn)
                self._buf_por_sock.pop(conn, None)
            try:
                conn.close()
            except OSError:
                pass

    def _loop_accept(self) -> None:
        assert self._sock_srv is not None
        self._sock_srv.settimeout(1.0)
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock_srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            conn.setblocking(True)
            with self._clientes_lock:
                self._clientes.append(conn)
            self._enqueue({"evt": "hello", "msg": "conexao_estabelecida"})
            threading.Thread(
                target=self._loop_cliente,
                args=(conn,),
                name="ClienteTCP",
                daemon=True,
            ).start()

    # Sensores — instancia a partir de pins; eventos na mesma fila de saída.

    def _montar_sensores(self) -> None:
        n: Callable[[dict[str, Any]], None] = lambda e: self._enqueue(e)
        specs = [
            (
                pins.SENSOR_PRESENCA_PASSAGEM_1,
                "Presença/Passagem 1",
                "presenca_passagem",
                1,
            ),
            (
                pins.SENSOR_PRESENCA_PASSAGEM_2,
                "Presença/Passagem 2",
                "presenca_passagem",
                2,
            ),
            (
                pins.SENSOR_VELO_PRES_PASS_1,
                "Velocidade/Presença/Passagem 1",
                "velocidade_presenca_passagem",
                1,
            ),
            (
                pins.SENSOR_VELO_PRES_PASS_2,
                "Velocidade/Presença/Passagem 2",
                "velocidade_presenca_passagem",
                2,
            ),
        ]
        for pin, nome, cat, sid in specs:
            self._sensores.append(
                SensorDigital(pin, nome, cat, sid, notificar=n),
            )

    # Inicialização em execução — inicia modelos, sensores, thread de envio e socket em escuta.

    def run(self) -> None:
        from semaforo.model1 import Modelo1
        from semaforo.model2 import Modelo2

        if self._modelo in ("1", "ambos"):
            self._m1 = Modelo1(notificar=self._wrap_evt(1))
            self._workers.append(
                threading.Thread(
                    target=self._m1.run_forever,
                    args=(self._stop,),
                    name="Modelo1",
                    daemon=True,
                )
            )
        if self._modelo in ("2", "ambos"):
            self._m2 = Modelo2(notificar=self._wrap_evt(2))
            self._workers.append(
                threading.Thread(
                    target=self._m2.run_forever,
                    args=(self._stop,),
                    name="Modelo2",
                    daemon=True,
                )
            )
        for t in self._workers:
            t.start()

        self._montar_sensores()

        envio = threading.Thread(target=self._loop_envio, name="EnvioTCP", daemon=True)
        envio.start()

        self._sock_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock_srv.bind((self._bind_host, self._port))
        self._sock_srv.listen(4)
        accept_thr = threading.Thread(target=self._loop_accept, name="AcceptTCP", daemon=True)
        accept_thr.start()

    # Encerramento — sinaliza parada, aguarda threads, fecha sockets e libera GPIO.

    def close(self) -> None:
        self._stop.set()
        for t in self._workers:
            t.join(timeout=8.0)
        if self._sock_srv is not None:
            try:
                self._sock_srv.close()
            except OSError:
                pass
            self._sock_srv = None
        with self._clientes_lock:
            for c in list(self._clientes):
                try:
                    c.close()
                except OSError:
                    pass
            self._clientes.clear()
        self._buf_por_sock.clear()
        for s in self._sensores:
            try:
                s.close()
            except Exception:
                pass
        self._sensores.clear()
        if self._m1 is not None:
            try:
                self._m1.close()
            except Exception:
                pass
        if self._m2 is not None:
            try:
                self._m2.close()
            except Exception:
                pass
        try:
            rpi_io.write_output(self._buzzer_pin, False)
            rpi_io.cleanup_pin(self._buzzer_pin)
        except Exception:
            pass
        try:
            rpi_io.cleanup_all()
        except Exception:
            pass

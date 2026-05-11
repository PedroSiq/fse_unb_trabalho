"""
Servidor central: interface de utilizador (consola) + ligação TCP/IP ao distribuído.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
from typing import Optional

from semaforo.protocolo import PROTO_VERSAO, iter_mensagens, serializar


class ServidorCentral:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._stop = threading.Event()
        self._buf = bytearray()

    def _ajuda(self) -> None:
        sys.stdout.write(
            f"""
=== Servidor central (→ {self._host}:{self._port}) ===
  ping              — pergunta ao distribuído
  buzzer [ms]       — ex.: buzzer 250 (padrão 200 ms)
  status            — pedido genérico de estado
  sair              — termina
(v={PROTO_VERSAO} em todas as mensagens JSON)
"""
        )
        sys.stdout.flush()

    def _loop_leitura(self) -> None:
        assert self._sock is not None
        self._sock.settimeout(0.5)
        while not self._stop.is_set():
            try:
                chunk = self._sock.recv(8192)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                sys.stdout.write("[central] ligação fechada pelo distribuído.\n")
                sys.stdout.flush()
                self._stop.set()
                break
            try:
                for msg in iter_mensagens(self._buf, chunk):
                    sys.stdout.write(
                        "[dist] " + json.dumps(msg, ensure_ascii=False) + "\n"
                    )
                    sys.stdout.flush()
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                sys.stdout.write(f"[central] JSON inválido: {e}\n")
                sys.stdout.flush()

    def _enviar(self, obj: dict) -> None:
        assert self._sock is not None
        self._sock.sendall(serializar(obj))

    def run(self) -> None:
        self._sock = socket.create_connection((self._host, self._port), timeout=10.0)
        self._ajuda()
        t = threading.Thread(target=self._loop_leitura, name="LeituraTCP", daemon=True)
        t.start()

        while not self._stop.is_set():
            try:
                linha = input("[central] > ").strip()
            except EOFError:
                break
            if not linha:
                continue
            partes = linha.split()
            cmd = partes[0].lower()
            if cmd in ("sair", "quit", "exit"):
                self._stop.set()
                break
            if cmd in ("?", "ajuda", "help"):
                self._ajuda()
            elif cmd == "ping":
                self._enviar({"v": PROTO_VERSAO, "cmd": "ping"})
            elif cmd == "buzzer":
                ms = int(partes[1]) if len(partes) > 1 else 200
                self._enviar({"v": PROTO_VERSAO, "cmd": "buzzer", "ms": ms})
            elif cmd == "status":
                self._enviar({"v": PROTO_VERSAO, "cmd": "status"})
            else:
                sys.stdout.write("Comando desconhecido. Escreva ajuda.\n")
                sys.stdout.flush()

        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

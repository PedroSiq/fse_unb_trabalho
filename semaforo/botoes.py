"""Leitura de botões com debounce e impressão imediata (RPi.GPIO + polling)."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any, Callable, Optional

from semaforo.rpi_io import PolledInput


class BotaoPedestre:
    """
    Botão ativo em nível alto; pull-down interno; debounce por lockout em software.
    """

    def __init__(
        self,
        pin: int,
        nome: str,
        lockout_s: float = 0.25,
        on_press: Optional[Callable[[], None]] = None,
        notificar: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        self._pin = pin
        self._nome = nome
        self._on_press = on_press
        self._notificar = notificar
        self._lockout_s = lockout_s
        self._locked_until = 0.0
        self._lock = threading.Lock()
        self._poller = PolledInput(pin, self._handle_rising)

    def _handle_rising(self) -> None:
        with self._lock:
            t = time.monotonic()
            if t < self._locked_until:
                return
            self._locked_until = t + self._lockout_s

        msg = f"[BOTÃO] {self._nome} (GPIO) acionado\n"
        sys.stdout.write(msg)
        sys.stdout.flush()

        if self._on_press is not None:
            self._on_press()

        if self._notificar is not None:
            self._notificar(
                {
                    "evt": "pedestre",
                    "nome": self._nome,
                    "pin": self._pin,
                }
            )

    def close(self) -> None:
        self._poller.close()

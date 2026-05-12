"""Sensor digital: mesma lógica elétrica dos botões; evento opcional para o servidor distribuído."""

from __future__ import annotations

import sys
import threading
import time
from typing import Callable, Optional

from semaforo.rpi_io import PolledInput


# Sensor digital — leitura por PolledInput; categorização para logs e mensagens de rede.


class SensorDigital:
    """
    Pulso em nível alto; debounce análogo ao dos botões de pedestre.

    Opcionalmente encaminha dicionário de evento para callback (por exemplo enfileiramento TCP).
    """

    def __init__(
        self,
        pin: int,
        nome: str,
        categoria: str,
        sensor_id: int,
        lockout_s: float = 0.2,
        notificar: Optional[Callable[[dict], None]] = None,
    ) -> None:
        self._nome = nome
        self._categoria = categoria
        self._sensor_id = sensor_id
        self._notificar = notificar
        self._lockout_s = lockout_s
        self._locked_until = 0.0
        self._lock = threading.Lock()
        self._pin = pin
        self._poller = PolledInput(pin, self._on_rising)

    def _on_rising(self) -> None:
        with self._lock:
            t = time.monotonic()
            if t < self._locked_until:
                return
            self._locked_until = t + self._lockout_s

        sys.stdout.write(f"[SENSOR] {self._nome} (GPIO {self._pin})\n")
        sys.stdout.flush()

        if self._notificar is not None:
            self._notificar(
                {
                    "evt": "sensor",
                    "categoria": self._categoria,
                    "id": self._sensor_id,
                    "nome": self._nome,
                    "pin": self._pin,
                }
            )

    def close(self) -> None:
        self._poller.close()

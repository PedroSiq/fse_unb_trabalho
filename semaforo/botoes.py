"""Leitura de botões com debounce e impressão imediata no terminal."""

from __future__ import annotations

import sys
import threading
import time
from typing import Callable, Optional

from gpiozero import Button


class BotaoPedestre:
    """
    Botão ativo em nível alto; debounce via gpiozero + lockout curto
    para um único reconhecimento por pulso (~200 ms).
    """

    def __init__(
        self,
        pin: int,
        nome: str,
        debounce_s: float = 0.05,
        lockout_s: float = 0.25,
        on_press: Optional[Callable[[], None]] = None,
    ) -> None:
        self._nome = nome
        self._on_press = on_press
        self._lockout_s = lockout_s
        self._locked_until = 0.0
        self._lock = threading.Lock()

        self._btn = Button(
            pin,
            pull_up=False,
            bounce_time=debounce_s,
        )
        self._btn.when_pressed = self._handle_pressed

    def _handle_pressed(self) -> None:
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

    def close(self) -> None:
        self._btn.close()

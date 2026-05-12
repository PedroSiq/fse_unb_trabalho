"""
Acesso aos pinos via RPi.GPIO (modo BCM).

Entradas são lidas por consulta periódica em thread, em vez de interrupção por borda,
para melhor compatibilidade entre versões da Raspberry Pi e do Python em ambiente de laboratório.
"""

from __future__ import annotations

import threading
from typing import Callable

_lock = threading.Lock()
_initialized = False


# Configuração global — modo BCM, pinos como saída ou entrada com pull-down.


def init() -> None:
    global _initialized
    import RPi.GPIO as GPIO

    with _lock:
        if not _initialized:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            _initialized = True


def setup_output_low(pin: int) -> None:
    import RPi.GPIO as GPIO

    init()
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)


def setup_input_pull_down(pin: int) -> None:
    import RPi.GPIO as GPIO

    init()
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


def write_output(pin: int, high: bool) -> None:
    import RPi.GPIO as GPIO

    GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)


def read_input_high(pin: int) -> bool:
    import RPi.GPIO as GPIO

    return GPIO.input(pin) == GPIO.HIGH


def cleanup_pin(pin: int) -> None:
    import RPi.GPIO as GPIO

    try:
        GPIO.cleanup(pin)
    except Exception:
        pass


def cleanup_all() -> None:
    global _initialized
    import RPi.GPIO as GPIO

    with _lock:
        try:
            GPIO.cleanup()
        except Exception:
            pass
        _initialized = False


# Entrada digital — detecção de borda de subida por consulta periódica em thread em segundo plano.


class PolledInput:
    """
    Consulta o pino em intervalos regulares; em transição de baixo para alto, dispara o callback.

    Evita depender de add_event_detect do RPi.GPIO em cenários onde esse recurso falha.
    """

    def __init__(
        self,
        pin: int,
        on_rising: Callable[[], None],
        poll_interval_s: float = 0.002,
    ) -> None:
        self._pin = pin
        self._on_rising = on_rising
        self._poll = poll_interval_s
        self._stop = threading.Event()
        setup_input_pull_down(pin)
        self._thr = threading.Thread(
            target=self._loop,
            name=f"poll-in-{pin}",
            daemon=True,
        )
        self._thr.start()

    def _loop(self) -> None:
        prev = False
        while not self._stop.is_set():
            cur = read_input_high(self._pin)
            if cur and not prev:
                self._on_rising()
            prev = cur
            self._stop.wait(self._poll)

    def close(self) -> None:
        self._stop.set()
        self._thr.join(timeout=3.0)
        cleanup_pin(self._pin)

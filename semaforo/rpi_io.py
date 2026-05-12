"""GPIO com RPi.GPIO (BCM), sem gpiozero — evita add_event_detect / camadas extra."""

from __future__ import annotations

import threading
from typing import Callable

_lock = threading.Lock()
_initialized = False


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


class PolledInput:
    """
    Entrada digital com pull-down; deteta **flanco de subida** por *polling*
    (sem add_event_detect).
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

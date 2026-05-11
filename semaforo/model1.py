"""Modelo 1 — três LEDs independentes (Verde → Amarelo → Vermelho)."""

from __future__ import annotations

import threading
import time
from enum import Enum, auto
from typing import Any, Callable, Optional

from gpiozero import LED

from semaforo import pins


class _Fase(Enum):
    VERDE = auto()
    AMARELO = auto()
    VERMELHO = auto()


class Modelo1:
    """
    Ciclo: Verde (10 s) → Amarelo (2 s) → Vermelho (10 s) → …
    Verde mínimo para atendimento ao pedestre: 5 s.
    Dois botões (OR) solicitam travessia: após 5 s de verde antecipam amarelo;
    antes dos 5 s aguarda o mínimo e então amarelo.
    """

    T_VERDE_S = 10.0
    T_VERDE_MIN_PED_S = 5.0
    T_AMARELO_S = 2.0
    T_VERMELHO_S = 10.0

    def __init__(
        self,
        notificar: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        self._led_verde = LED(pins.M1_LED_VERDE, active_high=True, initial_value=False)
        self._led_amarelo = LED(pins.M1_LED_AMARELO, active_high=True, initial_value=False)
        self._led_vermelho = LED(pins.M1_LED_VERMELHO, active_high=True, initial_value=False)

        self._ped_lock = threading.Lock()
        self._ped_solicitado = False
        self._em_verde = False

        from semaforo.botoes import BotaoPedestre

        self._bot_princ = BotaoPedestre(
            pins.M1_BOTAO_PED_PRINCIPAL,
            "Modelo 1 — Pedestre Principal",
            on_press=self._marcar_ped,
            notificar=notificar,
        )
        self._bot_cruz = BotaoPedestre(
            pins.M1_BOTAO_PED_CRUZAMENTO,
            "Modelo 1 — Pedestre Cruzamento",
            on_press=self._marcar_ped,
            notificar=notificar,
        )

    def _marcar_ped(self) -> None:
        if not self._em_verde:
            return
        with self._ped_lock:
            self._ped_solicitado = True

    def _consumir_ped(self) -> bool:
        with self._ped_lock:
            if not self._ped_solicitado:
                return False
            self._ped_solicitado = False
            return True

    def _peek_ped(self) -> bool:
        with self._ped_lock:
            return self._ped_solicitado

    def _apagar_todos(self) -> None:
        self._led_verde.off()
        self._led_amarelo.off()
        self._led_vermelho.off()

    def _set_fase(self, fase: _Fase) -> None:
        self._apagar_todos()
        if fase is _Fase.VERDE:
            self._led_verde.on()
        elif fase is _Fase.AMARELO:
            self._led_amarelo.on()
        else:
            self._led_vermelho.on()

    def run_forever(self, stop: Optional[threading.Event] = None) -> None:
        fase = _Fase.VERMELHO
        while stop is None or not stop.is_set():
            if fase is _Fase.VERMELHO:
                self._set_fase(_Fase.VERMELHO)
                if self._aguardar(self.T_VERMELHO_S, stop):
                    return
                fase = _Fase.VERDE

            elif fase is _Fase.VERDE:
                self._set_fase(_Fase.VERDE)
                self._em_verde = True
                try:
                    t0 = time.monotonic()
                    while stop is None or not stop.is_set():
                        elapsed = time.monotonic() - t0
                        ped = self._peek_ped()

                        if elapsed >= self.T_VERDE_S:
                            self._consumir_ped()
                            break

                        if ped and elapsed >= self.T_VERDE_MIN_PED_S:
                            self._consumir_ped()
                            break

                        if ped and elapsed < self.T_VERDE_MIN_PED_S:
                            restante = self.T_VERDE_MIN_PED_S - elapsed
                            if self._aguardar(min(restante, 0.05), stop):
                                return
                            continue

                        if self._aguardar(min(self.T_VERDE_S - elapsed, 0.05), stop):
                            return
                finally:
                    self._em_verde = False

                if stop and stop.is_set():
                    return
                fase = _Fase.AMARELO

            elif fase is _Fase.AMARELO:
                self._set_fase(_Fase.AMARELO)
                if self._aguardar(self.T_AMARELO_S, stop):
                    return
                fase = _Fase.VERMELHO

    def _aguardar(self, segundos: float, stop: Optional[threading.Event] = None) -> bool:
        """Retorna True se interrompido por `stop`."""
        if segundos <= 0:
            return bool(stop and stop.is_set())
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            if stop and stop.is_set():
                return True
            time.sleep(min(0.05, fim - time.monotonic()))
        return False

    def close(self) -> None:
        self._bot_princ.close()
        self._bot_cruz.close()
        self._led_verde.close()
        self._led_amarelo.close()
        self._led_vermelho.close()

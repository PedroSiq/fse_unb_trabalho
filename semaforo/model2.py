"""Modelo 2 — cruzamento completo via código de 3 bits na GPIO."""

from __future__ import annotations

import threading
import time
from enum import Enum, auto
from typing import Optional

from gpiozero import OutputDevice

from semaforo import pins


class _Estado(Enum):
    """Sequência: S1 → S2 → S4 → S5 → S6 → S4 → S1 …"""

    S1_VERDE_VERMELHO = auto()  # código 1
    S2_AMARELO_VERMELHO = auto()  # código 2
    S4_VERMELHO_VERMELHO = auto()  # código 4
    S5_VERMELHO_VERDE = auto()  # código 5
    S6_VERMELHO_AMARELO = auto()  # código 6


# Códigos 3 bits (bit0 → GPIO24, bit1 → GPIO8, bit2 → GPIO7)
CODIGO = {
    _Estado.S1_VERDE_VERMELHO: 1,
    _Estado.S2_AMARELO_VERMELHO: 2,
    _Estado.S4_VERMELHO_VERMELHO: 4,
    _Estado.S5_VERMELHO_VERDE: 5,
    _Estado.S6_VERMELHO_AMARELO: 6,
}


class Modelo2:
    """
    Temporização (s): verde principal 10–20, verde cruzamento 5–10;
    amarelos e vermelho total: 2.
    Botão principal (GPIO 25): durante verde principal, após mínimo antecipa S2.
    Botão cruzamento (GPIO 22): durante verde cruzamento, após mínimo antecipa S6.
    """

    T_VERDE_PRINC_MIN = 10.0
    T_VERDE_PRINC_MAX = 20.0
    T_VERDE_CRUZ_MIN = 5.0
    T_VERDE_CRUZ_MAX = 10.0
    T_AMARELO = 2.0
    T_VERMELHO_TOTAL = 2.0

    def __init__(self) -> None:
        self._bit0 = OutputDevice(pins.M2_BIT0, initial_value=False)
        self._bit1 = OutputDevice(pins.M2_BIT1, initial_value=False)
        self._bit2 = OutputDevice(pins.M2_BIT2, initial_value=False)

        self._lock_ped_p = threading.Lock()
        self._lock_ped_c = threading.Lock()
        self._ped_principal = False
        self._ped_cruzamento = False
        self._aceita_ped_principal = False
        self._aceita_ped_cruzamento = False

        from semaforo.botoes import BotaoPedestre

        self._bot_princ = BotaoPedestre(
            pins.M2_BOTAO_PED_PRINCIPAL,
            "Modelo 2 — Pedestre Principal",
            on_press=self._marcar_ped_principal,
        )
        self._bot_cruz = BotaoPedestre(
            pins.M2_BOTAO_PED_CRUZAMENTO,
            "Modelo 2 — Pedestre Cruzamento",
            on_press=self._marcar_ped_cruzamento,
        )

    def _marcar_ped_principal(self) -> None:
        if not self._aceita_ped_principal:
            return
        with self._lock_ped_p:
            self._ped_principal = True

    def _marcar_ped_cruzamento(self) -> None:
        if not self._aceita_ped_cruzamento:
            return
        with self._lock_ped_c:
            self._ped_cruzamento = True

    def _peek_ped_principal(self) -> bool:
        with self._lock_ped_p:
            return self._ped_principal

    def _peek_ped_cruzamento(self) -> bool:
        with self._lock_ped_c:
            return self._ped_cruzamento

    def _consumir_ped_principal(self) -> bool:
        with self._lock_ped_p:
            if not self._ped_principal:
                return False
            self._ped_principal = False
            return True

    def _consumir_ped_cruzamento(self) -> bool:
        with self._lock_ped_c:
            if not self._ped_cruzamento:
                return False
            self._ped_cruzamento = False
            return True

    def _aplicar_codigo(self, codigo: int) -> None:
        self._bit0.value = bool(codigo & 1)
        self._bit1.value = bool((codigo >> 1) & 1)
        self._bit2.value = bool((codigo >> 2) & 1)

    def _mostrar_estado(self, st: _Estado) -> None:
        self._aplicar_codigo(CODIGO[st])

    @staticmethod
    def _sleep_slice(seg: float, stop: Optional[threading.Event]) -> bool:
        if seg <= 0:
            return bool(stop and stop.is_set())
        fim = time.monotonic() + seg
        while time.monotonic() < fim:
            if stop and stop.is_set():
                return True
            time.sleep(min(0.05, fim - time.monotonic()))
        return False

    def _aguardar_verde_principal(self, stop: Optional[threading.Event]) -> bool:
        self._mostrar_estado(_Estado.S1_VERDE_VERMELHO)
        self._aceita_ped_principal = True
        try:
            t0 = time.monotonic()
            while stop is None or not stop.is_set():
                elapsed = time.monotonic() - t0
                if elapsed >= self.T_VERDE_PRINC_MAX:
                    self._consumir_ped_principal()
                    return False
                if self._peek_ped_principal() and elapsed >= self.T_VERDE_PRINC_MIN:
                    self._consumir_ped_principal()
                    return False
                if self._sleep_slice(
                    min(0.05, self.T_VERDE_PRINC_MAX - elapsed),
                    stop,
                ):
                    return True
        finally:
            self._aceita_ped_principal = False
        return bool(stop and stop.is_set())

    def _aguardar_verde_cruzamento(self, stop: Optional[threading.Event]) -> bool:
        self._mostrar_estado(_Estado.S5_VERMELHO_VERDE)
        self._aceita_ped_cruzamento = True
        try:
            t0 = time.monotonic()
            while stop is None or not stop.is_set():
                elapsed = time.monotonic() - t0
                if elapsed >= self.T_VERDE_CRUZ_MAX:
                    self._consumir_ped_cruzamento()
                    return False
                if self._peek_ped_cruzamento() and elapsed >= self.T_VERDE_CRUZ_MIN:
                    self._consumir_ped_cruzamento()
                    return False
                if self._sleep_slice(
                    min(0.05, self.T_VERDE_CRUZ_MAX - elapsed),
                    stop,
                ):
                    return True
        finally:
            self._aceita_ped_cruzamento = False
        return bool(stop and stop.is_set())

    def run_forever(self, stop: Optional[threading.Event] = None) -> None:
        while stop is None or not stop.is_set():
            if self._aguardar_verde_principal(stop):
                return

            self._mostrar_estado(_Estado.S2_AMARELO_VERMELHO)
            if self._sleep_slice(self.T_AMARELO, stop):
                return

            self._mostrar_estado(_Estado.S4_VERMELHO_VERMELHO)
            if self._sleep_slice(self.T_VERMELHO_TOTAL, stop):
                return

            if self._aguardar_verde_cruzamento(stop):
                return

            self._mostrar_estado(_Estado.S6_VERMELHO_AMARELO)
            if self._sleep_slice(self.T_AMARELO, stop):
                return

            self._mostrar_estado(_Estado.S4_VERMELHO_VERMELHO)
            if self._sleep_slice(self.T_VERMELHO_TOTAL, stop):
                return

    def close(self) -> None:
        self._bot_princ.close()
        self._bot_cruz.close()
        self._bit0.close()
        self._bit1.close()
        self._bit2.close()

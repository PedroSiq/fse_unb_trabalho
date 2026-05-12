"""
Modelo 2: três saídas que codificam o estado (S1 a S6).

Tempos de verde entre mínimo e máximo; pedestre pode antecipar o amarelo após o mínimo em verde.
"""

from __future__ import annotations

import threading
import time
from enum import Enum, auto
from typing import Any, Callable, Optional

from semaforo import pins
from semaforo import rpi_io


# Estados do cruzamento — sequência conforme o enunciado (S1, S2, S4, S5, S6).


class _Estado(Enum):
    """Sequência: S1 → S2 → S4 → S5 → S6 → S4 → retorno ao ciclo inicial."""

    S1_VERDE_VERMELHO = auto()  # código 1
    S2_AMARELO_VERMELHO = auto()  # código 2
    S4_VERMELHO_VERMELHO = auto()  # código 4
    S5_VERMELHO_VERDE = auto()  # código 5
    S6_VERMELHO_AMARELO = auto()  # código 6


# Mapeamento estado–código — valor de 3 bits nas saídas GPIO (bit 0 = M2_BIT0).

CODIGO = {
    _Estado.S1_VERDE_VERMELHO: 1,
    _Estado.S2_AMARELO_VERMELHO: 2,
    _Estado.S4_VERMELHO_VERMELHO: 4,
    _Estado.S5_VERMELHO_VERDE: 5,
    _Estado.S6_VERMELHO_AMARELO: 6,
}


class Modelo2:
    """
    Cruzamento com duas vias; tempos de verde principal e de cruzamento entre mínimo e máximo.

    Cada botão de pedestre só é considerado na respectiva fase de verde; após o mínimo,
    o acionamento pode antecipar o amarelo daquele lado.
    """

    T_VERDE_PRINC_MIN = 10.0
    T_VERDE_PRINC_MAX = 20.0
    T_VERDE_CRUZ_MIN = 5.0
    T_VERDE_CRUZ_MAX = 10.0
    T_AMARELO = 2.0
    T_VERMELHO_TOTAL = 2.0

    # Construtor — saídas em nível baixo e botões com flags sincronizadas por lock.

    def __init__(
        self,
        notificar: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        rpi_io.init()
        self._b0 = pins.M2_BIT0
        self._b1 = pins.M2_BIT1
        self._b2 = pins.M2_BIT2
        for p in (self._b0, self._b1, self._b2):
            rpi_io.setup_output_low(p)

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
            notificar=notificar,
        )
        self._bot_cruz = BotaoPedestre(
            pins.M2_BOTAO_PED_CRUZAMENTO,
            "Modelo 2 — Pedestre Cruzamento",
            on_press=self._marcar_ped_cruzamento,
            notificar=notificar,
        )

    # Pedestres — cada botão só é aceito na fase de verde correspondente.

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

    # Saídas — escreve o código de 3 bits nas linhas GPIO do modelo 2.

    def _aplicar_codigo(self, codigo: int) -> None:
        rpi_io.write_output(self._b0, bool(codigo & 1))
        rpi_io.write_output(self._b1, bool((codigo >> 1) & 1))
        rpi_io.write_output(self._b2, bool((codigo >> 2) & 1))

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

    # Fases de verde prolongadas — espera em fatias curtas para permitir encerramento rápido.

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

    # Laço principal — percorre a sequência completa de estados do cruzamento.

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
        rpi_io.write_output(self._b0, False)
        rpi_io.write_output(self._b1, False)
        rpi_io.write_output(self._b2, False)
        for p in (self._b0, self._b1, self._b2):
            rpi_io.cleanup_pin(p)

#!/usr/bin/env python3
"""
Ponto de entrada: executa Modelo 1 e/ou Modelo 2 em paralelo na Raspberry Pi.
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from typing import Any, Optional


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Controle simultâneo dos semáforos Modelo 1 (3 LEDs) e Modelo 2 (3 bits).",
    )
    p.add_argument(
        "--modelo",
        choices=("1", "2", "ambos"),
        default="ambos",
        help="Qual modelo executar (padrão: ambos).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    stop = threading.Event()
    m1: Any = None
    m2: Any = None
    workers: list[threading.Thread] = []

    def handle_sig(_sig: int, _frame: Optional[object]) -> None:
        stop.set()
        sys.stderr.write("\nEncerrando…\n")

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        if args.modelo in ("1", "ambos"):
            from semaforo.model1 import Modelo1

            m1 = Modelo1()
            t = threading.Thread(
                target=m1.run_forever,
                args=(stop,),
                name="Modelo1",
                daemon=False,
            )
            t.start()
            workers.append(t)

        if args.modelo in ("2", "ambos"):
            from semaforo.model2 import Modelo2

            m2 = Modelo2()
            t = threading.Thread(
                target=m2.run_forever,
                args=(stop,),
                name="Modelo2",
                daemon=False,
            )
            t.start()
            workers.append(t)

        sys.stdout.write(
            "Semáforo em execução (Ctrl+C para sair). "
            f"Modo: {args.modelo}.\n"
        )
        sys.stdout.flush()

        while not stop.is_set():
            stop.wait(timeout=0.5)

        for t in workers:
            t.join(timeout=8.0)

    except KeyboardInterrupt:
        stop.set()
        for t in workers:
            t.join(timeout=8.0)
    finally:
        stop.set()
        for t in workers:
            t.join(timeout=1.0)
        if m1 is not None:
            try:
                m1.close()
            except Exception:
                pass
        if m2 is not None:
            try:
                m2.close()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

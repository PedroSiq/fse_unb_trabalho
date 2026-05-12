#!/usr/bin/env python3
"""
Entrada do sistema:
  local         — só GPIO (semáforos na Raspberry, sem rede)
  distribuido   — servidor distribuído: GPIO + TCP/IP (corre na Pi)
  central       — interface de utilizador + TCP/IP (corre no PC ou na Pi)
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
from typing import Any, Optional


def _configure_gpio_pin_factory() -> bool:
    """
    Evita o NativeFactory (sysfs), que em Pi OS recente não serve.

    Ordem: **RPi.GPIO** → **lgpio** → **pigpio** (daemon `pigpiod` activo).
    """
    if os.environ.get("GPIOZERO_PIN_FACTORY", "").strip():
        return True
    try:
        import RPi.GPIO  # noqa: F401

        os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio"
        return True
    except ImportError:
        pass
    try:
        import lgpio  # noqa: F401

        os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"
        return True
    except ImportError:
        pass
    try:
        import pigpio

        pi = pigpio.pi()
        if pi.connected:
            pi.stop()
            os.environ["GPIOZERO_PIN_FACTORY"] = "pigpio"
            return True
    except Exception:
        pass

    sys.stderr.write(
        "ERRO: nenhum backend GPIO utilizável (RPi.GPIO / lgpio / pigpio).\n"
        "  Tenta no venv: pip install RPi.GPIO\n"
        "  Ou: pip install pigpio (com pigpiod a correr)\n"
        "  Verifica pigpio: python3 -c \"import pigpio; p=pigpio.pi(); print(p.connected); p.stop()\"\n"
        "  Alternativa: README (lgpio via piwheels ou venv --system-site-packages).\n"
    )
    sys.stderr.flush()
    return False


def _run_local(args: argparse.Namespace) -> int:
    if not _configure_gpio_pin_factory():
        return 2
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
            "Modo local — semáforo (Ctrl+C). Modelo: %s.\n" % args.modelo
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


def _run_distribuido(args: argparse.Namespace) -> int:
    if not _configure_gpio_pin_factory():
        return 2
    from semaforo.servidor_distribuido import ServidorDistribuido

    sd = ServidorDistribuido(
        bind_host=args.host,
        port=args.port,
        modelo=args.modelo,
    )

    def handle_sig(_sig: int, _frame: Optional[object]) -> None:
        sys.stderr.write("\nEncerrando servidor distribuído…\n")
        sd.close()

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    sd.run()
    sys.stdout.write(
        "Servidor distribuído à escuta em %s:%s (modelo %s). Ctrl+C para sair.\n"
        % (args.host, args.port, args.modelo)
    )
    sys.stdout.flush()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        sd.close()
    return 0


def _run_central(args: argparse.Namespace) -> int:
    from semaforo.servidor_central import ServidorCentral

    sc = ServidorCentral(args.host, args.port)
    try:
        sc.run()
    except (ConnectionRefusedError, OSError) as e:
        sys.stderr.write(f"Sem ligação ao distribuído: {e}\n")
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Sistema de semáforos (local / central / distribuído).")
    sub = p.add_subparsers(dest="modo", required=True)

    p_loc = sub.add_parser("local", help="Apenas GPIO na máquina local (sem TCP).")
    p_loc.add_argument(
        "--modelo",
        choices=("1", "2", "ambos"),
        default="ambos",
        help="Modelo de semáforo a executar.",
    )

    p_dist = sub.add_parser(
        "distribuido",
        help="Servidor com GPIO + sensores + buzzer; aceita TCP do central.",
    )
    p_dist.add_argument(
        "--host",
        default="0.0.0.0",
        help="Endereço de escuta (padrão todas as interfaces).",
    )
    p_dist.add_argument("--port", type=int, default=8765, help="Porta TCP.")
    p_dist.add_argument(
        "--modelo",
        choices=("1", "2", "ambos"),
        default="ambos",
        help="Quais máquinas de semáforo carregar.",
    )

    p_cen = sub.add_parser(
        "central",
        help="Interface de utilizador na consola; liga ao distribuído por TCP.",
    )
    p_cen.add_argument(
        "--host",
        required=True,
        help="IP ou hostname do servidor distribuído (ex.: 192.168.1.10).",
    )
    p_cen.add_argument("--port", type=int, default=8765, help="Porta TCP do distribuído.")

    args = p.parse_args()

    if args.modo == "local":
        return _run_local(args)
    if args.modo == "distribuido":
        return _run_distribuido(args)
    if args.modo == "central":
        return _run_central(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

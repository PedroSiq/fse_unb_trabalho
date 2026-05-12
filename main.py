import argparse
import signal
import sys
import threading
import time
from typing import Any, Optional


# Verificação de ambiente — exige RPi.GPIO nos modos que acessam hardware na Raspberry Pi.


def _ensure_rpi_gpio() -> bool:
    """Verifica a importação de RPi.GPIO e inicializa o modo BCM dos pinos."""
    try:
        import RPi.GPIO  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "ERRO: módulo RPi.GPIO não encontrado. Na Pi: pip install RPi.GPIO\n"
        )
        sys.stderr.flush()
        return False
    from semaforo import rpi_io

    rpi_io.init()
    return True


# Modo local — executa os modelos de semáforo em threads e libera os pinos ao encerrar.


def _run_local(args: argparse.Namespace) -> int:
    if not _ensure_rpi_gpio():
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
        try:
            from semaforo import rpi_io

            rpi_io.cleanup_all()
        except Exception:
            pass

    return 0


# Modo distribuído — ciclo de vida do ServidorDistribuido (GPIO e rede na Raspberry Pi).


def _run_distribuido(args: argparse.Namespace) -> int:
    if not _ensure_rpi_gpio():
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


# Modo central — interface textual ligada ao host e à porta do distribuído.


def _run_central(args: argparse.Namespace) -> int:
    from semaforo.servidor_central import ServidorCentral

    sc = ServidorCentral(args.host, args.port)
    try:
        sc.run()
    except (ConnectionRefusedError, OSError) as e:
        sys.stderr.write(f"Sem conexão com o distribuído: {e}\n")
        return 1
    return 0


# Linha de comando — definição dos subcomandos local, distribuido e central.


def main() -> int:
    p = argparse.ArgumentParser(
        description="Semáforos (FSE): modos local, distribuido e central.",
    )
    sub = p.add_subparsers(dest="modo", required=True)

    p_loc = sub.add_parser("local", help="Apenas GPIO neste host, sem TCP.")
    p_loc.add_argument(
        "--modelo",
        choices=("1", "2", "ambos"),
        default="ambos",
        help="Qual modelo de semáforo executar: 1, 2 ou ambos.",
    )

    p_dist = sub.add_parser(
        "distribuido",
        help="Na Raspberry Pi: semáforos, sensores e buzzer; aguarda o modo central na rede.",
    )
    p_dist.add_argument(
        "--host",
        default="0.0.0.0",
        help="Endereço de escuta (0.0.0.0 = todas as interfaces de rede).",
    )
    p_dist.add_argument("--port", type=int, default=8765, help="Porta TCP do servidor.")
    p_dist.add_argument(
        "--modelo",
        choices=("1", "2", "ambos"),
        default="ambos",
        help="Modelos a carregar no distribuído: 1, 2 ou ambos.",
    )

    p_cen = sub.add_parser(
        "central",
        help="Interface em terminal: envia comandos JSON ao servidor distribuído.",
    )
    p_cen.add_argument(
        "--host",
        required=True,
        help="Host onde o modo distribuido está em execução (IP ou nome DNS).",
    )
    p_cen.add_argument("--port", type=int, default=8765, help="Porta TCP (igual à do distribuido).")

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


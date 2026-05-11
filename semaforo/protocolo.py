"""Mensagens JSON por linha (TCP) entre servidor central e distribuído."""

from __future__ import annotations

import json
from typing import Any, Iterator

PROTO_VERSAO = 1


def serializar(msg: dict[str, Any]) -> bytes:
    m = dict(msg)
    m.setdefault("v", PROTO_VERSAO)
    return (json.dumps(m, ensure_ascii=False) + "\n").encode("utf-8")


def iter_mensagens(buf: bytearray, chunk: bytes) -> Iterator[dict[str, Any]]:
    buf.extend(chunk)
    while True:
        i = buf.find(b"\n")
        if i < 0:
            break
        linha = bytes(buf[:i])
        del buf[: i + 1]
        linha = linha.strip()
        if not linha:
            continue
        yield json.loads(linha.decode("utf-8"))



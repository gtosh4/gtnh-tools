"""Minimal named-binary-tag codec (Minecraft 1.7.10 flavour, big-endian, gzip on disk).

Values carry their tag type explicitly so round-trips are lossless:
Byte/Short/Int/Long/Float/Double wrap numbers, ``str`` is TAG_String,
``bytes``/``bytearray`` is TAG_Byte_Array, ``IntArray`` is TAG_Int_Array,
``List`` is TAG_List and ``dict`` is TAG_Compound (insertion order kept).
"""
from __future__ import annotations

import gzip
import io
import struct
from dataclasses import dataclass, field
from typing import Any

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY = range(12)


@dataclass(frozen=True)
class Byte:
    v: int


@dataclass(frozen=True)
class Short:
    v: int


@dataclass(frozen=True)
class Int:
    v: int


@dataclass(frozen=True)
class Long:
    v: int


@dataclass(frozen=True)
class Float:
    v: float


@dataclass(frozen=True)
class Double:
    v: float


@dataclass(frozen=True)
class IntArray:
    v: tuple[int, ...]


@dataclass
class List:
    """TAG_List; ``kind`` is the element tag id (COMPOUND, INT, ...)."""

    kind: int
    items: list = field(default_factory=list)


_SCALAR = {Byte: (BYTE, ">b"), Short: (SHORT, ">h"), Int: (INT, ">i"), Long: (LONG, ">q"),
           Float: (FLOAT, ">f"), Double: (DOUBLE, ">d")}


def tag_id(value: Any) -> int:
    t = type(value)
    if t in _SCALAR:
        return _SCALAR[t][0]
    if t is str:
        return STRING
    if t in (bytes, bytearray):
        return BYTE_ARRAY
    if t is IntArray:
        return INT_ARRAY
    if t is List:
        return LIST
    if t is dict:
        return COMPOUND
    raise TypeError(f"not an NBT value: {value!r} ({t.__name__}); wrap numbers in Byte/Short/Int/...")


def _write_payload(out: io.BytesIO, value: Any) -> None:
    t = type(value)
    if t in _SCALAR:
        out.write(struct.pack(_SCALAR[t][1], value.v))
    elif t is str:
        raw = value.encode("utf-8")
        out.write(struct.pack(">H", len(raw)))
        out.write(raw)
    elif t in (bytes, bytearray):
        out.write(struct.pack(">i", len(value)))
        out.write(value)
    elif t is IntArray:
        out.write(struct.pack(f">i{len(value.v)}i", len(value.v), *value.v))
    elif t is List:
        kind = value.kind if value.items else (value.kind or END)
        out.write(struct.pack(">bi", kind, len(value.items)))
        for item in value.items:
            if tag_id(item) != kind:
                raise TypeError(f"list of tag {kind} holds {item!r}")
            _write_payload(out, item)
    elif t is dict:
        for name, item in value.items():
            _write_named(out, name, item)
        out.write(b"\x00")
    else:
        raise TypeError(f"not an NBT value: {value!r}")


def _write_named(out: io.BytesIO, name: str, value: Any) -> None:
    raw = name.encode("utf-8")
    out.write(struct.pack(">bH", tag_id(value), len(raw)))
    out.write(raw)
    _write_payload(out, value)


def dumps(root: dict, name: str = "") -> bytes:
    out = io.BytesIO()
    _write_named(out, name, root)
    return out.getvalue()


def save(path, root: dict, name: str = "") -> None:
    with gzip.open(path, "wb") as fh:
        fh.write(dumps(root, name))


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, fmt: str):
        size = struct.calcsize(fmt)
        vals = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return vals

    def string(self) -> str:
        (n,) = self.take(">H")
        raw = self.data[self.pos:self.pos + n]
        self.pos += n
        return raw.decode("utf-8", errors="surrogateescape")

    def payload(self, kind: int):
        if kind == BYTE:
            return Byte(self.take(">b")[0])
        if kind == SHORT:
            return Short(self.take(">h")[0])
        if kind == INT:
            return Int(self.take(">i")[0])
        if kind == LONG:
            return Long(self.take(">q")[0])
        if kind == FLOAT:
            return Float(self.take(">f")[0])
        if kind == DOUBLE:
            return Double(self.take(">d")[0])
        if kind == BYTE_ARRAY:
            (n,) = self.take(">i")
            raw = self.data[self.pos:self.pos + n]
            self.pos += n
            return bytes(raw)
        if kind == STRING:
            return self.string()
        if kind == LIST:
            elem, n = self.take(">bi")
            return List(elem, [self.payload(elem) for _ in range(n)])
        if kind == COMPOUND:
            out = {}
            while True:
                (child,) = self.take(">b")
                if child == END:
                    return out
                key = self.string()  # read before the payload: `out[k()] = v()` evaluates v first
                out[key] = self.payload(child)
        if kind == INT_ARRAY:
            (n,) = self.take(">i")
            return IntArray(self.take(f">{n}i"))
        raise ValueError(f"bad tag id {kind} at {self.pos}")


def loads(data: bytes) -> tuple[str, dict]:
    """Parse one named root tag; returns (root name, compound)."""
    r = _Reader(data)
    (kind,) = r.take(">b")
    if kind != COMPOUND:
        raise ValueError("root tag is not a compound")
    name = r.string()
    return name, r.payload(COMPOUND)


def load(path) -> tuple[str, dict]:
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return loads(raw)


def plain(value: Any) -> Any:
    """Strip tag wrappers (for printing/inspection)."""
    t = type(value)
    if t in _SCALAR:
        return value.v
    if t is IntArray:
        return list(value.v)
    if t is List:
        return [plain(v) for v in value.items]
    if t is dict:
        return {k: plain(v) for k, v in value.items()}
    return value

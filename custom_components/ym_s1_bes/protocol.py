"""YM-S1-BES BLE protocol codec."""

from __future__ import annotations

from dataclasses import dataclass

from .const import BLE_HEAD

READ_PAYLOAD = bytes.fromhex("e1 e9 e1")
COMMAND_XOR = 0xE9

CLEAR_PAYLOADS: dict[str, bytes] = {
    "energy": bytes.fromhex("ee eb e8 17 e1"),
    "time": bytes.fromhex("ee eb eb 14 e1"),
    "amount": bytes.fromhex("ee eb ea 15 e1"),
    "all": bytes.fromhex("ee eb e9 16 e1"),
}


@dataclass(frozen=True)
class MeterReading:
    """Decoded meter reading."""

    total_kwh: float
    total_time_minutes: int
    power_w: float
    voltage_v: float
    current_a: float
    power_factor: float
    power_upper_limit_w: int
    power_lower_limit_w: int
    unit_price: float
    amount: float
    valid_power_w: int
    firmware: int


@dataclass(frozen=True)
class ClearAck:
    """Decoded clear command acknowledgement."""

    total_kwh: float
    total_time_minutes: int
    amount: float
    firmware: int


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to AA:BB:CC:DD:EE:FF."""
    value = mac.replace(":", "").replace("-", "").strip().upper()
    if len(value) != 12:
        raise ValueError("MAC must contain 12 hex digits")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("MAC contains non-hex characters") from exc
    return ":".join(value[i : i + 2] for i in range(0, 12, 2))


def mac_to_advertised_name(mac: str) -> str:
    """Build the YUNM advertised name from a normal MAC address."""
    parts = normalize_mac(mac).split(":")
    return BLE_HEAD + "".join(reversed(parts))


def advertised_name_to_mac(name: str | None) -> str | None:
    """Decode a YUNM advertised name into a normal MAC address."""
    if not name:
        return None
    value = name.strip().upper()
    if len(value) != 16 or not value.startswith(BLE_HEAD):
        return None
    body = value[len(BLE_HEAD) :]
    try:
        int(body, 16)
    except ValueError:
        return None
    reversed_parts = [body[i : i + 2] for i in range(0, 12, 2)]
    return ":".join(reversed(reversed_parts))


class YmS1BesProtocol:
    """Codec for the YM-S1-BES mode1 long-frame protocol."""

    def __init__(self, mac: str) -> None:
        self.mac = normalize_mac(mac)
        self.mac_bytes = bytes.fromhex(self.mac.replace(":", ""))
        self.xor_key = sum(self.mac_bytes) & 0xFF
        self.crc_init = (self.mac_bytes[5] + self.mac_bytes[4] + 10) & 0xFFFF
        self.crc_poly = (((self.mac_bytes[5] + 11) << 8) | self.mac_bytes[4]) & 0xFFFF

    def crc(self, payload: bytes) -> int:
        """Calculate the device CRC for a payload."""
        crc = self.crc_init
        for byte in payload:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ self.crc_poly
                else:
                    crc >>= 1
                crc &= 0xFFFF
        return crc

    def build_frame(self, payload: bytes) -> bytes:
        """Build an EC ED mode1 long frame."""
        crc = self.crc(payload)
        frame = bytearray([0xEC, 0xED, (len(payload) >> 8) & 0xFF, len(payload) & 0xFF])
        frame.extend(payload)
        frame.extend([(crc >> 8) & 0xFF, crc & 0xFF])
        return bytes(byte ^ self.xor_key for byte in frame)

    def parse_frame(self, raw: bytes) -> tuple[bytes | None, int]:
        """Parse bytes from the notify stream.

        Returns a tuple of `(payload, consumed_bytes)`. Payload is `None` when
        more bytes are required.
        """
        if len(raw) < 6:
            return None, 0

        decoded = bytes(byte ^ self.xor_key for byte in raw)
        if decoded[:2] != b"\xec\xed":
            raise ValueError(f"unexpected frame header: {decoded[:2].hex()}")

        length = _u16be(decoded, 2)
        frame_length = length + 6
        if len(decoded) < frame_length:
            return None, 0

        payload = decoded[4 : 4 + length]
        got_crc = _u16be(decoded, 4 + length)
        expected_crc = self.crc(payload)
        if got_crc != expected_crc:
            raise ValueError(f"CRC mismatch: got={got_crc:04x} expected={expected_crc:04x}")

        return payload, frame_length


def decode_meter_payload(payload: bytes) -> MeterReading:
    """Decode a 0x08 meter payload."""
    decoded = _decode_semantic(payload)
    if len(decoded) < 32 or decoded[0] != 0x08:
        raise ValueError("not a meter reading payload")

    return MeterReading(
        total_kwh=_u32be(decoded, 3) / 100,
        total_time_minutes=_u32be(decoded, 7),
        power_w=_u16be(decoded, 11) / 10,
        voltage_v=_u16be(decoded, 13) / 10,
        current_a=_u16be(decoded, 15) / 1000,
        power_factor=decoded[17] / 100,
        power_upper_limit_w=_u16be(decoded, 18),
        power_lower_limit_w=_u16be(decoded, 20),
        unit_price=_u16be(decoded, 22) / 100,
        amount=_u32be(decoded, 24) / 100,
        valid_power_w=_u16be(decoded, 28),
        firmware=decoded[30],
    )


def decode_clear_ack(payload: bytes) -> ClearAck:
    """Decode a 0x07 clear acknowledgement."""
    decoded = _decode_semantic(payload)
    if len(decoded) < 16 or decoded[0] != 0x07:
        raise ValueError("not a clear acknowledgement payload")

    amount_raw = (decoded[11] << 16) | (decoded[12] << 8) | decoded[13]
    return ClearAck(
        total_kwh=_u32be(decoded, 3) / 100,
        total_time_minutes=_u32be(decoded, 7),
        amount=amount_raw / 100,
        firmware=decoded[14],
    )


def decode_set_config_ack(payload: bytes) -> MeterReading:
    """Decode a 0x2D set-config acknowledgement."""
    decoded = _decode_semantic(payload)
    if len(decoded) < 32 or decoded[0] != 0x2D:
        raise ValueError("not a set-config acknowledgement payload")

    return MeterReading(
        total_kwh=_u32be(decoded, 3) / 100,
        total_time_minutes=_u32be(decoded, 7),
        power_w=_u16be(decoded, 11) / 10,
        voltage_v=_u16be(decoded, 13) / 10,
        current_a=_u16be(decoded, 15) / 1000,
        power_factor=decoded[17] / 100,
        power_upper_limit_w=_u16be(decoded, 18),
        power_lower_limit_w=_u16be(decoded, 20),
        unit_price=_u16be(decoded, 22) / 100,
        amount=_u32be(decoded, 24) / 100,
        valid_power_w=_u16be(decoded, 28),
        firmware=decoded[30],
    )


def build_set_config_payload(unit_price: float, valid_power_w: int) -> bytes:
    """Build the 0x2D payload for unit price and timing power."""
    price_cents = round(unit_price * 100)
    if not 0 <= price_cents <= 999:
        raise ValueError("unit price must be between 0 and 9.99")
    if not 0 <= valid_power_w <= 999:
        raise ValueError("valid power must be between 0 and 999")

    logical = bytearray(
        [
            0x2D,
            0x04,
            (valid_power_w >> 8) & 0xFF,
            valid_power_w & 0xFF,
            (price_cents >> 8) & 0xFF,
            price_cents & 0xFF,
        ]
    )
    logical.append(sum(logical) & 0xFF)
    return bytes(byte ^ COMMAND_XOR for byte in logical)


def _decode_semantic(payload: bytes) -> bytes:
    return bytes(byte ^ 0xB2 for byte in payload)


def _u16be(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def _u32be(data: bytes, offset: int) -> int:
    return (
        (data[offset] << 24)
        | (data[offset + 1] << 16)
        | (data[offset + 2] << 8)
        | data[offset + 3]
    )

import asyncio
import base64
import re
import uuid
import zlib
import aiohttp
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger import logger

DEFAULT_IMAGE = "assets/unknown_server.png"

# Packet encoding/decoding

def compress_packet(data: bytes, threshold: int) -> bytes:
    if len(data) >= threshold:
        compressed_data = zlib.compress(data)
        uncompressed_length = encode_varint(len(data))
        return encode_varint(len(uncompressed_length) + len(compressed_data)) + uncompressed_length + compressed_data
    else:
        uncompressed_length = encode_varint(0)
        return encode_varint(len(uncompressed_length) + len(data)) + uncompressed_length + data

async def read_compressed_packet(reader, threshold: int):
    packet_length = await read_varint(reader)
    data = await reader.readexactly(packet_length)
    data_reader = asyncio.StreamReader()
    data_reader.feed_data(data)
    data_reader.feed_eof()

    uncompressed_length = await read_varint(data_reader)
    if uncompressed_length == 0:
        return data_reader
    else:
        compressed_data = await data_reader.read()
        decompressed = zlib.decompress(compressed_data)
        new_reader = asyncio.StreamReader()
        new_reader.feed_data(decompressed)
        new_reader.feed_eof()
        return new_reader

def encode_varint(value):
    if not isinstance(value, int):
        logger.error(f"Function encode_varint(value) expects an integer, but got {type(value).__name__}: {value}", "Packet Encoder")
        return
    buffer = bytearray()
    while True:
        temp = value & 0b01111111
        value >>= 7
        if value != 0:
            temp |= 0b10000000
        logger.debug(f"Function: encode_varint: buffer type = {type(buffer)}, temp = {temp}", "Packet Encoder")
        buffer.append(temp)
        if value == 0:
            break
    return bytes(buffer)

def encode_string(string):
    string_bytes = string.encode('utf-8')
    return encode_varint(len(string_bytes)) + string_bytes

def encode_uuid(uuid_str: str):
    return uuid.UUID(uuid_str).bytes

async def read_varint(reader):
    value = 0
    shift = 0
    while True:
        byte = await reader.readexactly(1)
        byte_val = byte[0]
        value |= (byte_val & 0x7F) << shift
        if not (byte_val & 0x80):
            break
        shift += 7
    return value

async def read_string(reader):
    length = await read_varint(reader)
    string_bytes = await reader.readexactly(length)
    return string_bytes.decode('utf-8')

# Mojang API

async def get_uuid(username: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{username}") as response:
            json_data = await response.json()
            if response.status == 200:
                return json_data.get("id")
            elif response.status == 404:
                return str(uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{username}"))
            else:
                logger.warning(f"[{username}] get_uuid(): No vaild response code: {response.status} Response: {json_data}", "MojangAPI")
            return None

# Minecraft formatting

FORMAT_CODES = {
    "black": "§0",
    "dark_blue": "§1",
    "dark_green": "§2",
    "dark_aqua": "§3",
    "dark_red": "§4",
    "dark_purple": "§5",
    "gold": "§6",
    "gray": "§7",
    "dark_gray": "§8",
    "blue": "§9",
    "green": "§a",
    "aqua": "§b",
    "red": "§c",
    "light_purple": "§d",
    "yellow": "§e",
    "white": "§f"
}
STYLE_CODES = {
    "obfuscated": "§k",
    "bold": "§l",
    "strikethrough": "§m",
    "underlined": "§n",
    "italic": "§o",
    "reset": "§r"
}

def parse_hex_color(hex_color):
    hex_color = hex_color.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", hex_color):
        return ""
    return "§x" + "".join(f"§{c}" for c in hex_color.lower())

def parse_component(component):
    if isinstance(component, str):
        return component
    text: str = ""
    color = component.get("color")
    if color:
        if color.startswith("#"):
            text += parse_hex_color(color)
        elif color in FORMAT_CODES:
            text += FORMAT_CODES[color]
    for key, code in STYLE_CODES.items():
        if component.get(key):
            text += code
    text += component.get("text", "")
    for extra in component.get("extra", []):
        text += parse_component(extra)
    return text

def recompile_color_codes(text: str):
    def repl(match):
        hexcode = match.group(1)
        extra_code = match.group(2) or ''
        rest = match.group(3) or ''
        color = "§x" + ''.join(f"§{c}" for c in hexcode)
        if extra_code:
            color += f"§{extra_code}"
        return color + rest
    pattern = re.compile(r"x([0-9a-fA-F]{6})([lomnkr])?([^x]*)")
    result = ""
    i = 0
    while i < len(text):
        m = pattern.match(text, i)
        if m:
            result += repl(m)
            i = m.end()
        else:
            result += text[i]
            i += 1
    return result

def strip_mc_formatting(text: str) -> str:
    if text is None:
        return None
    text = re.sub(r'§x(§[0-9a-fA-F]){6}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'§[0-9a-fklmnor]', '', text, flags=re.IGNORECASE)
    return text

# Image converter

def get_base64_from_image(filepath: str) -> str:
    with open(filepath, "rb") as f:
        image_data = f.read()
    base64_data = base64.b64encode(image_data).decode("ascii")
    return base64_data
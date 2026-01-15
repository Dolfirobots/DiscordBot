import argparse
import json
import asyncio
import socket
import struct
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger import logger
from minecraft.utils import get_uuid, recompile_color_codes, strip_mc_formatting
from minecraft.versions import get_protocol_version

PREFIX = "Server Query"

# Helpers

def safe_decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin1")

def parse_plugins(plugin_str):
    if not plugin_str or ':' not in plugin_str:
        return []
    plugin_part = plugin_str.split(":", 1)[1]
    raw_plugins = [p.strip() for p in plugin_part.split(";") if p.strip()]
    parsed = []
    for entry in raw_plugins:
        parts = entry.rsplit(" ", 1)
        if len(parts) == 2:
            name, version = parts
            parsed.append(f"{name}:{version}")
        else:
            parsed.append(entry) 
    return parsed
    
# Query

async def query_supported(ip: str, port: int = 25565, timeout: int = 1.2):
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    session_id = b'\x01\x02\x03\x04'
    challenge_request = b'\xFE\xFD\x09' + session_id
    try:
        await loop.sock_sendto(sock, challenge_request, (ip, port))
        try:
            data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 512), timeout)
        except asyncio.TimeoutError:
            return False
        if not data or data[0] != 0x09:
            return False
        return True
    except Exception as e:
        return False
    finally:
        sock.close()

async def get_query(ip: str, port: int = 25565, timeout: int = 3):
    if not await query_supported(ip=ip, port=port, timeout=timeout):
        return {}

    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    session_id = b'\x01\x02\x03\x04'

    try:
        await loop.sock_sendto(sock, b'\xFE\xFD\x09' + session_id, (ip, port))
        try:
            data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 2048), timeout)
        except asyncio.TimeoutError:
            logger.error("Timeout on challenge", PREFIX)
            return None
        if data[0] != 0x09:
            logger.error("Unvaild challenge answer", PREFIX)
            return None
        challenge_token = int(data[5:data.find(b'\x00', 5)].decode('ascii'))
        challenge_token_bytes = struct.pack('>i', challenge_token)

        await loop.sock_sendto(sock, b'\xFE\xFD\x00' + session_id + challenge_token_bytes + b'\x00\x00\x00\x00', (ip, port))
        try:
            data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), timeout)
        except asyncio.TimeoutError:
            logger.warning("Timeout on status query", PREFIX)
            return None
        if data[0] != 0x00:
            logger.error("Unvaild status answer", PREFIX)
            return None

        payload = data[5:]
        sections = payload.split(b"\x00\x00\x01player_\x00\x00")
        info = {}
        if sections:
            parts = sections[0].split(b'\x00')
            for i in range(0, len(parts) - 1, 2):
                key = safe_decode(parts[i])
                value = safe_decode(parts[i + 1])
                info[key] = value

        players = []
        if len(sections) == 2:
            players = [safe_decode(p) for p in sections[1].split(b'\x00') if p]
        players = [{"name": name, "id": uuid} for name, uuid in zip(players, await asyncio.gather(*(get_uuid(n) for n in players)))]

        if "plugins" in info:
            software = info["plugins"].split(":", 1)[0].replace("on ", "")
            plugins = parse_plugins(info["plugins"])
        else:
            software = None
            plugins = None
        
        return {
            "motd": recompile_color_codes(info.get("hostname", "")),
            "plain": strip_mc_formatting(recompile_color_codes(info.get("hostname"))),
            "software": software,

            "version_name": info.get("version", None),
            "version_protocol": await get_protocol_version(info.get("version", None)), # TODO

            "query_supported": True,
            "query_players": players,
            "query_default_world": info["map"],
            "query_plugins": plugins,
            "query_gametype": info.get("query_gametype", "SMP"),
            "query_game_id": info.get("game_id", "MINECRAFT"),
            
            "players_max": info.get("maxplayers", 0),
            "players_online": info.get("sumplayers", 0)
        }
    except Exception as e:
        logger.error(f"[{ip}:{port}] {e}", PREFIX)
        return {}
    finally:
        sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", help="Your Minecraft server IP.")
    parser.add_argument("--port", help="Your Minecraft server Port. Default: 25565")
    args = parser.parse_args()
    if args.ip:
        port = 25565
        if args.port:
            try:
                port = int(args.port)
                if not (1 <= port <= 65535):
                    raise ValueError
            except ValueError:
                logger.error("Invaild Port! Must be an integer between 1 and 65535!", PREFIX)
        result = asyncio.run(get_query(args.ip, port))
        logger.info("Result: " + json.dumps(result, ensure_ascii=False), PREFIX)
    else:
        logger.warning("This is module part of Server Seeker.", PREFIX)
        logger.warning(f"You can only use it in code or > python {__file__} --ip IP --port PORT", PREFIX)
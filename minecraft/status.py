import asyncio
import json
import time
import zlib
import socket
import argparse
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger import logger
from minecraft.utils import encode_varint, encode_string, read_varint, parse_component, get_base64_from_image, strip_mc_formatting, DEFAULT_IMAGE

PREFIX = "Server Status"

async def get_server_status(ip: str, port: int = 25565, protocol_version: int = 765, timeout: float = 2.0):
    async def _get_server_status():
        start_time = time.time()
        reader, writer = await asyncio.open_connection(ip, port)

        handshake = (
            encode_varint(0) +
            encode_varint(protocol_version) +
            encode_string(ip) +
            port.to_bytes(2, 'big') +
            encode_varint(1)
        )
        writer.write(encode_varint(len(handshake)) + handshake)
        await writer.drain()

        writer.write(encode_varint(1) + encode_varint(0))
        await writer.drain()

        packet_length = await read_varint(reader)
        packet_id = await read_varint(reader)
        if packet_id != 0:
            logger.error(f"[{ip}:{port}] Unexpected packet ID: {packet_id}", PREFIX)

        json_length = await read_varint(reader)
        json_data = await reader.readexactly(json_length)

        try:
            decompressed = zlib.decompress(json_data)
            json_data = decompressed
        except zlib.error:
            pass

        status = json.loads(json_data.decode('utf-8'))

        description = ""
        if "description" in status:
            description = parse_component(status["description"])

        return {
            "description": description,
            "plain_description": strip_mc_formatting(description) if description else "",

            "icon": status.get("favicon", f"{get_base64_from_image(DEFAULT_IMAGE)}"),
            "version_name": status.get("version", {}).get("name", ""),
            "version_protocol": status.get("version", {}).get("protocol", 0),
            
            "players_max": status.get("players", {}).get("max", 0),
            "players_online": status.get("players", {}).get("online", 0),
            "players_sample": status.get("players", {}).get("sample", []),
            
            "is_forge_server": True if status.get("modinfo", None) is not None else False,
            "mods": status.get("modinfo", {}).get("modList", None),
            "mod_loader": status.get("modinfo", {}).get("type", None),
            
            "latency": round(time.time() - start_time, 2)
        }
    
    # Getter with safe exeptions
    try:
        return await asyncio.wait_for(_get_server_status(), timeout=timeout)
    
    except asyncio.TimeoutError:
        logger.debug(f"[{ip}:{port}] Timeout after {timeout} seconds", PREFIX)
        return None
    
    except Exception as e:
        if "0 bytes read on a total of 1 expected bytes" in str(e):
            logger.warning(f"[{ip}:{port}] This server could have turned status off.", PREFIX)
            return {
                "icon": get_base64_from_image(DEFAULT_IMAGE)
            }
        
        logger.error(f"[{ip}:{port}] {str(e).replace("[Errno 111]", "")}", PREFIX)
        return None

# Testing via command line
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
        result = asyncio.run(get_server_status(args.ip, port))
        logger.info("Result: " + json.dumps(result, ensure_ascii=False), PREFIX)
    else:
        logger.warning("This is module part of Server Seeker.", PREFIX)
        logger.warning(f"You can only use it in code or > python {__file__} --ip IP --port PORT", PREFIX)
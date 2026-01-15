import asyncio
import json
import aiohttp
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logger import logger

PREFIX = "Minecraft Versions"
CACHE_FILE = "assets/protocol_versions.json"
SOURCE_URL = "https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/pc/common/protocolVersions.json"

async def _fetch_remote_data():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SOURCE_URL, timeout=5) as response:
                if response.status == 200:
                    return await response.json(content_type=None)
                else:
                    logger.error(f"Remote returned status {response.status}", PREFIX)
                    return None
    except Exception as e:
        logger.error(f"Error fetching versions from remote: {e}", PREFIX)
        return None

def _load_local_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading versions cache: {e}", PREFIX)
        return {}

async def _save_cache(cache):
    try:
        def write_sync():
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        
        await asyncio.to_thread(write_sync)
    except Exception as e:
        logger.warning(f"Error saving the versions cache: {e}", PREFIX)

async def update_cache():
    local_cache = _load_local_cache()
    remote_data = await _fetch_remote_data()
    
    if not remote_data:
        return local_cache

    new_entries = 0
    for entry in remote_data:
        version = entry.get("minecraftVersion")
        protocol = entry.get("version")
        if version and protocol:
            if version not in local_cache:
                new_entries += 1
            local_cache[version] = protocol

    if new_entries > 0:
        logger.info(f"{new_entries} new version(s) added.", PREFIX)
        await _save_cache(local_cache)
    return local_cache

async def get_protocol_version(version: str):
    cache = await update_cache()
    if version.endswith(".0"):
        version = version[:-2]
    return cache.get(version, None)

async def get_version_name(protocol: int):
    cache = await update_cache()
    for version, proto in cache.items():
        if proto == protocol:
            return version
    return None

def get_release_type(version) -> str:
    if version:
        if version.startswith("1.") and "-" not in version:
            return "release"
        if any(x in version for x in ["pre", "rc", "w"]):
            return "snapshot"
        return "unknown"
    return None
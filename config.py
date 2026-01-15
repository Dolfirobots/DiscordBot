import pathlib
import aiofiles
import json
import asyncio
import os
from typing import Any, Callable, Awaitable, Union

from logger import logger

PREFIX = "Config"
CONFIGS_DIR = pathlib.Path(__file__).parent.resolve() / "config"

class Config:
    _locks: dict[str, asyncio.Lock] = {}

    def __init__(self, relative_path: str):
        self.root = pathlib.Path(__file__).parent.resolve()
        self.path = CONFIGS_DIR / relative_path
        
        path_str = str(self.path.absolute())
        if path_str not in Config._locks:
            Config._locks[path_str] = asyncio.Lock()
        
        self.lock = Config._locks[path_str]

    async def validate(self, default_content: str = ""):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.warning(f"Config file {self.path.name} does not exist. Creating a new one.", PREFIX)
            try:
                if self.path.suffix == ".json" and not default_content:
                    default_content = "{}"
                
                async with aiofiles.open(self.path, mode='w', encoding='utf-8') as f:
                    await f.write(default_content)
                logger.success(f"Created new config file at {self.path.name}.", PREFIX)
            except Exception as e:
                logger.critical(f"Error creating config file {self.path.name}: {e}", PREFIX)
                raise

    # TXT
    async def get_lines(self, with_comments: bool = False) -> list[str]:
        try:
            async with self.lock:
                async with aiofiles.open(self.path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                
                lines = content.splitlines()
                if with_comments:
                    return [line.strip() for line in lines if line.strip()]
                
                return [
                    line.split("#")[0].strip() 
                    for line in lines 
                    if line.split("#")[0].strip()
                ]
        except Exception as e:
            logger.error(f"Error reading TXT file {self.path.name}: {e}", PREFIX)
            raise

    # JSON
    async def load_json(self) -> dict[str, Any]:
        try:
            async with aiofiles.open(self.path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content) if content.strip() else {}
        except Exception as e:
            logger.error(f"Error reading JSON file {self.path.name}: {e}", PREFIX)
            return {}

    async def save_json(self, data: dict[str, Any], indent: int = 4):
        temp_path = self.path.with_suffix(".tmp")
        try:
            async with aiofiles.open(temp_path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=indent, ensure_ascii=False))
            os.replace(temp_path, self.path)
        except Exception as e:
            logger.error(f"Error saving JSON file {self.path.name}: {e}", PREFIX)
            if temp_path.exists():
                os.remove(temp_path)
            raise

    async def update_json(self, func: Union[Callable[[dict], None], Callable[[dict], Awaitable[None]]]):
        async with self.lock:
            data = await self.load_json()
            if asyncio.iscoroutinefunction(func):
                await func(data)
            else:
                func(data)
            await self.save_json(data)
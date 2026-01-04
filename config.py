import pathlib
import aiofiles
import json
from typing import Any

from logger import logger

PREFIX = "Config"

class FileType:
    TXT = "txt"
    JSON = "json"
    YAML = "yaml" # in work

class Config:
    def __init__(self, relative_path: str, file_type: str):
        self.root = pathlib.Path(__file__).parent.resolve()
        self.path = self.root / "config" / relative_path
        self.file_type = file_type
    
    async def validate(self, default_content: str = ""):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.warning(f"Config file {self.path} does not exist. Creating a new one.", PREFIX)
            try:
                if self.file_type == FileType.JSON and not default_content:
                    default_content = "{}"
                
                async with aiofiles.open(self.path, mode='w', encoding='utf-8') as f:
                    await f.write(default_content)
                logger.info(f"Created new config file at {self.path}.", PREFIX)
            except Exception as e:
                logger.error(f"Error creating config file {self.path}: {e}", PREFIX)

    # --- TXT Methods ---
    async def get_lines(self, with_comments: bool = False) -> list[str]:
        try:
            async with aiofiles.open(self.path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                if with_comments:
                    return [
                        line.strip() 
                        for line in content.splitlines() 
                        if line.strip()
                    ]
                
                return [
                    line.split("#")[0].strip() 
                    for line in content.splitlines() 
                    if line.split("#")[0].strip()
                ]
        except Exception as e:
            logger.error(f"Error reading TXT file {self.path}: {e}", PREFIX)
            return []

    # --- JSON Methods ---
    async def load_json(self) -> dict[str, Any]:
        try:
            async with aiofiles.open(self.path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error reading JSON file {self.path}: {e}", PREFIX)
            return {}

    async def save_json(self, data: dict[str, Any], indent: int = 4):
        try:
            async with aiofiles.open(self.path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=indent, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Error saving JSON file {self.path}: {e}", PREFIX)
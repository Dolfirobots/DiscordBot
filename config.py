import pathlib
import aiofiles

from logger import logger

class FileType:
    TXT = "txt"
    JSON = "json" # in work
    YAML = "yaml" # in work

class Config:
    def __init__(self, relative_path: str, file_type: FileType):
        self.root = pathlib.Path(__file__).parent.resolve()
        self.path = self.root / "config" / relative_path
        self.file_type = file_type
    
    # Checking if config file exists, if not create it
    async def validate(self, default_content: str = ""):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.warning(f"Config file {self.path} does not exist. Creating a new one.")
            try:
                async with aiofiles.open(self.path, mode='w', encoding='utf-8') as f:
                    await f.write(default_content)
                logger.info(f"Created new config file at {self.path}.")
            except Exception as e:
                logger.error(f"Error creating config file {self.path}: {e}")

    # TXT methods
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
            logger.error(f"Error reading and parsing config file {self.path}: {e}")
            return []
        
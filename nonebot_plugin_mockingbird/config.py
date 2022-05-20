import json
import os
from pathlib import Path
from typing import Optional

import nonebot
from nonebot.log import logger

from .download import get_model_list_file

global_config = nonebot.get_driver().config
if not hasattr(global_config, "mockingbird_path"):
    MOCKINGBIRD_PATH = os.path.join(os.path.dirname(__file__), "resource")
else:
    MOCKINGBIRD_PATH = global_config.mockingbird_path

class MockingBirdManager:
    def __init__(self, path: Optional[Path]):
        self.model_list = {}
        self.config = {}

        if not path:
            model_list_file = Path(MOCKINGBIRD_PATH) / "model_list.json"
            config_file = Path(MOCKINGBIRD_PATH) / "config.json"
        else:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            model_list_file = path / "model_list.json"
            config_file = path / "config.json"

        self.model_list_file = model_list_file
        self.config_file = config_file

        if not model_list_file.exists():
            logger.info("Downloading MockingBird model data resource...")
            get_model_list_file(model_list_file)
            with open(model_list_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(dict()))
                f.close()

        if model_list_file.exists():
            with open(model_list_file, "r", encoding="utf-8") as f:
                self.model_list = json.load(f)

        if not config_file.exists():
            self.init_data()

        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)

    def init_data(self) -> None:
        """
        初始化配置文件
        """
        self.config = {
            "model": "azusa",
            "voice_accuracy": 9,
            "max_steps": 4,
        }
        self.save_data()
    
    def set_config(self, config_name: str, value) -> None:
        self.config[config_name] = value
        self.save_data()

    def get_config(self, config_name: str):
        return self.config[config_name]

    def save_data(self) -> None:
        """
        保存配置文件
        """
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def get_model_list(self) -> dict:
        return self.model_list

Config = MockingBirdManager(Path(MOCKINGBIRD_PATH))
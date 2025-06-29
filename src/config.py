import json
import sys
import time
import winreg
from pathlib import Path
from typing import Dict, Optional

from .constants import CONFIG_FILE
from .models import AppConfig

DEFAULT_CONFIG = {
    "Github_Personal_Token": "",
    "Custom_Steam_Path": "",
    "Debug_Mode": False,
    "Logging_Files": True,
    "Help": "The Github Personal Token can be generated in the Developer settings section of GitHub.",
}


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.config_path = CONFIG_FILE
        self._config_data: Dict = {}
        self.app_config: AppConfig = AppConfig()
        self.steam_path: Optional[Path] = None
        self._load_config()

    def _generate_config(self) -> None:
        """生成默认配置文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            print("The configuration file has been generated.")
        except IOError as e:
            print(f"Configuration file creation failed:{str(e)}")
            sys.exit(1)

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            self._generate_config()
            print("Please fill in the configuration file and then run the program again. It will exit after 5 seconds.")
            time.sleep(5)
            sys.exit(1)

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config_data = json.load(f)

            self.app_config = AppConfig(
                github_token=self._config_data.get("Github_Personal_Token", ""),
                custom_steam_path=self._config_data.get("Custom_Steam_Path", ""),
                debug_mode=self._config_data.get("Debug_Mode", False),
                logging_files=self._config_data.get("Logging_Files", True),
            )

            self.steam_path = self._get_steam_path()

        except json.JSONDecodeError:
            print("Configuration file is damaged. Re-generating...")
            self._generate_config()
            sys.exit(1)
        except Exception as e:
            print(f"Configuration file loading failed:{str(e)}")
            sys.exit(1)

    def _get_steam_path(self) -> Path:
        """获取Steam安装路径"""
        try:
            if self.app_config.custom_steam_path:
                return Path(self.app_config.custom_steam_path)

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"
            ) as key:
                return Path(winreg.QueryValueEx(key, "SteamPath")[0])
        except Exception as e:
            print(f"Failed to obtain the Steam installed path:{str(e)}")
            sys.exit(1)

    @property
    def github_headers(self) -> Optional[Dict[str, str]]:
        """获取GitHub请求头"""
        if self.app_config.github_token:
            return {"Authorization": f"Bearer {self.app_config.github_token}"}
        return None

import traceback
from typing import List, Dict, Tuple

from . import __version__, __author__, __website__
from .constants import BANNER, REPO_LIST
from .config import ConfigManager
from .logger import Logger
from .models import DepotInfo
from .network.client import HttpClient
from .network.github import GitHubAPI
from .utils.region import RegionDetector
from .utils.steam import parse_key_file, parse_manifest_filename
from .tools.steamtools import SteamTools
from .tools.greenluma import GreenLuma


class OnekeyApp:
    """Onekey主应用"""

    def __init__(self):
        self.config = ConfigManager()
        self.logger = Logger(
            "Onekey",
            debug_mode=self.config.app_config.debug_mode,
            log_file=self.config.app_config.logging_files,
        )
        self.client = HttpClient()
        self.github = GitHubAPI(self.client, self.config.github_headers, self.logger)

    def show_banner(self):
        """显示横幅"""
        self.logger.info(BANNER)
        self.logger.info(
            f"The source code of this program is open on Github under the GPL 2.0 license."
        )
        self.logger.info(
            f"Author: {__author__} | Version: {__version__} | Official Website: {__website__}"
        )
        self.logger.info("GitHub Repository: https://github.com/ikunshare/Onekey")
        self.logger.warning("ikunshare.top | Prohibition of resale")
        self.logger.warning(
            "Note: Make sure you have Windows 10/11 installed and properly configure Steam. SteamTools/GreenLuma"
        )
        if not self.config.app_config.github_token:
            self.logger.warning("If you use the VPN, a Token must be configured. I don't believe your IP address can be that clean.")

    async def handle_depot_files(
        self, app_id: str
    ) -> Tuple[List[DepotInfo], Dict[str, List[str]]]:
        """处理仓库文件"""
        depot_list = []
        depot_map = {}

        repo_info = await self.github.get_latest_repo_info(REPO_LIST, app_id)
        if not repo_info:
            return depot_list, depot_map

        self.logger.info(f"Current selected manifest repository: https://github.com/{repo_info.name}")
        self.logger.info(f"The last update time of this manifest branch：{repo_info.last_update}")

        branch_url = f"https://api.github.com/repos/{repo_info.name}/branches/{app_id}"
        branch_res = await self.client.get(
            branch_url, headers=self.config.github_headers
        )
        branch_res.raise_for_status()

        tree_url = branch_res.json()["commit"]["commit"]["tree"]["url"]
        tree_res = await self.client.get(tree_url)
        tree_res.raise_for_status()

        depot_cache = self.config.steam_path / "depotcache"
        depot_cache.mkdir(exist_ok=True)

        for item in tree_res.json()["tree"]:
            file_path = item["path"]

            if file_path.endswith(".manifest"):
                save_path = depot_cache / file_path
                if save_path.exists():
                    self.logger.warning(f"Existing manifest: {save_path}")
                    continue

                content = await self.github.fetch_file(
                    repo_info.name, repo_info.sha, file_path
                )
                save_path.write_bytes(content)
                self.logger.info(f"Manifest download successful: {file_path}")

                depot_id, manifest_id = parse_manifest_filename(file_path)
                if depot_id and manifest_id:
                    depot_map.setdefault(depot_id, []).append(manifest_id)

            elif "key.vdf" in file_path.lower():
                key_content = await self.github.fetch_file(
                    repo_info.name, repo_info.sha, file_path
                )
                depot_list.extend(parse_key_file(key_content))

        for depot_id in depot_map:
            depot_map[depot_id].sort(key=lambda x: int(x), reverse=True)

        return depot_list, depot_map

    async def run(self, app_id: str):
        """运行主程序"""
        try:
            detector = RegionDetector(self.client, self.logger)
            is_cn, country = await detector.check_cn()
            self.github.is_cn = is_cn

            await self.github.check_rate_limit()

            self.logger.info(f"Game is currently being processed: {app_id}...")
            depot_data, depot_map = await self.handle_depot_files(app_id)

            if not depot_data:
                self.logger.error("No manifest of this game was found.")
                return

            print("\nPlease select the unlocking tool:")
            print("1. SteamTools")
            print("2. GreenLuma")

            choice = input("Please enter your choice (1/2): ").strip()

            if choice == "1":
                tool = SteamTools(self.config.steam_path)

                version_lock = False
                lock_choice = input(
                    "Is version locking enabled (recommended to use when selecting the repository SteamAutoCracks/ManifestHub)? (y/n):"
                ).lower()
                if lock_choice == "y":
                    version_lock = True

                success = await tool.setup(
                    depot_data, app_id, depot_map=depot_map, version_lock=version_lock
                )
            elif choice == "2":
                tool = GreenLuma(self.config.steam_path)
                success = await tool.setup(depot_data, app_id)
            else:
                self.logger.error("An ineffective choice.")
                return

            if success:
                self.logger.info("Game unlocking configuration successful!")
                self.logger.info("It will take effect after restarting Steam.")
            else:
                self.logger.error("Unlock the game failed.")

        except Exception as e:
            self.logger.error(f"error: {traceback.format_exc()}")
        finally:
            await self.client.close()


async def main():
    """程序入口"""
    app = OnekeyApp()
    app.show_banner()

    app_id = input("\nPlease enter the game AppID: ").strip()

    app_id_list = [id for id in app_id.split("-") if id.isdigit()]
    if not app_id_list:
        app.logger.error("Invalid App ID")
        return

    await app.run(app_id_list[0])

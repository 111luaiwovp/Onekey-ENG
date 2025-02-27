DEFAULT_CONFIG = {
    "Github_Personal_Token": "",
    "Custom_Steam_Path": "",
    "QA1": "Github Personal Token����GitHub���õ�Developer settings������",
    "�̳�": "https://ikunshare.com/Onekey_tutorial",
}

import platform
import sys
import os
import traceback
import logzero
import asyncio
import aiofiles
import httpx
import winreg
import ujson as json
import vdf
from typing import Any, Tuple, List, Dict
from pathlib import Path
from enum import Enum


class RepoChoice(Enum):
    IKUN = ("ikun0014/ManifestHub", "�Ѷϸ��ľɲֿ�")
    AUIOWU = ("Auiowu/ManifestAutoUpdate", "δ֪ά��״̬�Ĳֿ�")
    STEAM_AUTO = ("SteamAutoCracks/ManifestHub", "�ٷ��Ƽ��ֿ�")


DEFAULT_CONFIG = {
    "Github_Personal_Token": "",
    "Custom_Steam_Path": "",
    "QA1": "Github Personal Token����GitHub���õ�Developer settings������",
    "�̳�": "https://ikunshare.com/Onekey_tutorial",
}

DEFAULT_REPO = RepoChoice.STEAM_AUTO
WINDOWS_VERSIONS = ["10", "11"]
STEAM_REG_PATH = r"Software\Valve\Steam"
CONFIG_PATH = Path("./config.json")
LOCK = asyncio.Lock()
CLIENT = httpx.AsyncClient(verify=False, timeout=30)

log = logzero.setup_logger("Onekey")


def init() -> None:
    """��ʼ������̨���"""
    banner = r"""
    _____   __   _   _____   _   _    _____  __    __ 
   /  _  \ |  \ | | | ____| | | / /  | ____| \ \  / /
   | | | | |   \| | | |__   | |/ /   | |__    \ \/ / 
   | | | | | |\   | |  __|  | |\ \   |  __|    \  /  
   | |_| | | | \  | | |___  | | \ \  | |___    / /   
   \_____/ |_|  \_| |_____| |_|  \_\ |_____|  /_/    
    """
    print(banner)
    print("����: ikun0014 | �汾: 1.3.7 | ����: ikunshare.com")
    print("��Ŀ�ֿ�: GitHub: https://github.com/ikunshare/Onekey")
    print("��ʾ: ��ȷ���Ѱ�װ���°�Windows 10/11����ȷ����Steam")


def validate_windows_version() -> None:
    """��֤Windows�汾"""
    if platform.system() != "Windows":
        log.error("��֧��Windows����ϵͳ")
        sys.exit(1)

    release = platform.uname().release
    if release not in WINDOWS_VERSIONS:
        log.error(f"��ҪWindows 10/11����ǰ�汾: Windows {release}")
        sys.exit(1)


async def load_config() -> Dict[str, Any]:
    """�첽���������ļ�"""
    if not CONFIG_PATH.exists():
        await generate_config()
        log.info("����д�����ļ����������г���")
        sys.exit(0)

    try:
        async with aiofiles.open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except json.JSONDecodeError:
        log.error("�����ļ��𻵣�������������...")
        await generate_config()
        sys.exit(1)
    except Exception as e:
        log.error(f"���ü���ʧ��: {str(e)}")
        sys.exit(1)


async def generate_config() -> None:
    """����Ĭ�������ļ�"""
    try:
        async with aiofiles.open(CONFIG_PATH, "w", encoding="utf-8") as f:
            await f.write(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False))
        log.info("�����ļ�������")
    except IOError as e:
        log.error(f"�����ļ�����ʧ��: {str(e)}")
        sys.exit(1)


def get_steam_path(config: Dict) -> Path:
    """��ȡSteam��װ·��"""
    try:
        if custom_path := config.get("Custom_Steam_Path"):
            return Path(custom_path)

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STEAM_REG_PATH) as key:
            return Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except Exception as e:
        log.error(f"Steam·����ȡʧ��: {str(e)}")
        sys.exit(1)


async def download_key(file_path: str, repo: str, sha: str) -> bytes:
    """������Կ�ļ�"""
    try:
        return await fetch_from_cdn(file_path, repo, sha)
    except Exception as e:
        log.error(f"��Կ����ʧ��: {str(e)}")
        raise


async def handle_depot_files(
    repo: str, app_id: str, steam_path: Path
) -> List[Tuple[str, str]]:
    """�����嵥�ļ�����Կ"""
    collected = []
    try:
        async with httpx.AsyncClient() as client:
            branch_url = f"https://api.github.com/repos/{repo}/branches/{app_id}"
            branch_res = await client.get(branch_url)
            branch_res.raise_for_status()

            tree_url = branch_res.json()["commit"]["commit"]["tree"]["url"]
            tree_res = await client.get(tree_url)
            tree_res.raise_for_status()

            depot_cache = steam_path / "depotcache"
            depot_cache.mkdir(exist_ok=True)

            for item in tree_res.json()["tree"]:
                file_path = item["path"]
                if file_path.endswith(".manifest"):
                    await download_manifest(
                        file_path, depot_cache, repo, branch_res.json()["commit"]["sha"]
                    )
                elif "key.vdf" in file_path.lower():
                    key_content = await download_key(
                        file_path, repo, branch_res.json()["commit"]["sha"]
                    )
                    collected.extend(parse_key_vdf(key_content))
    except httpx.HTTPStatusError as e:
        log.error(f"HTTP����: {e.response.status_code}")
    except Exception as e:
        log.error(f"�ļ�����ʧ��: {str(e)}")
    return collected


async def download_manifest(path: str, save_dir: Path, repo: str, sha: str) -> None:
    """�����嵥�ļ�"""
    save_path = save_dir / path
    if save_path.exists():
        log.warning(f"�嵥�Ѵ���: {path}")
        return

    content = await fetch_from_cdn(path, repo, sha)
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)
    log.info(f"�嵥���سɹ�: {path}")


async def fetch_from_cdn(path: str, repo: str, sha: str) -> bytes:
    """��CDN��ȡ��Դ"""
    mirrors = (
        [
            f"https://jsdelivr.pai233.top/gh/{repo}@{sha}/{path}",
            f"https://cdn.jsdmirror.com/gh/{repo}@{sha}/{path}",
            f"https://raw.gitmirror.com/{repo}/{sha}/{path}",
        ]
        if os.environ.get("IS_CN") == "yes"
        else [f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"]
    )

    for url in mirrors:
        try:
            res = await CLIENT.get(url)
            res.raise_for_status()
            return res.content
        except httpx.HTTPError:
            continue
    raise Exception("���о���Դ��������")


def parse_key_vdf(content: bytes) -> List[Tuple[str, str]]:
    """������Կ�ļ�"""
    try:
        depots = vdf.loads(content.decode("utf-8"))["depots"]
        return [(d_id, d_info["DecryptionKey"]) for d_id, d_info in depots.items()]
    except Exception as e:
        log.error(f"��Կ����ʧ��: {str(e)}")
        return []


async def setup_unlock_tool(
    config: Dict, depot_data: List[Tuple[str, str]], app_id: str, tool_choice: int
) -> bool:
    """���ý�������"""
    if tool_choice == 1:
        return await setup_steamtools(config, depot_data, app_id)
    elif tool_choice == 2:
        return await setup_greenluma(config, depot_data)
    else:
        log.error("��Ч�Ĺ���ѡ��")
        return False


async def setup_steamtools(
    config: Dict, depot_data: List[Tuple[str, str]], app_id: str
) -> bool:
    """����SteamTools"""
    steam_path = (
        Path(config["Custom_Steam_Path"])
        if config.get("Custom_Steam_Path")
        else get_steam_path(config)
    )
    st_path = steam_path / "config" / "stplug-in"
    st_path.mkdir(exist_ok=True)

    lua_content = f'addappid({app_id}, 1, "None")\n'
    for d_id, d_key in depot_data:
        lua_content += f'addappid({d_id}, 1, "{d_key}")\n'

    lua_file = st_path / f"{app_id}.lua"
    async with aiofiles.open(lua_file, "w") as f:
        await f.write(lua_content)

    proc = await asyncio.create_subprocess_exec(
        str(st_path / "luapacka.exe"),
        str(lua_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()

    if proc.returncode != 0:
        log.error(f"Lua����ʧ��: {await proc.stderr.read()}")
        return False
    return True


async def setup_greenluma(config: Dict, depot_data: List[Tuple[str, str]]) -> bool:
    """����GreenLuma"""
    steam_path = (
        Path(config["Custom_Steam_Path"])
        if config.get("Custom_Steam_Path")
        else get_steam_path(config)
    )
    applist_dir = steam_path / "AppList"
    applist_dir.mkdir(exist_ok=True)

    for f in applist_dir.glob("*.txt"):
        f.unlink()

    for idx, (d_id, _) in enumerate(depot_data, 1):
        (applist_dir / f"{idx}.txt").write_text(str(d_id))

    config_path = steam_path / "config" / "config.vdf"
    async with aiofiles.open(config_path, "r+") as f:
        content = vdf.loads(await f.read())
        content.setdefault("depots", {}).update(
            {d_id: {"DecryptionKey": d_key} for d_id, d_key in depot_data}
        )
        await f.seek(0)
        await f.write(vdf.dumps(content))
    return True


async def main_flow():
    """�����̿���"""
    validate_windows_version()
    init()

    try:
        app_id = input("��������ϷAppID: ").strip()
        if not app_id.isdigit():
            raise ValueError("��Ч��AppID")

        print(
            "\n".join(
                [f"{idx+1}. {item.value[1]}" for idx, item in enumerate(RepoChoice)]
            )
        )
        repo_choice = int(input("��ѡ���嵥�ֿ� (Ĭ��3): ") or 3)
        selected_repo = list(RepoChoice)[repo_choice - 1].value[0]

        tool_choice = int(input("��ѡ��������� (1.SteamTools 2.GreenLuma): "))

        config = await load_config()
        steam_path = get_steam_path(config)
        depot_data = await handle_depot_files(selected_repo, app_id, steam_path)

        if await setup_unlock_tool(config, depot_data, app_id, tool_choice):
            log.info("��Ϸ�������óɹ���")
            if tool_choice == 1:
                log.info("������SteamTools��Ч")
            elif tool_choice == 2:
                log.info("������GreenLuma��Ч")
        else:
            log.error("����ʧ�ܣ�������־")
    except Exception as e:
        log.error(f"���д���: {str(e)}")
        log.debug(traceback.format_exc())
    finally:
        await CLIENT.aclose()


if __name__ == "__main__":
    asyncio.run(main_flow())
    os.system("pause")

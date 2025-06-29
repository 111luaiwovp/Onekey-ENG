from typing import Tuple

from ..constants import REGION_CHECK_URL
from ..network.client import HttpClient
from ..logger import Logger


class RegionDetector:
    """地区检测器"""

    def __init__(self, client: HttpClient, logger: Logger):
        self.client = client
        self.logger = logger

    async def check_cn(self) -> Tuple[bool, str]:
        """检查是否在中国大陆"""
        try:
            req = await self.client.get(REGION_CHECK_URL)
            body = req.json()
            is_cn = bool(body.get("flag", True))
            country = body.get("country", "Unknown")

            if not is_cn:
                self.logger.info(
                    f"You have used the project in the non-China region ({country}). "
                    "The system has automatically switched back to the official Github download CDN."
                )

            return is_cn, country
        except Exception as e:
            self.logger.warning("Failed to check the server location. Automatically assume that you are in China mainland.")
            return True, "CN"

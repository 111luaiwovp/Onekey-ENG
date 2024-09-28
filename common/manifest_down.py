from aiohttp import ClientError, ClientResponse
from tqdm.asyncio import tqdm_asyncio
from typing import Union

from .log import log


async def get(sha: str, path: str, repo: str, session, chunk_size: int = 1024) -> bytearray:
    url_list = [
        f'https://cdn.jsdmirror.com/gh/{repo}@{sha}/{path}',
        f'https://jsd.onmicrosoft.cn/gh/{repo}@{sha}/{path}',
        f'https://raw.dgithub.xyz/{repo}/{sha}/{path}',
        f'https://raw.gitmirror.com/{repo}/{sha}/{path}',
        f'https://raw.githubusercontent.com/{repo}/{sha}/{path}'
    ]
    
    retry = 3
    while retry > 0:
        for url in url_list:
            try:
                # log.debug(f"尝试从 URL: {url} 下载文件: {path}")
                async with session.get(url, ssl=False) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('Content-Length', 0))
                        content = bytearray()

                        with tqdm_asyncio(total=total_size, unit='B', unit_scale=True, desc=f'下载 {path}', colour='#ffadad') as pbar:
                            async for chunk in response.content.iter_chunked(chunk_size):
                                content.extend(chunk)
                                pbar.update(len(chunk))
                        
                        return content
                    else:
                        log.error(f'🔄 获取失败: {path} - 状态码: {response.status}')
            except ClientError as e:
                log.error(f'🔄 获取失败: {path} - 连接错误: {str(e)}')
        
        retry -= 1
        log.warning(f'🔄 重试剩余次数: {retry} - {path}')
    
    log.error(f'🔄 超过最大重试次数: {path}')
    raise Exception(f'🔄 无法下载: {path}')

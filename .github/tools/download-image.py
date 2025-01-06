import json
import os
import logging
from pathlib import Path
from urllib.request import getproxies, urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_system_proxy():
    """
    获取并过滤系统代理设置，仅保留 HTTP 和 HTTPS 代理。
    :return: 返回代理字典，如 {'http': 'http://127.0.0.1:8080', 'https': 'https://127.0.0.1:8080'}
    """
    proxies = getproxies()
    filtered_proxies = {k: v.replace('https', 'http') if k == 'https' else v for k, v in proxies.items() if k in ['http', 'https']}

    if filtered_proxies:
        print(f"检测到系统代理配置：{filtered_proxies}")
    else:
        print("未检测到系统代理配置。")
    return filtered_proxies

def load_json(file_path):
    """加载 JSON 文件"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"{file_path} 不存在，返回空字典")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"解析 {file_path} 出错: {e}")
        return {}

def save_json(file_path, data):
    """保存 JSON 文件"""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"保存 {file_path} 出错: {e}")

def download_image(download_url, save_path, retries=3, proxy=None):
    """下载图片并保存"""
    for attempt in range(retries):
        try:
            req = Request(download_url)
            if proxy:
                req.set_proxy(proxy.get("http"), "http")
                req.set_proxy(proxy.get("https"), "https")
            
            with urlopen(req, timeout=10) as response:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as image_file:
                    image_file.write(response.read())
            logging.info(f"图片已下载: {save_path}")
            return
        except (HTTPError, URLError) as e:
            logging.warning(f"下载失败 ({attempt + 1}/{retries})，错误: {e}")
            time.sleep(2 ** attempt)
    logging.error(f"最终无法下载图片: {download_url}")

def fetch_api_content(url, headers=None, retries=3, proxy=None):
    """获取 API 内容"""
    for attempt in range(retries):
        try:
            req = Request(url, headers=headers or {})
            if proxy:
                req.set_proxy(proxy.get("http"), "http")
                req.set_proxy(proxy.get("https"), "https")
            
            with urlopen(req, timeout=10) as response:
                return json.load(response)
        except (HTTPError, URLError) as e:
            logging.warning(f"请求失败 ({attempt + 1}/{retries})，错误: {e}")
            time.sleep(2 ** attempt)
    logging.error(f"最终无法获取内容: {url}")
    return None

def process_repo(base_url, repo_name, repo_dirs, hash_file, headers=None, proxies=None):
    """
    通用仓库处理逻辑
    :param base_url: 仓库 API 基础 URL
    :param repo_name: 仓库名称
    :param repo_dirs: 需要处理的目录列表
    :param hash_file: 已下载文件的哈希记录
    :param headers: 请求头
    :param proxies: 代理设置
    """
    for dir_name in repo_dirs:
        url = f"{base_url}/{dir_name}"
        contents = fetch_api_content(url, headers=headers, proxy=proxies)
        if not contents:
            logging.error(f"无法获取 {repo_name}/{dir_name} 的内容")
            continue

        logging.info(f"需要下载 {len(contents)} 个文件")
        for item in contents:
            if item.get('type') == 'file' and item['name'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                if item['sha'] in hash_file:
                    logging.info(f"跳过 {item['name']}，因为它已下载")
                    continue

                image_name = os.path.basename(item['download_url'])
                save_path = Path(f"./downloaded_images/{repo_name}/{dir_name}/{image_name}")
                download_image(item['download_url'], save_path, proxy=proxies)
                hash_file[item['sha']] = image_name


def process_github_repo(repo_name, repo_dirs, hash_file, access_token=None, proxies=None):
    """
    处理 GitHub 仓库
    :param repo_name: 仓库名称
    :param repo_dirs: 需要处理的目录列表
    :param hash_file: 已下载文件的哈希记录
    :param access_token: GitHub 访问令牌
    :param proxies: 代理设置
    """
    headers = {}
    if access_token:
        headers['Authorization'] = f"token {access_token}"
    base_url = f"https://api.github.com/repos/{repo_name}/contents"
    process_repo(base_url, repo_name, repo_dirs, hash_file, headers, proxies)


def process_gitee_repo(repo_name, repo_dirs, hash_file, access_token=None, proxies=None):
    """
    处理 Gitee 仓库
    :param repo_name: 仓库名称
    :param repo_dirs: 需要处理的目录列表
    :param hash_file: 已下载文件的哈希记录
    :param access_token: Gitee 访问令牌
    :param proxies: 代理设置
    """
    headers = {}
    if access_token:
        headers['Authorization'] = f"token {access_token}"
    base_url = f"https://gitee.com/api/v5/repos/{repo_name}/contents"
    process_repo(base_url, repo_name, repo_dirs, hash_file, headers, proxies)


def main():
    # 自动识别系统代理
    proxies = get_system_proxy()

    # 读取配置和哈希文件
    config = load_json('config.json')
    hash_file = load_json("downloaded_images/file.json")

    # 下载图片
    for repo_info in config.get('repos', []):
        repo_name = repo_info.get('repo')
        repo_type = repo_info.get('type')
        repo_dirs = repo_info.get('dir', [])

        if not repo_name or not repo_type or not repo_dirs:
            logging.warning("配置缺少必要字段，跳过此仓库")
            continue

        access_token = repo_info.get('token')
        if repo_type == "github":
            process_github_repo(repo_name, repo_dirs, hash_file, access_token, proxies)
        elif repo_type == "gitee":
            process_gitee_repo(repo_name, repo_dirs, hash_file, access_token, proxies)
        else:
            logging.warning(f"不支持的仓库类型: {repo_type}")

    # 保存更新后的哈希文件
    save_json("downloaded_images/file.json", hash_file)

if __name__ == "__main__":
    main()

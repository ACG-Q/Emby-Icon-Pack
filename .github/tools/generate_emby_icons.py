import os
import json
import argparse

# 读取配置文件
def read_config(config_path):
    """
    读取配置文件并返回 JSON 数据。
    """
    with open(config_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# 写入 JSON 文件
def write_json(path, content):
    """
    将内容写入指定路径的 JSON 文件。
    """
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(content, file, ensure_ascii=False, indent=4)

# 获取文件夹及其子文件夹中的图片文件列表
def get_image_files(folder_path):
    """
    获取指定文件夹及其所有子文件夹中的所有图片文件，支持的格式为 PNG、JPG、JPEG 和 GIF，
    并返回相对于根目录的父目录的文件路径。
    """
    image_files = []
    # 获取 folder_path 的父目录
    parent_folder_path = os.path.dirname(folder_path)
    
    # 遍历所有子目录及文件
    for root, dirs, files in os.walk(folder_path):
        # 遍历每个文件，如果是图片文件则添加到 image_files 列表中
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                # 获取相对于父目录的文件路径
                relative_path = os.path.relpath(os.path.join(root, file), parent_folder_path)
                relative_path = relative_path.replace(os.sep, '/')
                image_files.append(relative_path)
    return image_files

# 生成图片的完整 URL
def generate_image_urls(image_files, proxy_data, repo, branch="main", owner="github"):
    """
    根据代理规则或默认格式生成图片的 URL 列表。
    """
    image_urls = []
    for image in image_files:
        if not proxy_data:
            # 如果没有代理，使用 GitHub raw URL 结构
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{image}"
        else:
            url = proxy_data['format'].format(
                proxy=proxy_data['proxy'],
                branch=branch,
                owner=owner,
                repo=repo,
                file=image
            )
        
        name = os.path.splitext(os.path.basename(image))[0]
        image_urls.append({"name": name, "url": url})
    return image_urls

# 生成不使用代理的图标库 JSON 文件
def generate_no_proxy_json(image_files, repo, output_dir, branch, owner):
    """
    生成不使用代理的 JSON 文件，并写入指定路径。
    """
    icons = generate_image_urls(image_files, None, repo, branch, owner)
    result = {
        "name": "Emby Icons (No Proxy)",
        "description": "不使用代理生成的 Emby 图标库",
        "icons": icons
    }
    output_file = os.path.join(output_dir, "output.json")
    write_json(output_file, result)
    print(f"JSON 数据已生成到 {output_file}")

# 生成带代理的图标库 JSON 文件
def generate_proxy_json(image_files, config, repo, output_dir, branch, owner):
    """
    根据代理配置生成带代理的 JSON 文件，并写入相应路径。
    """
    for proxy_name, proxy_data in config['proxy_rules'].items():
        if proxy_name == 'no_proxy':  # 跳过 'no_proxy' 规则
            continue
        icons = generate_image_urls(image_files, proxy_data, repo, branch, owner)
        result = {
            "name": f"Emby Icons ({proxy_name})",
            "description": f"通过 {proxy_name} 代理生成的 Emby 图标库",
            "icons": icons
        }
        output_file = os.path.join(output_dir, f"output_{proxy_name}.json")
        write_json(output_file, result)
        print(f"JSON 数据已生成到 {output_file}")

# 主函数
def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="生成 Emby 图标的 JSON 文件")
    parser.add_argument('-o', '--owner', type=str, required=True, help='仓库拥有者名称')
    parser.add_argument('-r', '--repo', type=str, required=True, help='当前仓库名称')
    parser.add_argument('-b', '--branch', type=str, default="main", help='分支名称，默认为 "main"')
    parser.add_argument('--output', type=str, default="output", help='输出目录')
    args = parser.parse_args()

    # 定义路径
    config_path = "config.json"
    images_folder = "downloaded_images"
    output_dir = args.output

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 定义额外信息
    owner = args.owner  # 使用命令行传递的仓库拥有者名称
    repo = args.repo  # 使用命令行传递的仓库名
    branch = args.branch  # 使用命令行传递的分支名

    # 读取配置和图片
    config = read_config(config_path)
    image_files = get_image_files(images_folder)

    # 先生成不使用代理的 JSON 文件
    generate_no_proxy_json(image_files, repo, output_dir, branch, owner)

    # 遍历代理规则，生成对应的 JSON 文件
    generate_proxy_json(image_files, config, repo, output_dir, branch, owner)

if __name__ == "__main__":
    main()

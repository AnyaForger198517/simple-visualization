import json
import time
from datetime import datetime
from collections import defaultdict
import os
import re


def load_data_from_file(filename):
    """从JSON文件加载数据"""
    # 清理文件名，移除可能的引号
    filename = filename.strip('"\'')

    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_utc_to_date(utc_timestamp):
    """将UTC时间戳转换为年月日格式"""
    dt = datetime.fromtimestamp(utc_timestamp)
    return dt.strftime("%Y-%m-%d")


def process_data_file(input_file):
    """处理数据文件：转换时间戳并按月份分类"""
    # 清理文件名，移除可能的引号
    input_file = input_file.strip('"\'')

    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件 '{input_file}' 不存在")
        return False

    # 从文件加载数据
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: 文件 '{input_file}' 不是有效的JSON格式")
        print(f"详细信息: {e}")
        return False
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(input_file, "r", encoding="gbk") as f:
                data = json.load(f)
        except:
            print(f"错误: 无法读取文件 '{input_file}'，请检查编码")
            return False

    print(f"成功加载 {len(data)} 条记录")

    # 检查数据格式
    if not isinstance(data, list):
        print(f"警告: 数据格式不是列表，尝试转换...")
        # 如果是字典，尝试提取可能的键
        if isinstance(data, dict):
            # 查找包含帖子数据的键
            possible_keys = ['posts', 'articles', 'data', 'items']
            for key in possible_keys:
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    print(f"从键 '{key}' 中提取了 {len(data)} 条记录")
                    break
            else:
                print("错误: 无法识别数据格式")
                return False

    # 任务1: 将created_utc转换为年月日形式
    processed_count = 0
    error_count = 0
    for item in data:
        try:
            utc_timestamp = item.get("created_utc")
            if utc_timestamp and isinstance(utc_timestamp, (int, float)):
                date_str = convert_utc_to_date(utc_timestamp)
                item["created_date"] = date_str
                processed_count += 1
            else:
                item["created_date"] = "Unknown"
                error_count += 1
        except Exception as e:
            item["created_date"] = "Error"
            error_count += 1
            print(f"警告: 处理记录时出错: {e}")

    print(f"已处理 {processed_count} 条记录，{error_count} 条记录有问题")

    # 基于输入文件名创建输出文件名
    input_dir, input_filename = os.path.split(input_file)
    input_name, input_ext = os.path.splitext(input_filename)

    # 保存任务1的结果
    output_file = f"{input_name}_with_dates.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"任务1完成: 已保存到 {output_file}")

    # 任务2: 按月份分类
    monthly_data = defaultdict(list)
    unknown_posts = []
    error_posts = []

    for item in data:
        date_str = item.get("created_date", "")
        if date_str == "Unknown":
            unknown_posts.append(item)
        elif date_str == "Error":
            error_posts.append(item)
        elif date_str:
            year_month = date_str[:7]  # 取前7个字符，如 "2026-01"
            monthly_data[year_month].append(item)

    # 为每个月份创建单独的JSON文件
    output_dir = f"{input_name}_monthly_posts"
    os.makedirs(output_dir, exist_ok=True)

    files_created = 0
    for month, posts in monthly_data.items():
        # 清理月份名称，确保是有效的文件名
        month_clean = month.replace(":", "_").replace("/", "_")
        filename = os.path.join(output_dir, f"{month_clean}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        files_created += 1
        print(f"已创建 {filename}，包含 {len(posts)} 条记录")

    # 如果有日期未知的帖子，单独保存
    if unknown_posts:
        filename = os.path.join(output_dir, "unknown_date.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(unknown_posts, f, indent=2, ensure_ascii=False)
        files_created += 1
        print(f"已创建 {filename}，包含 {len(unknown_posts)} 条日期未知的记录")

    # 如果有错误的帖子，单独保存
    if error_posts:
        filename = os.path.join(output_dir, "error_date.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(error_posts, f, indent=2, ensure_ascii=False)
        files_created += 1
        print(f"已创建 {filename}，包含 {len(error_posts)} 条日期错误的记录")

    # 创建月份索引文件
    index_data = {
        "input_file": input_file,
        "total_months": len(monthly_data),
        "months": sorted(list(monthly_data.keys())),
        "total_posts": len(data),
        "posts_by_month": {month: len(posts) for month, posts in monthly_data.items()},
        "posts_with_unknown_date": len(unknown_posts),
        "posts_with_error_date": len(error_posts)
    }

    with open(os.path.join(output_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"\n任务2完成: 已在 '{output_dir}' 目录中创建 {files_created} 个文件")
    print(f"处理完成！总共处理了 {len(data)} 条帖子")

    # 显示统计信息
    print("\n统计信息:")
    print(f"  有效月份数: {len(monthly_data)}")
    for month in sorted(monthly_data.keys()):
        print(f"    {month}: {len(monthly_data[month])} 条")
    print(f"  日期未知: {len(unknown_posts)} 条")
    print(f"  日期错误: {len(error_posts)} 条")

    return True


def main():
    """主函数"""
    print("帖子数据处理工具")
    print("=" * 50)

    # 询问用户输入文件
    input_file = input("请输入JSON文件完整路径（或按Enter退出）: ").strip()
    if not input_file:
        print("已退出")
        return

    # 尝试处理文件
    success = process_data_file(input_file)

    if not success:
        print("\n处理失败，请检查：")
        print("1. 文件路径是否正确")
        print("2. 文件是否是有效的JSON格式")
        print("3. 文件是否包含中文字符（尝试使用英文路径）")

        # 提供简单的路径检查
        if '"' in input_file or "'" in input_file:
            print("\n注意: 您输入的路径包含引号，已自动处理")

        # 让用户重试
        retry = input("\n是否重新输入文件路径？(y/n): ").strip().lower()
        if retry == 'y':
            main()


if __name__ == "__main__":
    main()
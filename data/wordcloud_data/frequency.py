import json
import os
import re
from collections import defaultdict


def load_vocabulary(vocab_file):
    """加载词典"""
    with open(vocab_file, 'r', encoding='utf-8') as f:
        vocabulary = json.load(f)
    print(f"加载词典成功，包含 {len(vocabulary)} 个词汇")
    return vocabulary


def count_word_frequency(text, vocabulary):
    """
    统计文本中词典词汇的词频

    参数:
    text: 文本字符串
    vocabulary: 词汇列表

    返回:
    词频字典
    """
    if not text or not isinstance(text, str):
        return {word: 0 for word in vocabulary}

    # 将文本转换为小写
    text_lower = text.lower()

    # 创建词频字典，初始化为0
    word_freq = {word: 0 for word in vocabulary}

    # 对每个词汇进行计数
    for word in vocabulary:
        if not word or not isinstance(word, str):
            continue

        # 使用正则表达式进行单词边界匹配
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        matches = re.findall(pattern, text_lower)
        word_freq[word] = len(matches)

    return word_freq


def process_json_files(vocabulary, input_folder, output_folder):
    """
    处理所有JSON文件，统计词频

    参数:
    vocabulary: 词汇列表
    input_folder: 输入文件夹路径
    output_folder: 输出文件夹路径
    """
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)

    # 获取所有JSON文件
    json_files = []
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.json'):
            json_files.append(file_name)

    print(f"找到 {len(json_files)} 个JSON文件")

    processed_count = 0

    for file_name in json_files:
        input_path = os.path.join(input_folder, file_name)

        try:
            # 读取JSON文件
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"处理文件: {file_name}")

            # 提取articles字段
            articles_text = ""

            # 检查数据结构类型
            if isinstance(data, list):
                # 如果是列表，遍历每个元素
                for item in data:
                    if isinstance(item, dict) and 'articles' in item:
                        article = item.get('articles', '')
                        if article and isinstance(article, str):
                            articles_text += article + " "
            elif isinstance(data, dict):
                # 如果是字典，直接获取articles字段
                if 'articles' in data:
                    article = data.get('articles', '')
                    if article and isinstance(article, str):
                        articles_text = article
                elif 'data' in data and isinstance(data['data'], list):
                    # 尝试从data字段中提取
                    for item in data['data']:
                        if isinstance(item, dict) and 'articles' in item:
                            article = item.get('articles', '')
                            if article and isinstance(article, str):
                                articles_text += article + " "

            # 统计词频
            word_frequencies = count_word_frequency(articles_text, vocabulary)

            # 添加元数据
            result = {
                'filename': file_name,
                'total_words_in_articles': len(articles_text.split()),
                'vocabulary_size': len(vocabulary),
                'word_frequencies': word_frequencies
            }

            # 生成输出文件名
            base_name = os.path.splitext(file_name)[0]
            output_filename = f"{base_name}_word_freq.json"
            output_path = os.path.join(output_folder, output_filename)

            # 保存结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"  已保存到: {output_filename}")
            processed_count += 1

        except Exception as e:
            print(f"处理文件 {file_name} 时出错: {e}")

    print(f"\n处理完成! 成功处理 {processed_count} 个文件")
    return processed_count


def clean_path(path):
    """清理路径，去除可能的引号"""
    path = path.strip()
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]
    return path


def main():
    """主函数"""
    print("词频统计工具")
    print("=" * 50)

    # 输入词典文件路径
    vocab_file = input("请输入词典JSON文件路径: ").strip()
    vocab_file = clean_path(vocab_file)

    if not os.path.exists(vocab_file):
        print(f"错误: 词典文件 '{vocab_file}' 不存在")
        return

    # 加载词典
    try:
        vocabulary = load_vocabulary(vocab_file)
    except Exception as e:
        print(f"加载词典失败: {e}")
        return

    # 输入JSON文件夹路径
    input_folder = input("请输入JSON文件夹路径: ").strip()
    input_folder = clean_path(input_folder)

    if not os.path.exists(input_folder):
        print(f"错误: 文件夹 '{input_folder}' 不存在")
        return

    # 输出文件夹路径
    output_folder = input("请输入输出文件夹路径（默认: word_frequencies）: ").strip()
    if not output_folder:
        output_folder = "word_frequencies"

    print(f"\n开始处理...")
    print(f"词典文件: {vocab_file}")
    print(f"输入文件夹: {input_folder}")
    print(f"输出文件夹: {output_folder}")
    print("-" * 50)

    # 处理所有文件
    processed_count = process_json_files(vocabulary, input_folder, output_folder)

    # 生成汇总报告
    if processed_count > 0:
        generate_summary(vocab_file, input_folder, output_folder)

    print("\n所有操作完成!")


def generate_summary(vocab_file, input_folder, output_folder):
    """生成汇总报告"""
    summary_file = os.path.join(output_folder, "summary.txt")

    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("词频统计汇总报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"词典文件: {vocab_file}\n")
        f.write(f"输入文件夹: {input_folder}\n")
        f.write(f"输出文件夹: {output_folder}\n")
        f.write(f"生成时间: {get_current_time()}\n\n")

        # 统计输出文件
        output_files = []
        for file_name in os.listdir(output_folder):
            if file_name.endswith('_word_freq.json'):
                output_files.append(file_name)

        f.write(f"共生成 {len(output_files)} 个词频统计文件:\n")
        for file_name in sorted(output_files):
            f.write(f"  - {file_name}\n")

    print(f"汇总报告已保存到: {summary_file}")


def get_current_time():
    """获取当前时间字符串"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def test_simple():
    """简单测试版本"""
    # 这里是一个更简单的版本，不需要用户交互
    vocab_file = "vocabulary.json"  # 词典文件路径
    input_folder = "monthly_posts"  # JSON文件夹路径
    output_folder = "word_frequencies"  # 输出文件夹路径

    print("开始词频统计...")

    # 加载词典
    vocabulary = load_vocabulary(vocab_file)

    # 处理文件
    process_json_files(vocabulary, input_folder, output_folder)

    print("统计完成!")


if __name__ == "__main__":
    # 使用完整交互版本
    main()

    # 或者使用简单测试版本（取消下面的注释）
    # test_simple()
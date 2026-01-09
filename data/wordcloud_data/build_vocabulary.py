import json
import os


def extract_vocabulary_simple(folder_path):
    """
    简化版：从所有JSON文件中提取所有topic_words并构建词典

    参数:
    folder_path: 包含JSON文件的文件夹路径

    返回:
    词汇列表（去重后的词典）
    """
    # 使用集合来自动去重
    vocabulary_set = set()

    # 遍历文件夹中的所有JSON文件
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.json'):
            file_path = os.path.join(folder_path, file_name)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 提取所有主题词
                topics = data.get('topics', [])
                for topic in topics:
                    topic_words = topic.get('topic_words', [])
                    for word in topic_words:
                        # 确保不是空字符串
                        if word and isinstance(word, str):
                            vocabulary_set.add(word)

            except Exception as e:
                print(f"处理文件 {file_name} 时出错: {e}")
                continue

    # 将集合转换为列表
    vocabulary_list = list(vocabulary_set)

    return vocabulary_list


def save_vocabulary_simple(vocabulary_list, output_file):
    """
    保存词典到JSON文件
    """
    # 按字母顺序排序（可选，如果需要）
    vocabulary_list.sort()

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vocabulary_list, f, indent=2, ensure_ascii=False)

    print(f"词典已保存到: {output_file}")
    print(f"词典包含 {len(vocabulary_list)} 个词汇")


def main_simple():
    """主函数 - 简化版"""
    print("词汇词典构建工具")
    print("=" * 50)

    # 输入文件夹路径
    folder_path = input("请输入包含JSON文件的文件夹路径: ").strip()

    # 清理路径（去掉可能的引号）
    folder_path = folder_path.strip('"\'')

    if not os.path.exists(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        return

    # 提取词汇
    print("\n正在提取词汇...")
    vocabulary_list = extract_vocabulary_simple(folder_path)

    if not vocabulary_list:
        print("错误: 未提取到任何词汇")
        return

    print(f"提取到 {len(vocabulary_list)} 个词汇")

    # 保存词典
    output_file = "vocabulary.json"
    save_vocabulary_simple(vocabulary_list, output_file)

    print("\n处理完成!")


# 运行主函数
if __name__ == "__main__":
    main_simple()
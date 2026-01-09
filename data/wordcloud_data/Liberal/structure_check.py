import json
import os

# 参考文件路径（2011-02.json）
REFERENCE_FILE = "2011-02.json"

def get_json_structure(file_path):
    """
    读取JSON文件并提取其键结构（递归处理嵌套字典）
    返回结构化的键列表，例如：['month', 'total_articles', 'deep_topics_summary[0].topic_id', ...]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 递归提取键路径
        def extract_keys(obj, parent_path=""):
            keys = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    current_path = f"{parent_path}.{k}" if parent_path else k
                    keys.append(current_path)
                    keys.extend(extract_keys(v, current_path))
            elif isinstance(obj, list) and obj:
                # 假设列表中第一个元素的结构代表整个列表的结构
                first_item = obj[0]
                current_path = f"{parent_path}[0]"
                keys.extend(extract_keys(first_item, current_path))
            return keys
        
        return sorted(extract_keys(data))
    
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return None

def main():
    # 获取参考文件的键结构
    reference_structure = get_json_structure(REFERENCE_FILE)
    if reference_structure is None:
        print("无法读取参考文件，程序退出")
        return
    
    print(f"参考文件 {REFERENCE_FILE} 的键结构已加载")
    print("=" * 50)
    
    # 遍历当前目录下的所有JSON文件
    for filename in os.listdir("."):
        if filename.endswith(".json") and filename != REFERENCE_FILE:
            file_path = os.path.join(".", filename)
            file_structure = get_json_structure(file_path)
            
            if file_structure is None:
                continue
            
            # 对比键结构
            if file_structure != reference_structure:
                print(f"⚠️  文件 {filename} 键结构与参考文件不同")
                
                # 可选：输出具体差异
                reference_set = set(reference_structure)
                file_set = set(file_structure)
                missing_keys = reference_set - file_set
                extra_keys = file_set - reference_set
                
                if missing_keys:
                    print(f"  - 缺失的键: {sorted(missing_keys)}")
                if extra_keys:
                    print(f"  - 多余的键: {sorted(extra_keys)}")
                print("-" * 30)
    
    print("✅ 检查完成")

if __name__ == "__main__":
    main()
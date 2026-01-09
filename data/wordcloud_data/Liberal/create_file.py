import os

# 定义基础年份和文件扩展名
base_year = 2020
file_ext = ".json"

# 循环生成1-12月的文件
for month in range(1, 13):  # range(1,13) 会生成 1,2,...,12
    # 将月份格式化为两位数（01, 02, ..., 12）
    month_str = f"{month:02d}"
    # 拼接文件名
    filename = f"{base_year}-{month_str}{file_ext}"
    
    # 在当前目录创建空文件
    try:
        # 使用with语句自动管理文件句柄，确保文件正确创建和关闭
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入空内容（创建空文件），也可以根据需要写入初始内容如 {}
            pass
        print(f"成功创建文件: {filename}")
    except Exception as e:
        print(f"创建文件 {filename} 失败: {e}")
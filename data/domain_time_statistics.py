import json
import os
from datetime import datetime, timezone
from collections import defaultdict, Counter

def process_reddit_data(input_json_path):
    """
    
    参数:
        input_json_path (str): 输入JSON文件路径（保守派/自由派数据）
    """
    # ===================== 步骤1：读取并校验数据 =====================
    if not os.path.exists(input_json_path):
        print(f"错误：输入文件 {input_json_path} 不存在！")
        return
    
    # 提取输入文件名（不含路径和后缀），用于拼接输出文件名
    input_file_name = os.path.basename(input_json_path)
    input_file_prefix = os.path.splitext(input_file_name)[0]
    
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list) or len(data) == 0:
            print("错误：JSON文件内容不是非空数组格式！")
            return
        total_posts = len(data)  # 总发帖数（分母）
        print(f"成功读取数据，总条目数：{total_posts}")
    
    except json.JSONDecodeError:
        print("错误：JSON文件格式无效，请检查！")
        return
    except Exception as e:
        print(f"读取数据出错：{str(e)}")
        return

    # ===================== 步骤2：时间维度统计 =====================
    # 初始化时间统计字典：{年份: {月份: {发帖量, 点赞数, 评论数}}}
    time_stats = defaultdict(lambda: defaultdict(lambda: {
        "post_count": 0,
        "total_upvotes": 0,
        "total_comments": 0
    }))

    # 初始化域名统计计数器
    domain_counter = Counter()

    # 遍历每条数据处理
    for idx, item in enumerate(data):
        # 处理时间戳
        created_utc = item.get("created_utc")
        if not isinstance(created_utc, (int, float)):
            print(f"警告：第 {idx+1} 条数据created_utc无效，跳过")
            continue
        
        # 转换UTC时间戳为年月日（兼容秒级/毫秒级）
        try:
            ts = created_utc / 1000 if created_utc > 1e12 else created_utc
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            year = dt.year
            month = dt.month
        except ValueError as e:
            print(f"警告：第 {idx+1} 条数据时间戳无效（{created_utc}），跳过：{str(e)}")
            continue
        except Exception as e:
            print(f"警告：第 {idx+1} 条数据时间转换失败，跳过：{str(e)}")
            continue
        
        # 提取点赞数和评论数（默认0）
        upvotes = item.get("num_upvotes", 0)
        comments = item.get("num_comments", 0)
        upvotes = upvotes if isinstance(upvotes, (int, float)) else 0
        comments = comments if isinstance(comments, (int, float)) else 0

        # 更新时间统计
        time_stats[year][month]["post_count"] += 1
        time_stats[year][month]["total_upvotes"] += upvotes
        time_stats[year][month]["total_comments"] += comments

        # 更新域名统计（过滤空值/无效值）
        domain = item.get("url_domain", "").strip()
        if domain and domain not in ["null", "undefined"]:
            domain_counter[domain] += 1

    # ===================== 步骤3：整理时间统计结果 =====================
    # 格式化时间统计结果（按年月升序排序）
    time_result = {}
    for year in sorted(time_stats.keys()):
        time_result[str(year)] = {}
        for month in sorted(time_stats[year].keys()):
            month_data = time_stats[year][month]
            time_result[str(year)][str(month)] = {
                "post_count": month_data["post_count"],
                "total_upvotes": int(month_data["total_upvotes"]),
                "total_comments": int(month_data["total_comments"]),
                "date_format_example": f"{year}-{month:02d}-01"
            }

    # 保存时间统计结果
    time_output_path = f"time_statistics_{input_file_prefix}.json"
    with open(time_output_path, 'w', encoding='utf-8') as f:
        json.dump(time_result, f, indent=4, ensure_ascii=False)
    print(f"\n✅ 时间统计结果已保存至：{time_output_path}")

    # ===================== 步骤4：整理域名统计结果（新增占比逻辑） =====================
    # 按发帖量降序排序
    sorted_domains = domain_counter.most_common()
    total_valid_domain_posts = sum(domain_counter.values())  # 有有效域名的发帖数
    # 总发帖数可能包含无域名的情况，占比分母用总发帖数total_posts
    total_posts_denominator = total_posts

    # -------------------- 4.1 Top5 域名统计（含占比） --------------------
    top5_domains = []
    top5_total = 0
    for d, c in sorted_domains[:5]:
        ratio = round((c / total_posts_denominator) * 100, 4)  # 保留4位小数
        top5_domains.append({
            "domain": d,
            "post_count": c,
            "post_ratio(%)": ratio  # 占总发帖数的百分比
        })
        top5_total += c

    # 计算Top5之外的域名统计
    other_than_top5_count = total_valid_domain_posts - top5_total
    other_than_top5_ratio = round((other_than_top5_count / total_posts_denominator) * 100, 4)
    # 补充无域名的发帖数和占比（总发帖数 - 有有效域名的发帖数）
    no_domain_count = total_posts_denominator - total_valid_domain_posts
    no_domain_ratio = round((no_domain_count / total_posts_denominator) * 100, 4)

    top5_result = {
        "top5_domains": top5_domains,
        "top5_total_posts": top5_total,
        "top5_total_ratio(%)": round((top5_total / total_posts_denominator) * 100, 4),
        "other_than_top5": {
            "post_count": other_than_top5_count,
            "post_ratio(%)": other_than_top5_ratio
        },
        "no_domain_posts": {  # 无有效域名的发帖数
            "post_count": no_domain_count,
            "post_ratio(%)": no_domain_ratio
        },
        "total_posts": total_posts_denominator,  # 总发帖数（分母）
        "total_valid_domain_posts": total_valid_domain_posts  # 有有效域名的发帖数
    }

    # 保存Top5域名结果（含占比）
    top5_path = f"top5_domains_{input_file_prefix}.json"
    with open(top5_path, 'w', encoding='utf-8') as f:
        json.dump(top5_result, f, indent=4, ensure_ascii=False)
    print(f"✅ Top5 域名统计（含占比）已保存至：{top5_path}")

    # -------------------- 4.2 Top10 域名统计（含占比） --------------------
    top10_domains = []
    top10_total = 0
    for d, c in sorted_domains[:10]:
        ratio = round((c / total_posts_denominator) * 100, 4)
        top10_domains.append({
            "domain": d,
            "post_count": c,
            "post_ratio(%)": ratio
        })
        top10_total += c

    # 计算Top10之外的域名统计
    other_than_top10_count = total_valid_domain_posts - top10_total
    other_than_top10_ratio = round((other_than_top10_count / total_posts_denominator) * 100, 4)

    top10_result = {
        "top10_domains": top10_domains,
        "top10_total_posts": top10_total,
        "top10_total_ratio(%)": round((top10_total / total_posts_denominator) * 100, 4),
        "other_than_top10": {
            "post_count": other_than_top10_count,
            "post_ratio(%)": other_than_top10_ratio
        },
        "no_domain_posts": {
            "post_count": no_domain_count,
            "post_ratio(%)": no_domain_ratio
        },
        "total_posts": total_posts_denominator,
        "total_valid_domain_posts": total_valid_domain_posts
    }

    # 保存Top10域名结果（含占比）
    top10_path = f"top10_domains_{input_file_prefix}.json"
    with open(top10_path, 'w', encoding='utf-8') as f:
        json.dump(top10_result, f, indent=4, ensure_ascii=False)
    print(f"✅ Top10 域名统计（含占比）已保存至：{top10_path}")

    # ===================== 输出统计摘要 =====================
    print("\n📊 统计摘要：")
    if time_stats:
        print(f"- 时间覆盖范围：{min(time_stats.keys())} ~ {max(time_stats.keys())}")
    print(f"- 总发帖数：{total_posts_denominator}")
    print(f"- 有有效域名的发帖数：{total_valid_domain_posts}（占比 {round((total_valid_domain_posts/total_posts_denominator)*100,4)}%）")
    print(f"- 无有效域名的发帖数：{no_domain_count}（占比 {no_domain_ratio}%）")
    print(f"- 发帖量最高域名：{sorted_domains[0][0]}（{sorted_domains[0][1]} 条，占比 {round((sorted_domains[0][1]/total_posts_denominator)*100,4)}%）")

# ===================== 主程序入口 =====================
if __name__ == "__main__":
    INPUT_FILE = "conservative.json"
    
    # 执行数据处理
    process_reddit_data(INPUT_FILE)
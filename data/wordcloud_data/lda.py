import json
import os
import re
import numpy as np
from collections import defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import warnings

warnings.filterwarnings('ignore')


class TextPreprocessor:
    """文本预处理类"""

    def __init__(self):
        # 检查并设置NLTK数据路径
        nltk_data_path = self.get_nltk_data_path()
        if nltk_data_path:
            nltk.data.path.append(nltk_data_path)

        # 加载停用词
        try:
            self.stop_words = set(stopwords.words('english'))
            # 测试分词器是否可用
            test_text = "This is a test"
            word_tokenize(test_text)
        except LookupError:
            print("警告: NLTK数据未找到，请确保已下载")
            print("可以手动下载或运行: nltk.download(['punkt', 'stopwords', 'wordnet'])")
            self.stop_words = set(self.get_basic_stopwords())

        # 词形还原器
        try:
            self.lemmatizer = WordNetLemmatizer()
        except:
            # 如果WordNet不可用，创建一个简单的替代
            class SimpleLemmatizer:
                def lemmatize(self, word):
                    return word

            self.lemmatizer = SimpleLemmatizer()

        # 添加自定义停用词
        self.stop_words.update([
            'http', 'https', 'com', 'www', 'html', 'like', 'would', 'could',
            'should', 'might', 'may', 'also', 'get', 'one', 'two', 'three',
            'first', 'second', 'third', 'new', 'said', 'say', 'says', 'just',
            'know', 'think', 'going', 'go', 'see', 'make', 'take', 'use',
            'want', 'need', 'look', 'good', 'bad', 'better', 'worse', 'really',
            'much', 'many', 'lot', 'lots', 'thing', 'things', 'way', 'ways',
            'time', 'times', 'people', 'person', 'year', 'years', 'day', 'days',
            'even', 'still', 'well', 'back', 'right', 'left', 'yes', 'no',
            'dont', 'doesnt', 'didnt', 'isnt', 'arent', 'wasnt', 'werent',
            'cant', 'cannot', 'couldnt', 'shouldnt', 'wont', 'wouldnt',
            'might', 'must', 'shall', 'mightnt', 'mustnt', 'neednt',
            'let', 'lets', 'perhaps', 'maybe', 'probably', 'possibly',
            'actually', 'basically', 'essentially', 'literally', 'virtually',
            'generally', 'usually', 'often', 'sometimes', 'never', 'always',
            'almost', 'nearly', 'quite', 'rather', 'somewhat', 'somehow'
        ])

    def get_nltk_data_path(self):
        """获取NLTK数据路径"""
        # 常见的NLTK数据路径
        possible_paths = [
            os.path.expanduser("~/nltk_data"),  # Linux/Mac
            os.path.expanduser("~/.local/share/nltk_data"),  # Linux
            os.path.expanduser("~/AppData/Roaming/nltk_data"),  # Windows
            os.path.expanduser("~/AppData/Local/nltk_data"),  # Windows
            "C:/nltk_data",  # Windows自定义
            "D:/nltk_data",  # Windows自定义
            "E:/nltk_data",  # Windows自定义
            "/usr/share/nltk_data",  # Linux系统
            "/usr/local/share/nltk_data",  # Linux系统
            "/opt/nltk_data",  # Linux系统
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"找到NLTK数据路径: {path}")
                return path

        print("未找到NLTK数据路径，将使用基础功能")
        return None

    def get_basic_stopwords(self):
        """获取基础停用词列表（当NLTK不可用时）"""
        basic_stopwords = [
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so',
            'than', 'such', 'both', 'through', 'about', 'for', 'is', 'of',
            'while', 'during', 'to', 'from', 'in', 'out', 'on', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there',
            'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        ]
        return basic_stopwords

    def preprocess(self, text):
        """预处理文本"""
        if not isinstance(text, str):
            return ""

        # 转换为小写
        text = text.lower()

        # 移除URL
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

        # 移除特殊字符和数字（保留字母和空格）
        text = re.sub(r'[^a-zA-Z\s]', ' ', text)

        # 分词（如果word_tokenize不可用，使用简单分词）
        try:
            tokens = word_tokenize(text)
        except:
            tokens = text.split()

        # 移除停用词和短词
        tokens = [word for word in tokens if word not in self.stop_words and len(word) > 2]

        # 词形还原
        tokens = [self.lemmatizer.lemmatize(word) for word in tokens]

        return ' '.join(tokens)


class LDATopicModeler:
    """LDA主题建模类"""

    def __init__(self, n_topics=5, max_features=1000, random_state=42):
        self.n_topics = n_topics
        self.max_features = max_features
        self.random_state = random_state
        self.preprocessor = TextPreprocessor()
        self.vectorizer = None
        self.lda_model = None

    def fit(self, documents):
        """训练LDA模型"""
        # 预处理文档
        processed_docs = [self.preprocessor.preprocess(doc) for doc in documents]

        # 创建文档-词矩阵
        self.vectorizer = CountVectorizer(
            max_features=self.max_features,
            stop_words='english',
            min_df=2,  # 最小文档频率
            max_df=0.95  # 最大文档频率（避免常见词）
        )

        doc_term_matrix = self.vectorizer.fit_transform(processed_docs)

        # 训练LDA模型
        self.lda_model = LatentDirichletAllocation(
            n_components=self.n_topics,
            random_state=self.random_state,
            learning_method='online',
            max_iter=20
        )

        self.lda_model.fit(doc_term_matrix)

        return self.lda_model, self.vectorizer

    def get_topics(self, top_n=10):
        """获取每个主题的top词"""
        if self.lda_model is None or self.vectorizer is None:
            raise ValueError("模型尚未训练，请先调用fit方法")

        feature_names = self.vectorizer.get_feature_names_out()

        topics = []
        for topic_idx, topic in enumerate(self.lda_model.components_):
            top_indices = topic.argsort()[:-top_n - 1:-1]
            top_words = [feature_names[i] for i in top_indices]
            topics.append({
                'topic_id': topic_idx,
                'topic_words': top_words,
                'topic_weights': topic[top_indices].tolist()
            })

        return topics

    def predict_topics(self, documents):
        """预测文档的主题分布"""
        if self.lda_model is None or self.vectorizer is None:
            raise ValueError("模型尚未训练，请先调用fit方法")

        processed_docs = [self.preprocessor.preprocess(doc) for doc in documents]
        doc_term_matrix = self.vectorizer.transform(processed_docs)
        topic_distributions = self.lda_model.transform(doc_term_matrix)

        return topic_distributions


def analyze_monthly_topics(monthly_dir, output_dir="monthly_topics", n_topics=5):
    """分析每个月的主题"""

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 获取所有月份文件
    month_files = []
    for file in os.listdir(monthly_dir):
        if file.endswith('.json') and not file.startswith('index') and not 'unknown' in file and not 'error' in file:
            month_files.append(file)

    print(f"找到 {len(month_files)} 个月份的文件")

    all_results = {}

    for month_file in month_files:
        month_name = month_file.replace('.json', '')
        print(f"\n处理 {month_name}...")

        # 读取月份数据
        file_path = os.path.join(monthly_dir, month_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            month_data = json.load(f)

        # 提取文章内容
        articles = []
        article_metadata = []

        for i, item in enumerate(month_data):
            article_text = item.get('articles', '')
            if article_text and len(str(article_text).strip()) > 100:  # 只处理长度大于100字符的文章
                articles.append(str(article_text))
                article_metadata.append({
                    'index': i,
                    'url': item.get('urls', ''),
                    'date': item.get('created_date', ''),
                    'upvotes': item.get('num_upvotes', 0)
                })

        if len(articles) < 10:  # 如果文章太少，跳过
            print(f"  {month_name} 只有 {len(articles)} 篇文章，跳过主题分析")
            continue

        print(f"  处理 {len(articles)} 篇文章...")

        try:
            # 训练LDA模型
            modeler = LDATopicModeler(n_topics=n_topics, max_features=800)
            lda_model, vectorizer = modeler.fit(articles)

            # 获取主题词
            topics = modeler.get_topics(top_n=15)

            # 预测每篇文章的主题分布
            topic_distributions = modeler.predict_topics(articles)

            # 为每篇文章分配主要主题
            for i, metadata in enumerate(article_metadata):
                if i < len(topic_distributions):
                    main_topic = int(np.argmax(topic_distributions[i]))
                    metadata['main_topic'] = main_topic
                    metadata['topic_distribution'] = topic_distributions[i].tolist()

            # 统计主题分布
            topic_counts = defaultdict(int)
            for metadata in article_metadata:
                if 'main_topic' in metadata:
                    topic_counts[metadata['main_topic']] += 1

            # 准备结果
            month_result = {
                'month': month_name,
                'total_articles': len(articles),
                'topics': topics,
                'topic_distribution': dict(topic_counts),
                'sample_articles_by_topic': {}
            }

            # 为每个主题收集示例文章
            for topic in topics:
                topic_id = topic['topic_id']
                # 找到属于这个主题的前3篇文章
                topic_articles = []
                for metadata in article_metadata:
                    if metadata.get('main_topic') == topic_id and len(topic_articles) < 3:
                        # 获取文章片段（前200字符）
                        article_idx = metadata['index']
                        if article_idx < len(articles):
                            article_preview = articles[article_idx][:200] + "..."
                            topic_articles.append({
                                'preview': article_preview,
                                'upvotes': metadata['upvotes'],
                                'url': metadata['url']
                            })

                month_result['sample_articles_by_topic'][topic_id] = topic_articles

            # 保存月份结果
            output_file = os.path.join(output_dir, f"{month_name}_topics.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(month_result, f, indent=2, ensure_ascii=False)

            print(f"  已保存主题分析结果到 {output_file}")

            # 添加到总结果
            all_results[month_name] = {
                'total_articles': len(articles),
                'topic_summary': [
                    {
                        'topic_id': topic['topic_id'],
                        'top_words': topic['topic_words'][:5],  # 只取前5个词作为摘要
                        'article_count': topic_counts.get(topic['topic_id'], 0)
                    }
                    for topic in topics
                ]
            }

        except Exception as e:
            print(f"  处理 {month_name} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # 保存汇总结果
    summary_file = os.path.join(output_dir, "topics_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n所有月份的主题分析完成！")
    print(f"详细结果保存在: {output_dir}")
    print(f"汇总结果保存在: {summary_file}")

    # 生成可视化摘要
    generate_topic_summary(all_results, output_dir)

    return all_results


def generate_topic_summary(all_results, output_dir):
    """生成主题分析摘要"""

    summary_lines = []
    summary_lines.append("=" * 60)
    summary_lines.append("LDA主题分析汇总报告")
    summary_lines.append("=" * 60)
    summary_lines.append("")

    for month, data in sorted(all_results.items()):
        summary_lines.append(f"月份: {month}")
        summary_lines.append(f"文章总数: {data['total_articles']}")
        summary_lines.append("主题摘要:")

        for topic in data['topic_summary']:
            words_str = ", ".join(topic['top_words'])
            summary_lines.append(f"  主题 {topic['topic_id']}: {words_str} ({topic['article_count']}篇文章)")

        summary_lines.append("-" * 40)

    # 保存为文本文件
    summary_text = "\n".join(summary_lines)
    text_file = os.path.join(output_dir, "topics_report.txt")
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(summary_text)

    # 打印摘要
    print("\n" + summary_text)

    return summary_text


def clean_path(path):
    """清理路径，去除可能的引号"""
    path = path.strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    elif path.startswith("'") and path.endswith("'"):
        path = path[1:-1]
    return path


def main():
    """主函数"""
    print("Reddit帖子LDA主题分析工具")
    print("=" * 60)

    # 输入月份数据目录
    monthly_dir = input("请输入月份JSON文件目录: ").strip()
    if not monthly_dir:
        print("错误: 必须输入目录路径")
        return

    # 清理路径
    monthly_dir = clean_path(monthly_dir)

    if not os.path.exists(monthly_dir):
        print(f"错误: 目录 '{monthly_dir}' 不存在")
        print(f"当前工作目录: {os.getcwd()}")
        # 显示当前目录下的文件和文件夹
        print("\n当前目录内容:")
        for item in os.listdir('.'):
            if os.path.isdir(item):
                print(f"  [目录] {item}")
            else:
                print(f"  [文件] {item}")
        return

    # 设置主题数量
    try:
        n_topics_input = input("请输入要提取的主题数量（默认5）: ").strip()
        n_topics = int(n_topics_input) if n_topics_input else 5
    except ValueError:
        n_topics = 5
        print(f"输入无效，使用默认主题数量: {n_topics}")

    print(f"\n开始分析目录: {monthly_dir}")
    print(f"主题数量: {n_topics}")

    # 分析主题
    monthly_topics_dir = "monthly_topics"
    results = analyze_monthly_topics(monthly_dir, monthly_topics_dir, n_topics)

    print("\n分析完成！")


if __name__ == "__main__":
    main()
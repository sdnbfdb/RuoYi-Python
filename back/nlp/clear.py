import re
import string

class TextCleaner:
    """
    文本清理工具类 - 提供多种正则表达式清理方法
    """
    
    @staticmethod
    def remove_html_tags(text):
        """去除 HTML 标签"""
        pattern = r'<[^>]+>'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_special_chars(text):
        """去除特殊字符（保留中文、英文、数字、空格）"""
        pattern = r'[^\u4e00-\u9fa5a-zA-Z0-9\s]'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_extra_spaces(text):
        """去除多余空格（多个空格合并为一个）"""
        # 去除首尾空格
        text = text.strip()
        # 多个空格合并为一个
        pattern = r'\s+'
        return re.sub(pattern, ' ', text)
    
    @staticmethod
    def remove_punctuation(text):
        """去除标点符号"""
        punctuation = string.punctuation + '，。！？；：、（）【】《》‘’“”·…—'
        pattern = r'[' + re.escape(punctuation) + r']'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_numbers(text):
        """去除数字"""
        pattern = r'\d+'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_urls(text):
        """去除 URL 链接"""
        pattern = r'https?://[\w\-._~:/?#[\]@!$&\'()*+,;=%]+'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_emails(text):
        """去除邮箱地址"""
        pattern = r'[\w.-]+@[\w.-]+\.\w+'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_phone_numbers(text):
        """去除手机号码"""
        pattern = r'1[3-9]\d{9}'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def remove_chinese_punctuation(text):
        """去除中文标点符号"""
        pattern = r'[，。！？；：、（）【】《》‘’“”·…—～·]'
        return re.sub(pattern, '', text)
    
    @staticmethod
    def clean_text(text, remove_num=False, remove_punc=False, remove_html=True):
        """
        综合清理文本
        :param text: 原始文本
        :param remove_num: 是否去除数字
        :param remove_punc: 是否去除标点
        :param remove_html: 是否去除HTML标签
        :return: 清理后的文本
        """
        if remove_html:
            text = TextCleaner.remove_html_tags(text)
        
        if remove_num:
            text = TextCleaner.remove_numbers(text)
        
        if remove_punc:
            text = TextCleaner.remove_punctuation(text)
        
        text = TextCleaner.remove_extra_spaces(text)
        
        return text
    
    @staticmethod
    def extract_chinese(text):
        """提取中文内容"""
        pattern = r'[\u4e00-\u9fa5]+'
        return ''.join(re.findall(pattern, text))
    
    @staticmethod
    def extract_words(text):
        """提取英文单词"""
        pattern = r'[a-zA-Z]+'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_numbers(text):
        """提取数字"""
        pattern = r'\d+'
        return re.findall(pattern, text)
    
    @staticmethod
    def split_sentences(text):
        """按中文句号、问号、感叹号分割句子"""
        pattern = r'([。！？])'
        parts = re.split(pattern, text)
        sentences = []
        for i in range(0, len(parts)-1, 2):
            sentences.append(parts[i] + parts[i+1])
        return sentences
    
    @staticmethod
    def extract_knowledge_content(text):
        """
        从知识库文档中提取文件内容部分
        去掉基本信息、描述、附件元信息等，只保留文件实际内容
        """
        pattern = r'- 文件内容:\s*\n\s*={20,}\n([\s\S]*?)\s*={20,}'
        match = re.search(pattern, text)

        if match:
            content = match.group(1).strip()
            content = re.sub(r'^\s{6}', '', content, flags=re.MULTILINE)
            return content
        return ''
    
    @staticmethod
    def clean_knowledge_text(text):
        """
        清理知识库文本：提取内容 + 去除多余标点 + 格式化
        """
        # 1. 提取文件内容部分
        content = TextCleaner.extract_knowledge_content(text)
        
        if not content:
            # 如果没有找到文件内容部分，返回清理后的原文本
            content = TextCleaner.clean_text(text)
        
        # 2. 去除多余的标点符号（保留必要的）
        # 保留：。！？；：、（）【】《》
        # 去除：重复的标点、特殊符号等
        content = re.sub(r'。{2,}', '。', content)
        content = re.sub(r'！{2,}', '！', content)
        content = re.sub(r'？{2,}', '？', content)
        content = re.sub(r'、{2,}', '、', content)
        content = re.sub(r'；{2,}', '；', content)
        content = re.sub(r'：{2,}', '：', content)
        
        # 3. 去除多余的空格和空行
        content = TextCleaner.remove_extra_spaces(content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 4. 去除 Markdown 格式符号（#、*、**等）但保留内容
        content = re.sub(r'^\s*#+\s*', '', content, flags=re.MULTILINE)  # 去除标题 #
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # 去除 **加粗**
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # 去除 *斜体*
        
        # 5. 去除多余的特殊符号
        content = re.sub(r'[●■◆▲▶★✓✕]', '', content)
        
        return content.strip()


# 示例用法
if __name__ == '__main__':
    sample_text = """
    <div class="content">
        这是一段测试文本，包含多种内容！
        电话号码：13812345678，邮箱：test@example.com
        网址：https://www.example.com/path?query=1
        数字：2024年，价格：¥999.00
        Hello World! 这是英文内容。
    </div>
    """
    
    print("=== 基础文本清理示例 ===")
    print("原始文本:")
    print(sample_text)
    print("\n" + "="*50 + "\n")
    
    print("1. 去除HTML标签:")
    print(TextCleaner.remove_html_tags(sample_text))
    print("\n" + "-"*50 + "\n")
    
    print("2. 综合清理:")
    print(TextCleaner.clean_text(sample_text, remove_num=True, remove_punc=True))
    print("\n" + "-"*50 + "\n")
    
    print("3. 提取中文:")
    print(TextCleaner.extract_chinese(sample_text))
    print("\n" + "-"*50 + "\n")
    
    print("4. 提取电话号码:")
    print(TextCleaner.extract_numbers(sample_text))
    print("\n" + "-"*50 + "\n")
    
    print("5. 分割句子:")
    sentences = TextCleaner.split_sentences("今天天气很好。你要去哪里？我要去公园！")
    for i, sent in enumerate(sentences, 1):
        print(f"句子{i}: {sent}")
    
    print("\n" + "="*60 + "\n")
    
    # 知识库文档清理示例
    print("=== 知识库文档清理示例 ===")
    import os
    
    # 读取知识库文档
    knowledge_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'knowledge', '31972024_猪肉做法大全.txt'
    )
    
    if os.path.exists(knowledge_file_path):
        with open(knowledge_file_path, 'r', encoding='utf-8') as f:
            knowledge_content = f.read()
        
        print(f"读取知识库文件: {knowledge_file_path}")
        print(f"原始文件大小: {len(knowledge_content)} 字符")
        print("\n" + "-"*60 + "\n")
        
        # 提取文件内容部分
        extracted = TextCleaner.extract_knowledge_content(knowledge_content)
        print("6. 提取文件内容部分:")
        print(f"提取内容大小: {len(extracted)} 字符")
        print("前500字符预览:")
        print(extracted[:500] + "..." if len(extracted) > 500 else extracted)
        print("\n" + "-"*60 + "\n")
        
        # 完整清理
        cleaned = TextCleaner.clean_knowledge_text(knowledge_content)
        print("7. 完整清理后的内容:")
        print(f"清理后大小: {len(cleaned)} 字符")
        print("前800字符预览:")
        print(cleaned[:800] + "..." if len(cleaned) > 800 else cleaned)
    else:
        print(f"知识库文件不存在: {knowledge_file_path}")

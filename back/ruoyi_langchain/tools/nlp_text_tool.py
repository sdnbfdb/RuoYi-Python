from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, List
from nlp.clear import TextCleaner
import re

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


class TextCleanInput(BaseModel):
    text: str = Field(description="需要清理的原始文本")
    remove_num: bool = Field(default=False, description="是否去除数字")
    remove_punc: bool = Field(default=False, description="是否去除标点")
    remove_html: bool = Field(default=True, description="是否去除HTML标签")


def clean_text(text: str, remove_num: bool = False, remove_punc: bool = False, remove_html: bool = True) -> str:
    cleaner = TextCleaner()
    cleaned = cleaner.clean_text(text, remove_num=remove_num, remove_punc=remove_punc, remove_html=remove_html)
    return f"清理后的文本（长度：{len(cleaned)}字符）:\n{cleaned[:2000]}{'...' if len(cleaned) > 2000 else ''}"


class TextExtractInput(BaseModel):
    text: str = Field(description="需要提取内容的文本")
    extract_type: str = Field(description="提取类型：chinese(中文), numbers(数字), emails(邮箱), phones(手机号), urls(网址)")


def extract_text(text: str, extract_type: str = "chinese") -> str:
    cleaner = TextCleaner()
    
    if extract_type == "chinese":
        result = cleaner.extract_chinese(text)
        return f"提取的中文内容（长度：{len(result)}字符）:\n{result[:2000]}{'...' if len(result) > 2000 else ''}"
    elif extract_type == "numbers":
        result = cleaner.extract_numbers(text)
        return f"提取的数字列表（共{len(result)}个）:\n{', '.join(result[:50])}{'...' if len(result) > 50 else ''}"
    elif extract_type == "emails":
        emails = re.findall(r'[\w.-]+@[\w.-]+\.\w+', text)
        return f"提取的邮箱列表（共{len(emails)}个）:\n{', '.join(emails[:20])}{'...' if len(emails) > 20 else ''}"
    elif extract_type == "phones":
        phones = re.findall(r'1[3-9]\d{9}', text)
        return f"提取的手机号列表（共{len(phones)}个）:\n{', '.join(phones[:20])}{'...' if len(phones) > 20 else ''}"
    elif extract_type == "urls":
        urls = re.findall(r'https?://[\w\-._~:/?#[\]@!$&\'()*+,;=%]+', text)
        return f"提取的URL列表（共{len(urls)}个）:\n{', '.join(urls[:20])}{'...' if len(urls) > 20 else ''}"
    else:
        return f"不支持的提取类型: {extract_type}。支持的类型：chinese, numbers, emails, phones, urls"


class TextSplitInput(BaseModel):
    text: str = Field(description="需要分块的文本")
    max_size: int = Field(default=800, description="每个分块的最大字符数")
    overlap: int = Field(default=100, description="分块之间的重叠字符数")


def split_text_into_chunks(text: str, max_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> str:
    lines = text.split('\n')

    sections = []
    current_title = '概述'
    current_lines = []

    for line in lines:
        stripped = line.strip()
        h2_match = re.match(r'^##\s+(.+)', stripped)
        if h2_match:
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    sections.append({'section_title': current_title, 'content': content})
            current_title = h2_match.group(1).strip()
            current_lines = [stripped]
        elif stripped.startswith('# '):
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    sections.append({'section_title': current_title, 'content': content})
            current_title = stripped.lstrip('#').strip()
            current_lines = [stripped]
        else:
            current_lines.append(line)

    if current_lines:
        content = '\n'.join(current_lines).strip()
        if content:
            sections.append({'section_title': current_title, 'content': content})

    if not sections:
        sections.append({'section_title': '全文', 'content': text.strip()})

    chunks = []
    chunk_index = 0

    for section in sections:
        section_title = section['section_title']
        content = section['content']

        if len(content) <= max_size:
            chunks.append({
                'section_title': section_title,
                'content': content,
                'index': chunk_index
            })
            chunk_index += 1
        else:
            sentences = re.split(r'(?<=[。！？；])', content)
            sentences = [s for s in sentences if s.strip()]

            current_chunk = ''
            for sent in sentences:
                if len(current_chunk) + len(sent) > max_size and current_chunk:
                    chunks.append({
                        'section_title': section_title,
                        'content': current_chunk.strip(),
                        'index': chunk_index
                    })
                    chunk_index += 1
                    if overlap > 0 and len(current_chunk) > overlap:
                        current_chunk = current_chunk[-overlap:] + sent
                    else:
                        current_chunk = sent
                else:
                    current_chunk += sent

            if current_chunk.strip():
                chunks.append({
                    'section_title': section_title,
                    'content': current_chunk.strip(),
                    'index': chunk_index
                })
                chunk_index += 1

    result_lines = [f"文本已分成 {len(chunks)} 个分块："]
    for i, chunk in enumerate(chunks):
        preview = chunk['content'][:100] + '...' if len(chunk['content']) > 100 else chunk['content']
        result_lines.append(f"\n分块 {i+1}（章节: {chunk['section_title']}）:")
        result_lines.append(f"  长度: {len(chunk['content'])} 字符")
        result_lines.append(f"  预览: {preview}")

    return '\n'.join(result_lines)


class KnowledgeExtractInput(BaseModel):
    text: str = Field(description="知识库文档原始文本")


def extract_knowledge_content(text: str) -> str:
    cleaner = TextCleaner()
    extracted = cleaner.extract_knowledge_content(text)
    
    if not extracted:
        extracted = cleaner.clean_knowledge_text(text)
    
    return f"提取的知识库内容（长度：{len(extracted)}字符）:\n{extracted[:3000]}{'...' if len(extracted) > 3000 else ''}"


clean_text_tool = StructuredTool.from_function(
    func=clean_text,
    name="clean_text",
    description="清理文本，去除HTML标签、数字、标点等噪声",
    args_schema=TextCleanInput
)

extract_text_tool = StructuredTool.from_function(
    func=extract_text,
    name="extract_text",
    description="从文本中提取特定类型的内容（中文、数字、邮箱、手机号、网址）",
    args_schema=TextExtractInput
)

split_text_tool = StructuredTool.from_function(
    func=split_text_into_chunks,
    name="split_text",
    description="将长文本按Markdown标题和句号分块，支持自定义分块大小和重叠",
    args_schema=TextSplitInput
)

extract_knowledge_tool = StructuredTool.from_function(
    func=extract_knowledge_content,
    name="extract_knowledge_content",
    description="从知识库文档中提取有效内容，去除元信息和格式标记",
    args_schema=KnowledgeExtractInput
)
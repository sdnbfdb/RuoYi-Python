import os
import sys
import re
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.code import tokenize, encode_texts_with_position
from nlp.clear import TextCleaner
from nlp.understand import SentimentAnalyzer
from nlp.vector_db import VectorDB, safe_print


# 默认每个 chunk 的最大字符数
DEFAULT_CHUNK_SIZE = 800
# chunk 之间重叠字符数，避免关键信息被截断
DEFAULT_CHUNK_OVERLAP = 100


def split_into_chunks(text: str, max_size: int = DEFAULT_CHUNK_SIZE,
                       overlap: int = DEFAULT_CHUNK_OVERLAP) -> list:
    """
    将文本按 Markdown 标题逐行拆分成段落，再对超长段落按句号拆分。
    关键：逐行解析，不会因为子标题（###）导致正文丢失。
    每个 chunk 返回: {'section_title': str, 'content': str, 'index': int}
    """
    lines = text.split('\n')

    # ---- 第一步：逐行解析，按 ## 二级标题拆分大段 ----
    # 只按 ## (2个#) 作为分界点，### 子标题归入父段落
    sections = []
    current_title = '概述'
    current_lines = []

    for line in lines:
        stripped = line.strip()
        # 只匹配恰好2个#的二级标题作为分界
        h2_match = re.match(r'^##\s+(.+)', stripped)
        if h2_match:
            # 保存当前段落
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    sections.append({'section_title': current_title, 'content': content})
            current_title = h2_match.group(1).strip()
            current_lines = [stripped]  # 标题行也保留在内容中
        elif stripped.startswith('# '):
            # 一级标题 (#)，也作为分界
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    sections.append({'section_title': current_title, 'content': content})
            current_title = stripped.lstrip('#').strip()
            current_lines = [stripped]
        else:
            current_lines.append(line)

    # 别忘了最后一段
    if current_lines:
        content = '\n'.join(current_lines).strip()
        if content:
            sections.append({'section_title': current_title, 'content': content})

    # 如果没有任何标题，整个文本作为一段
    if not sections:
        sections.append({'section_title': '全文', 'content': text.strip()})

    # ---- 第二步：对超长段落按句号再拆分 ----
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
            # 按句号拆分成句子
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
                    # 保留尾部重叠
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

    return chunks


class KnowledgeProcessor:
    def __init__(self, knowledge_path: str = None, db_path: str = None):
        if knowledge_path is None:
            knowledge_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'data', 'knowledge'
            )

        self.knowledge_path = knowledge_path
        self.vector_db = VectorDB(db_path)
        self.cleaner = TextCleaner()
        self.analyzer = SentimentAnalyzer()

        safe_print(f"[PATH] Knowledge base: {self.knowledge_path}")
        safe_print(f"[PATH] Vector DB: {self.vector_db.db_path}")

    def extract_content(self, filepath: str) -> str:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            extracted = self.cleaner.extract_knowledge_content(content)

            if not extracted:
                extracted = self.cleaner.clean_knowledge_text(content)

            return extracted

        except Exception as e:
            safe_print(f"[WARN] Read file failed {filepath}: {e}")
            return ""

    def extract_metadata(self, filepath: str, content: str) -> dict:
        filename = os.path.basename(filepath)
        filename_without_ext = filename.replace('.txt', '')  # 完整文件名：31972024_猪肉做法大全

        parts = filename_without_ext.split('_', 1)
        doc_id = parts[0] if len(parts) > 0 else 'unknown'
        title = parts[1] if len(parts) > 1 else filename_without_ext

        sentiment_result = self.analyzer.analyze(content[:500])

        tokens = tokenize(content[:1000])

        return {
            'id': doc_id,
            'filename': filename_without_ext,  # 用作向量文件命名
            'title': title,
            'filepath': filepath,
            'sentiment': sentiment_result['sentiment'],
            'sentiment_confidence': sentiment_result['confidence'],
            'word_count': len(content),
            'token_count': len(tokens),
            'preview': content[:200] + '...' if len(content) > 200 else content
        }

    def process_all(self) -> int:
        """段落级索引：将每个文档拆分为多个 chunk，每个 chunk 独立编码存入向量库"""
        safe_print("\n" + "=" * 60)
        safe_print("START processing knowledge base (chunk-level)")
        safe_print("=" * 60)

        pattern = os.path.join(self.knowledge_path, '*.txt')
        files = glob.glob(pattern)
        files = [f for f in files if not os.path.basename(f).startswith('_')]

        if not files:
            safe_print("[WARN] No files found in knowledge base")
            return 0

        safe_print(f"[INFO] Found {len(files)} files")

        # ---- 1. 逐文件拆分为 chunks ----
        all_chunks = []      # 所有 chunk 的文本内容（用于编码）
        all_metadata = []    # 每个 chunk 的元数据

        for filepath in files:
            content = self.extract_content(filepath)
            if not content:
                continue

            doc_meta = self.extract_metadata(filepath, content)
            doc_title = doc_meta['title']
            doc_id = doc_meta['id']

            # 拆分为 chunks
            chunks = split_into_chunks(content)
            safe_print(f"[FILE] {doc_title} -> {len(chunks)} chunks")

            for chunk in chunks:
                chunk_meta = {
                    **doc_meta,
                    'chunk_index': chunk['index'],
                    'chunk_section': chunk['section_title'],
                    'content': chunk['content'],
                    'preview': chunk['content'][:200] + '...' if len(chunk['content']) > 200 else chunk['content'],
                    # 保留文档级信息以便后续分组
                    'doc_id': doc_id,
                    'doc_title': doc_title,
                    'doc_filename': doc_meta['filename'],  # 用于向量文件命名
                }
                all_chunks.append(chunk['content'])
                all_metadata.append(chunk_meta)

        if not all_chunks:
            safe_print("[WARN] No valid content found")
            return 0

        # ---- 2. 编码所有 chunks ----
        safe_print(f"\n[INFO] Encoding {len(all_chunks)} chunks...")
        embeddings, vocab = encode_texts_with_position(
            all_chunks,
            max_features=5000,
            ngram_range=(1, 2),
            position_weight=0.1
        )

        safe_print(f"[INFO] Vector shape: {embeddings.shape}")
        safe_print(f"[INFO] Vocab size: {len(vocab)}")

        # ---- 3. 存入向量库 ----
        self.vector_db.clear()
        self.vector_db.add_batch(embeddings, all_metadata)
        self.vector_db.set_vocab(vocab)

        # 统计文档数
        doc_count = len(set(m['doc_id'] for m in all_metadata))

        safe_print("\n" + "=" * 60)
        safe_print(f"[OK] Done! {doc_count} docs -> {len(all_metadata)} chunks indexed")
        safe_print("=" * 60)

        return len(all_metadata)

    def rebuild_index(self):
        safe_print("\n[ WARN ] Rebuild index will clear existing DB!")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm == 'y':
            self.process_all()
        else:
            safe_print("Cancelled")

    def print_stats(self):
        stats = self.vector_db.get_stats()
        safe_print("\n[STATS] Vector DB:")
        safe_print(f"   Total records: {stats['total_count']}")
        safe_print(f"   Vector dim: {stats['vector_dim']}")
        safe_print(f"   Vocab size: {stats['vocab_size']}")
        safe_print(f"   Sentiment distribution:")
        for sent, count in stats['sentiments'].items():
            safe_print(f"      - {sent}: {count}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Knowledge Processor')
    parser.add_argument('--rebuild', action='store_true', help='Rebuild index')
    parser.add_argument('--stats', action='store_true', help='Show stats')
    parser.add_argument('--force', action='store_true', help='Force rebuild without confirmation')
    args = parser.parse_args()

    processor = KnowledgeProcessor()

    if args.rebuild:
        if args.force:
            processor.process_all()
        else:
            processor.rebuild_index()
    elif args.stats:
        processor.print_stats()
    else:
        if processor.vector_db.count() > 0:
            safe_print(f"\n[INFO] DB has {processor.vector_db.count()} records")
            response = input("Rebuild index? (y/n): ").strip().lower()
            if response == 'y':
                processor.rebuild_index()
            else:
                processor.print_stats()
        else:
            processor.process_all()
            processor.print_stats()


if __name__ == '__main__':
    main()
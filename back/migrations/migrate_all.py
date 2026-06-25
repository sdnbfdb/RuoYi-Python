import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import re
from vector_store.chroma_store import CharmDBStore, DashScopeEmbeddings
from knowledge.knowledge import load_knowledge_data, get_knowledge_by_id
from nlp.clear import TextCleaner
from nlp.excel.header_embedding import HeaderEmbeddingEncoder
from nlp.excel.header_matrix import HeaderMatrixAnalyzer
from nlp.excel.table_retriever import TableDataRetriever

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


def split_into_chunks(text: str, max_size: int = DEFAULT_CHUNK_SIZE,
                       overlap: int = DEFAULT_CHUNK_OVERLAP) -> list:
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

    return chunks


def migrate_knowledge_to_chroma():
    print("=" * 60)
    print("开始迁移知识库数据到 ChromaDB")
    print("=" * 60)

    chroma_store = CharmDBStore(persist_directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chroma_db'))

    knowledge_data = load_knowledge_data()
    print(f"从数据库加载到 {len(knowledge_data)} 条知识库记录")

    if not knowledge_data:
        print("没有找到知识库数据")
        return

    documents = []
    metadatas = []
    ids = []

    total_chunks = 0
    cleaner = TextCleaner()

    for item in knowledge_data:
        doc_id = str(item.get('id', ''))
        title = item.get('title', '')
        content = item.get('content', '')
        type_ = item.get('type', 'other')
        description = item.get('description', '')
        tags = item.get('tags', [])
        created_at = str(item.get('created_at', ''))
        created_by = item.get('created_by', '')

        cleaned_content = cleaner.clean_knowledge_text(content)
        if not cleaned_content:
            cleaned_content = cleaner.clean_text(content)

        chunks = split_into_chunks(cleaned_content)

        for chunk in chunks:
            chunk_id = f"{doc_id}_{chunk['index']}"
            document_text = f"标题：{title}\n章节：{chunk['section_title']}\n内容：{chunk['content']}"

            documents.append(document_text)
            
            metadata = {
                'doc_id': doc_id,
                'chunk_id': chunk_id,
                'title': title,
                'section_title': chunk['section_title'],
                'type': type_,
                'description': description,
                'created_at': created_at,
                'created_by': created_by,
                'source': 'knowledge_base',
                'chunk_index': chunk['index'],
                'content_preview': chunk['content'][:200]
            }
            if tags and len(tags) > 0:
                metadata['tags'] = tags
            
            metadatas.append(metadata)
            ids.append(chunk_id)
            total_chunks += 1

        print(f"文档 '{title}' -> {len(chunks)} 个分块")

    if documents:
        chroma_store.add_documents(
            collection_name='knowledge_base',
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"\n成功迁移 {len(knowledge_data)} 条文档，共 {total_chunks} 个分块到 ChromaDB")
    else:
        print("没有有效的文档内容")


def migrate_table_data_to_chroma():
    print("\n" + "=" * 60)
    print("开始迁移表格数据到 ChromaDB")
    print("=" * 60)

    chroma_store = CharmDBStore(persist_directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chroma_db'))

    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    if not os.path.exists(data_dir):
        print(f"数据目录不存在: {data_dir}")
        return

    encoder = HeaderEmbeddingEncoder()
    analyzer = HeaderMatrixAnalyzer()

    analyzer.load_files_from_directory(data_dir)
    analyzer.build_association_matrix()

    if analyzer.file_headers:
        documents = []
        metadatas = []
        ids = []

        for filename, headers in analyzer.file_headers.items():
            header_info = {
                'filename': filename,
                'headers': headers,
                'header_count': len(headers)
            }

            document_text = f"文件名：{filename}\n表头：{', '.join(headers)}"

            documents.append(document_text)
            metadatas.append({
                **header_info,
                'source': 'table_data',
                'vector_dim': 768 if encoder.model else 64
            })
            ids.append(f"table_{uuid.uuid4().hex[:8]}")

        if documents:
            chroma_store.add_documents(
                collection_name='table_headers',
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"成功迁移 {len(documents)} 个表格的表头信息到 ChromaDB")

    common_headers = analyzer.find_common_headers(min_files=2)
    if common_headers:
        print(f"\n公共表头（出现多次）:")
        for header, count in common_headers[:10]:
            print(f"  - {header}: {count} 个文件")


def migrate_nlp_data():
    print("\n" + "=" * 60)
    print("迁移NLP处理结果")
    print("=" * 60)

    chroma_store = CharmDBStore(persist_directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chroma_db'))

    nlp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nlp')
    data_dir = os.path.join(nlp_dir, 'excel', 'data')

    if os.path.exists(data_dir):
        retriever = TableDataRetriever(data_dir=data_dir)
        retriever.load_all()

        if retriever.tables:
            documents = []
            metadatas = []
            ids = []

            for filename, rows in retriever.tables.items():
                sample_data = []
                for row in rows[:5]:
                    row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
                    sample_data.append(row_str)

                document_text = f"文件名：{filename}\n表头：{', '.join(retriever.table_headers[filename])}\n示例数据：\n" + "\n".join(sample_data)

                documents.append(document_text)
                metadatas.append({
                    'filename': filename,
                    'headers': retriever.table_headers[filename],
                    'row_count': len(rows),
                    'source': 'nlp_excel_data'
                })
                ids.append(f"nlp_{uuid.uuid4().hex[:8]}")

            if documents:
                chroma_store.add_documents(
                    collection_name='nlp_excel',
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"成功迁移 {len(documents)} 个NLP表格数据到 ChromaDB")
    else:
        print(f"NLP数据目录不存在: {data_dir}")


def verify_migration():
    print("\n" + "=" * 60)
    print("验证迁移结果")
    print("=" * 60)

    chroma_store = CharmDBStore(persist_directory=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chroma_db'))

    collections = chroma_store.get_all_collections()
    print(f"ChromaDB中的集合: {collections}")

    for collection_name in collections:
        stats = chroma_store.get_collection_stats(collection_name)
        print(f"  {collection_name}: {stats['count']} 条记录")

    print("\n" + "=" * 60)
    print("迁移验证完成")
    print("=" * 60)


def main():
    migrate_knowledge_to_chroma()
    migrate_table_data_to_chroma()
    migrate_nlp_data()
    verify_migration()


if __name__ == '__main__':
    main()
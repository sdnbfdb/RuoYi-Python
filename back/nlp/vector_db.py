import numpy as np
import os
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime


def safe_print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))


class VectorDB:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'vector_db')

        self.db_path = db_path
        self.index_file = os.path.join(db_path, 'index.json')  # 统一索引文件
        self.vocab_file = os.path.join(db_path, 'vocab.json')
        
        # 每个txt文件独立存储：{filename: {'vectors': ndarray, 'metadata': list}}
        self.doc_dbs = {}
        self.vocab = {}

        os.makedirs(db_path, exist_ok=True)
        self._load()
    
    def _compute_keyword_matching(self, query_tokens: List[str], document_text: str) -> Dict:
        """计算查询关键词与文档内容的匹配程度"""
        if not query_tokens or not document_text:
            return {'matched_keywords': [], 'match_count': 0, 'match_ratio': 0.0}
        
        document_lower = document_text.lower()
        query_tokens_lower = [token.lower() for token in query_tokens]
        
        matched_keywords = []
        for token in query_tokens_lower:
            if token in document_lower:
                matched_keywords.append(token)
        
        match_count = len(matched_keywords)
        match_ratio = match_count / len(query_tokens_lower) if query_tokens_lower else 0.0
        
        return {
            'matched_keywords': matched_keywords,
            'match_count': match_count,
            'match_ratio': match_ratio
        }
    
    def _find_matched_sections(self, query_tokens: List[str], document_text: str, max_sections: int = 3) -> List[str]:
        """查找文档中与查询关键词匹配的具体段落"""
        if not query_tokens or not document_text:
            return []
        
        query_tokens_lower = [token.lower() for token in query_tokens]
        document_lower = document_text.lower()
        
        sections = document_text.split('。')
        matched_sections = []
        
        for section in sections:
            section_lower = section.lower()
            has_match = any(token in section_lower for token in query_tokens_lower)
            if has_match and section.strip():
                matched_sections.append(section.strip() + '。')
                if len(matched_sections) >= max_sections:
                    break
        
        return matched_sections

    def _load(self):
        """加载所有文档向量文件和统一索引"""
        if not os.path.exists(self.db_path):
            safe_print(f"[NEW] Create new vector DB")
            return
        
        # 加载统一索引文件
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        else:
            index_data = {}
        
        # 扫描所有 *_vectors.npy 文件
        vector_files = [f for f in os.listdir(self.db_path) 
                       if f.endswith('_vectors.npy')]
        
        if not vector_files:
            safe_print(f"[NEW] Create new vector DB")
            return
        
        total_records = 0
        for vf in vector_files:
            # 提取文件名：31972024_猪肉做法大全_vectors.npy -> 31972024_猪肉做法大全
            filename = vf.replace('_vectors.npy', '')
            
            vectors_file = os.path.join(self.db_path, vf)
            
            try:
                vectors = np.load(vectors_file)
                
                # 从索引文件获取metadata
                metadata = index_data.get(filename, {}).get('data', [])
                
                self.doc_dbs[filename] = {
                    'vectors': vectors,
                    'metadata': metadata
                }
                total_records += len(metadata)
            except Exception as e:
                safe_print(f"[WARN] Load {filename} failed: {e}")
        
        safe_print(f"[OK] Load vector DB: {len(self.doc_dbs)} docs, {total_records} records")
        
        # 加载词汇表
        if os.path.exists(self.vocab_file):
            with open(self.vocab_file, 'r', encoding='utf-8') as f:
                self.vocab = json.load(f)
            safe_print(f"[OK] Load vocab: {len(self.vocab)} words")
        else:
            self.vocab = {}

    def _save(self):
        """保存所有文档向量文件和统一索引"""
        # 构建统一索引
        index_data = {}
        
        for filename, doc_db in self.doc_dbs.items():
            # 保存向量文件：31972024_猪肉做法大全_vectors.npy
            vectors_file = os.path.join(self.db_path, f'{filename}_vectors.npy')
            
            if doc_db['vectors'] is not None and len(doc_db['vectors']) > 0:
                np.save(vectors_file, doc_db['vectors'])
            
            # 添加到索引：{filename: {title, data, created_at}}
            if doc_db['metadata']:
                # 从metadata中提取title（取第一个chunk的title）
                title = doc_db['metadata'][0].get('title', filename)
                created_at = doc_db['metadata'][0].get('created_at', datetime.now().isoformat())
                
                index_data[filename] = {
                    'title': title,
                    'data': doc_db['metadata'],
                    'created_at': created_at
                }
        
        # 保存统一索引文件
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        # 保存词汇表
        with open(self.vocab_file, 'w', encoding='utf-8') as f:
            json.dump(self.vocab, f, ensure_ascii=False, indent=2)
        
        # 清理旧的独立meta文件
        for f in os.listdir(self.db_path):
            if f.endswith('_meta.json'):
                os.remove(os.path.join(self.db_path, f))
        
        total = sum(len(db['metadata']) for db in self.doc_dbs.values())
        safe_print(f"[OK] DB saved: {len(self.doc_dbs)} docs, {total} records")

    def add(self, vector: np.ndarray, metadata: Dict):
        """添加单个向量到对应文档"""
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        
        # 使用完整文件名作为doc_id：31972024_猪肉做法大全
        doc_id = metadata.get('doc_filename', metadata.get('filename', metadata.get('id', 'unknown')))
        
        if doc_id not in self.doc_dbs:
            self.doc_dbs[doc_id] = {'vectors': vector, 'metadata': []}
        else:
            doc_db = self.doc_dbs[doc_id]
            if doc_db['vectors'] is None:
                doc_db['vectors'] = vector
            else:
                doc_db['vectors'] = np.vstack([doc_db['vectors'], vector])
        
        metadata['id'] = len(self.doc_dbs[doc_id]['metadata'])
        metadata['created_at'] = datetime.now().isoformat()
        self.doc_dbs[doc_id]['metadata'].append(metadata)
        
        self._save()

    def add_batch(self, vectors: np.ndarray, metadata_list: List[Dict]):
        """批量添加向量，按doc_filename分组存储"""
        # 按 doc_filename 分组
        doc_groups = {}
        for i, metadata in enumerate(metadata_list):
            # 使用完整文件名：31972024_猪肉做法大全
            doc_id = metadata.get('doc_filename', metadata.get('filename', metadata.get('id', 'unknown')))
            if doc_id not in doc_groups:
                doc_groups[doc_id] = {'indices': [], 'metadata': []}
            doc_groups[doc_id]['indices'].append(i)
            doc_groups[doc_id]['metadata'].append(metadata)
        
        # 分别添加到各个文档
        for doc_id, group in doc_groups.items():
            indices = group['indices']
            doc_vectors = vectors[indices]
            
            if doc_id not in self.doc_dbs:
                self.doc_dbs[doc_id] = {'vectors': doc_vectors, 'metadata': []}
            else:
                doc_db = self.doc_dbs[doc_id]
                if doc_db['vectors'] is None:
                    doc_db['vectors'] = doc_vectors
                else:
                    doc_db['vectors'] = np.vstack([doc_db['vectors'], doc_vectors])
            
            for metadata in group['metadata']:
                metadata['id'] = len(self.doc_dbs[doc_id]['metadata'])
                metadata['created_at'] = datetime.now().isoformat()
                self.doc_dbs[doc_id]['metadata'].append(metadata)
        
        self._save()

    def set_vocab(self, vocab: Dict):
        self.vocab = vocab
        self._save()

    def get_vocab(self) -> Dict:
        return self.vocab

    def _compute_attention_scores(self, query_vector: np.ndarray) -> np.ndarray:
        """计算查询向量与所有文档向量的注意力分数"""
        vectors, _ = self._get_all_vectors_and_metadata()
        if vectors is None or len(vectors) == 0:
            return np.array([])
            
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
            
        d_k = query_vector.shape[1]
        scores = np.dot(vectors, query_vector.T).flatten() / np.sqrt(d_k)
        return scores

    def _scaled_dot_product_attention(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict]:
        """缩放点积注意力机制"""
        vectors, metadata = self._get_all_vectors_and_metadata()
        if vectors is None or len(vectors) == 0:
            return []
            
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
            
        if vectors.shape[1] != query_vector.shape[1]:
            safe_print(f"[ERROR] Vector dimension mismatch: DB={vectors.shape[1]}, Query={query_vector.shape[1]}")
            return []
            
        query_norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        if query_norm[0][0] == 0:
            safe_print("[WARN] Query vector is all zeros")
            return []
            
        d_k = query_vector.shape[1]
        query_normalized = query_vector / query_norm
        vectors_norm = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors_normalized = np.nan_to_num(vectors / vectors_norm)
            
        attention_scores = np.dot(vectors_normalized, query_normalized.T).flatten() / np.sqrt(d_k)
        attention_weights = np.exp(attention_scores) / np.sum(np.exp(attention_scores))
            
        sorted_indices = np.argsort(-attention_weights)
            
        results = []
        for idx in sorted_indices[:top_k]:
            meta = metadata[idx].copy()
            meta['similarity'] = float(attention_weights[idx])
            meta['attention_score'] = float(attention_scores[idx])
            results.append(meta)
                
            if len(results) >= top_k:
                break
            
        return results

    def _multi_head_attention(self, query_vector: np.ndarray, num_heads: int = 3, top_k: int = 5) -> List[Dict]:
        """多头注意力机制"""
        vectors, metadata = self._get_all_vectors_and_metadata()
        if vectors is None or len(vectors) == 0:
            return []
            
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
            
        if vectors.shape[1] != query_vector.shape[1]:
            safe_print(f"[ERROR] Vector dimension mismatch: DB={vectors.shape[1]}, Query={query_vector.shape[1]}")
            return []
            
        d_model = query_vector.shape[1]
        if d_model % num_heads != 0:
            num_heads = 1
            
        d_k = d_model // num_heads
            
        all_head_results = []
            
        for head in range(num_heads):
            start = head * d_k
            end = (head + 1) * d_k
                
            query_head = query_vector[:, start:end]
            vectors_head = vectors[:, start:end]
                
            query_norm = np.linalg.norm(query_head, axis=1, keepdims=True)
            if query_norm[0][0] == 0:
                continue
                    
            query_normalized = query_head / query_norm
            vectors_norm = np.linalg.norm(vectors_head, axis=1, keepdims=True)
            vectors_normalized = np.nan_to_num(vectors_head / vectors_norm)
                
            scores = np.dot(vectors_normalized, query_normalized.T).flatten() / np.sqrt(d_k)
            weights = np.exp(scores) / np.sum(np.exp(scores))
                
            all_head_results.append(weights)
            
        if not all_head_results:
            return []
            
        combined_weights = np.mean(np.array(all_head_results), axis=0)
            
        sorted_indices = np.argsort(-combined_weights)
            
        results = []
        for idx in sorted_indices[:top_k]:
            meta = metadata[idx].copy()
            meta['similarity'] = float(combined_weights[idx])
            meta['attention_method'] = 'multi_head'
            meta['num_heads'] = num_heads
            results.append(meta)
                
            if len(results) >= top_k:
                break
            
        return results

    def search(self, query_vector: np.ndarray, top_k: int = 5,
               sentiment_filter: Optional[str] = None, use_attention: bool = True,
               query_tokens: Optional[List[str]] = None) -> List[Dict]:
        """搜索方法，支持普通相似度和注意力机制"""
        if use_attention:
            results = self._multi_head_attention(query_vector, top_k=top_k)
        else:
            results = self._traditional_search(query_vector, top_k, sentiment_filter)
        
        if query_tokens:
            for res in results:
                doc_content = res.get('content', res.get('preview', ''))
                keyword_match = self._compute_keyword_matching(query_tokens, doc_content)
                matched_sections = self._find_matched_sections(query_tokens, doc_content)
                
                res['keyword_matching'] = keyword_match
                res['matched_sections'] = matched_sections
        
        return results

    def _traditional_search(self, query_vector: np.ndarray, top_k: int = 5,
                            sentiment_filter: Optional[str] = None) -> List[Dict]:
        """传统的余弦相似度搜索"""
        vectors, metadata = self._get_all_vectors_and_metadata()
        if vectors is None or len(vectors) == 0:
            return []
            
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
            
        if vectors.shape[1] != query_vector.shape[1]:
            safe_print(f"[ERROR] Vector dimension mismatch: DB={vectors.shape[1]}, Query={query_vector.shape[1]}")
            return []
            
        query_norm = np.linalg.norm(query_vector, axis=1, keepdims=True)
        vectors_norm = np.linalg.norm(vectors, axis=1, keepdims=True)
            
        if query_norm[0][0] == 0:
            safe_print("[WARN] Query vector is all zeros")
            return []
            
        with np.errstate(divide='ignore', invalid='ignore'):
            query_normalized = query_vector / query_norm
            vectors_normalized = vectors / vectors_norm
            
        query_normalized = np.nan_to_num(query_normalized)
        vectors_normalized = np.nan_to_num(vectors_normalized)
            
        similarities = np.dot(vectors_normalized, query_normalized.T).flatten()
        similarities = np.nan_to_num(similarities, nan=-1.0)
            
        sorted_indices = np.argsort(-similarities)
            
        results = []
        for idx in sorted_indices[:top_k]:
            meta = metadata[idx].copy()
            meta['similarity'] = float(similarities[idx])
                
            if sentiment_filter and meta.get('sentiment') != sentiment_filter:
                continue
                
            results.append(meta)
                
            if len(results) >= top_k:
                break
            
        return results

    def search_grouped_by_doc(self, query_vector: np.ndarray, top_k: int = 5,
                                use_attention: bool = True,
                                query_tokens: Optional[List[str]] = None,
                                max_chunks_per_doc: int = 3) -> List[Dict]:
        """
        搜索后按文档分组聚合：同一文档的多个 chunk 合并展示，
        每个文档只保留相似度最高的 max_chunks_per_doc 个段落。
        返回: [{'doc_id': ..., 'doc_title': ..., 'best_similarity': ..., 'chunks': [...]}]
        """
        # 取 top_k * 3 扩大候选范围，因为同一文档可能占多个位置
        raw_results = self.search(query_vector, top_k=top_k * 3,
                                  use_attention=use_attention,
                                  query_tokens=query_tokens)

        if not raw_results:
            return []

        # 按 doc_id 分组
        doc_groups = {}
        for res in raw_results:
            doc_id = res.get('doc_id', res.get('id', 'unknown'))
            if doc_id not in doc_groups:
                doc_groups[doc_id] = {
                    'doc_id': doc_id,
                    'doc_title': res.get('doc_title', res.get('title', '未知')),
                    'best_similarity': res.get('similarity', 0),
                    'chunks': []
                }
            group = doc_groups[doc_id]

            # 只保留每个文档最好的 max_chunks_per_doc 个 chunk
            if len(group['chunks']) < max_chunks_per_doc:
                group['chunks'].append(res)
                # 更新最佳相似度
                if res.get('similarity', 0) > group['best_similarity']:
                    group['best_similarity'] = res.get('similarity', 0)

        # 按 best_similarity 降序排列文档
        sorted_groups = sorted(doc_groups.values(),
                               key=lambda g: g['best_similarity'],
                               reverse=True)

        return sorted_groups[:top_k]

    def search_by_sentiment(self, query_vector: np.ndarray,
                           sentiment: str, top_k: int = 5) -> List[Dict]:
        return self.search(query_vector, top_k * 2, sentiment_filter=sentiment)[:top_k]

    def get_chunks_by_filename(self, filename: str, max_chunks: int = 5, query_tokens: list = None) -> list:
        """按文件名直接获取段落（展示前 max_chunks 个），用于文件名匹配时的内容展示兼容"""
        results = []
        for doc_id, doc_db in self.doc_dbs.items():
            for meta in doc_db['metadata']:
                title = meta.get('doc_title', meta.get('title', ''))
                if filename in title or filename in doc_id:
                    chunk = dict(meta)
                    chunk['similarity'] = 1.0  # 直接匹配，相似度设为最高
                    if query_tokens:
                        content = meta.get('content', '') or meta.get('preview', '')
                        chunk['keyword_matching'] = self._compute_keyword_matching(query_tokens, content)
                    else:
                        chunk['keyword_matching'] = {'matched_keywords': [], 'match_count': 0, 'match_ratio': 0.0}
                    results.append(chunk)
                    if len(results) >= max_chunks:
                        return results
        return results

    def count(self) -> int:
        """返回总记录数"""
        return sum(len(db['metadata']) for db in self.doc_dbs.values())
    
    def _get_all_vectors_and_metadata(self):
        """合并所有文档的向量和元数据（用于搜索）"""
        if not self.doc_dbs:
            return None, []
        
        all_vectors = []
        all_metadata = []
        
        for doc_id, doc_db in self.doc_dbs.items():
            if doc_db['vectors'] is not None and len(doc_db['vectors']) > 0:
                all_vectors.append(doc_db['vectors'])
                all_metadata.extend(doc_db['metadata'])
        
        if not all_vectors:
            return None, []
        
        return np.vstack(all_vectors), all_metadata

    def clear(self):
        """清空所有文档向量文件"""
        self.doc_dbs = {}
        self.vocab = {}
        
        # 删除所有相关文件
        for f in os.listdir(self.db_path):
            if f.endswith('_vectors.npy') or f.endswith('_meta.json') or f == 'vocab.json':
                os.remove(os.path.join(self.db_path, f))
        
        safe_print(f"[DEL] DB cleared")

    def get_stats(self) -> Dict:
        sentiments = {}
        for doc_db in self.doc_dbs.values():
            for meta in doc_db['metadata']:
                sent = meta.get('sentiment', 'unknown')
                sentiments[sent] = sentiments.get(sent, 0) + 1
            
        # 获取向量维度
        vector_dim = 0
        for doc_db in self.doc_dbs.values():
            if doc_db['vectors'] is not None and len(doc_db['vectors']) > 0:
                vector_dim = doc_db['vectors'].shape[1]
                break
            
        return {
            'total_count': self.count(),
            'doc_count': len(self.doc_dbs),
            'sentiments': sentiments,
            'vector_dim': vector_dim,
            'vocab_size': len(self.vocab)
        }


def create_vector_db(db_path: str = None) -> VectorDB:
    return VectorDB(db_path)
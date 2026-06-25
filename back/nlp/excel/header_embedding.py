#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表头向量化编码工具
使用预训练语言模型将数据表头转换为向量表示并存储
"""

import os
import csv
import json
import numpy as np
from typing import List, Dict

# 在导入前设置环境变量，禁用自动转换
import os
os.environ['SAFETENSORS_FAST_GPU'] = '0'
os.environ['TRANSFORMERS_AUTO_CONVERSION'] = '0'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model_cache')

try:
    import torch
    from transformers import BertTokenizer, BertModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[警告] transformers 未安装，将使用简单的基于词频的向量化")


class HeaderEmbeddingEncoder:
    def __init__(self, model_name: str = "uer/roberta-base-finetuned-dianping-chinese"):
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.header_vectors = {}  # {表头: 向量}
        self.file_header_vectors = {}  # {文件名: {表头: 向量}}
        
        if TRANSFORMERS_AVAILABLE:
            self._load_model(model_name)
    
    def _load_model(self, model_name: str):
        """加载预训练BERT模型"""
        try:
            print(f"[INFO] 加载模型: {model_name}")
            nlp_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(nlp_dir, 'model_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # 先尝试使用本地模型
            try:
                self.tokenizer = BertTokenizer.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    local_files_only=True
                )
                self.model = BertModel.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    local_files_only=True,
                    ignore_mismatched_sizes=True
                )
                print("[INFO] 使用本地模型")
            except Exception as local_e:
                # 本地加载失败，尝试在线下载
                print(f"[INFO] 本地模型加载失败，尝试在线下载: {str(local_e)[:50]}")
                self.tokenizer = BertTokenizer.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    local_files_only=False
                )
                self.model = BertModel.from_pretrained(
                    model_name,
                    cache_dir=cache_dir,
                    local_files_only=False,
                    ignore_mismatched_sizes=True
                )
            
            self.model.to(self.device)
            self.model.eval()
            print("[OK] 模型加载成功")
        except Exception as e:
            print(f"[警告] 加载BERT模型失败: {str(e)[:100]}")
            print("[INFO] 将使用简单向量化方法")
    
    def encode_header(self, header: str) -> np.ndarray:
        """将单个表头编码为向量"""
        if TRANSFORMERS_AVAILABLE and self.model:
            return self._bert_encode(header)
        else:
            return self._simple_encode(header)
    
    def _bert_encode(self, header: str) -> np.ndarray:
        """使用BERT编码表头"""
        inputs = self.tokenizer(
            header,
            padding=True,
            truncation=True,
            max_length=32,
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # 使用 <[BOS_never_used_51bce0c785ca2f68081bfa7d91973934]> token的隐藏状态作为向量表示
        cls_embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy().flatten()
        return cls_embedding
    
    def _simple_encode(self, header: str) -> np.ndarray:
        """简单的基于字符和拼音特征的向量化"""
        # 特征维度：字符长度、字符类型分布、拼音特征等
        features = []
        
        # 字符长度
        features.append(len(header))
        
        # 字符类型统计
        char_counts = {
            'digit': 0,
            'letter': 0,
            'chinese': 0,
            'punctuation': 0
        }
        for char in header:
            if char.isdigit():
                char_counts['digit'] += 1
            elif char.isalpha():
                char_counts['letter'] += 1
            elif '\u4e00' <= char <= '\u9fff':
                char_counts['chinese'] += 1
            else:
                char_counts['punctuation'] += 1
        
        features.extend([char_counts[k] for k in ['digit', 'letter', 'chinese', 'punctuation']])
        
        # 归一化
        features = np.array(features, dtype=np.float32)
        if np.max(features) > 0:
            features = features / np.max(features)
        
        # 扩展到固定维度（64维）
        if len(features) < 64:
            padding = np.zeros(64 - len(features), dtype=np.float32)
            features = np.concatenate([features, padding])
        
        return features[:64]
    
    def encode_headers_from_file(self, file_path: str) -> Dict[str, np.ndarray]:
        """从文件提取表头并编码"""
        headers = self._extract_headers(file_path)
        if not headers:
            return {}
        
        filename = os.path.basename(file_path)
        self.file_header_vectors[filename] = {}
        
        for header in headers:
            vector = self.encode_header(header)
            self.file_header_vectors[filename][header] = vector
            # 也添加到全局表头向量字典
            if header not in self.header_vectors:
                self.header_vectors[header] = vector
        
        print(f"[OK] 处理文件: {filename} ({len(headers)} 个表头)")
        return self.file_header_vectors[filename]
    
    def _extract_headers(self, file_path: str) -> List[str]:
        """提取文件表头"""
        _, ext = os.path.splitext(file_path)
        
        if ext.lower() in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                df = pd.read_excel(file_path, nrows=0)
                return df.columns.tolist()
            except Exception as e:
                print(f"[警告] 读取Excel失败: {str(e)}")
        
        elif ext.lower() == '.csv':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    first_row = next(reader, None)
                    return first_row if first_row else []
            except Exception as e:
                print(f"[警告] 读取CSV失败: {str(e)}")
        
        return []
    
    def encode_directory(self, directory_path: str) -> Dict[str, Dict[str, np.ndarray]]:
        """处理目录中的所有文件"""
        if not os.path.exists(directory_path):
            print(f"[错误] 目录不存在: {directory_path}")
            return {}
        
        supported_exts = ['.xlsx', '.xls', '.csv']
        
        for filename in os.listdir(directory_path):
            _, ext = os.path.splitext(filename)
            if ext.lower() in supported_exts:
                file_path = os.path.join(directory_path, filename)
                self.encode_headers_from_file(file_path)
        
        print(f"\n处理完成! 共 {len(self.file_header_vectors)} 个文件, {len(self.header_vectors)} 个独特表头")
        return self.file_header_vectors
    
    def save_embeddings(self, output_dir: str) -> bool:
        """保存向量化结果：每个CSV文件一个npy文件"""
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 保存每个文件的表头向量为独立的npy文件
            if self.file_header_vectors:
                for filename, header_vecs in self.file_header_vectors.items():
                    # 文件名去掉扩展名：health_data.csv -> health_data
                    filename_without_ext = os.path.splitext(filename)[0]
                    
                    # 保存向量：health_data_vectors.npy
                    headers = list(header_vecs.keys())
                    vectors = np.array([header_vecs[h] for h in headers])
                    
                    npy_file = os.path.join(output_dir, f'{filename_without_ext}_vectors.npy')
                    np.save(npy_file, vectors)
                    
                    # 保存索引：health_data_index.json
                    index_data = {
                        'filename': filename,
                        'headers': headers,
                        'vector_dim': vectors.shape[1],
                        'total_headers': len(headers),
                        'model_used': 'BERT' if (TRANSFORMERS_AVAILABLE and self.model) else 'Simple'
                    }
                    
                    index_file = os.path.join(output_dir, f'{filename_without_ext}_index.json')
                    with open(index_file, 'w', encoding='utf-8') as f:
                        json.dump(index_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"[成功] {filename}: {npy_file} ({len(headers)} 个表头)")
                
                # 保存混合文件的关联矩阵（如果有多个文件）
                if len(self.file_header_vectors) > 1:
                    # 生成混合文件名：health_data+users
                    filenames = sorted(self.file_header_vectors.keys())
                    mixed_name = '+'.join([os.path.splitext(f)[0] for f in filenames])
                    
                    # 保存所有表头的合并向量
                    all_headers = []
                    all_vectors = []
                    header_to_file = {}  # 表头 -> 文件名映射
                    
                    for filename, header_vecs in self.file_header_vectors.items():
                        for header, vec in header_vecs.items():
                            if header not in all_headers:
                                all_headers.append(header)
                                all_vectors.append(vec)
                            header_to_file[header] = filename
                    
                    if all_headers:
                        vectors_matrix = np.array(all_vectors)
                        
                        # 保存混合向量文件：health_data+users_vectors.npy
                        mixed_npy = os.path.join(output_dir, f'{mixed_name}_vectors.npy')
                        np.save(mixed_npy, vectors_matrix)
                        
                        # 保存混合索引：health_data+users_index.json
                        mixed_index = {
                            'mixed_files': filenames,
                            'headers': all_headers,
                            'header_to_file': header_to_file,
                            'vector_dim': vectors_matrix.shape[1],
                            'total_headers': len(all_headers)
                        }
                        
                        mixed_index_file = os.path.join(output_dir, f'{mixed_name}_index.json')
                        with open(mixed_index_file, 'w', encoding='utf-8') as f:
                            json.dump(mixed_index, f, ensure_ascii=False, indent=2)
                        
                        print(f"[成功] 混合文件: {mixed_npy} ({len(all_headers)} 个表头)")
            
            return True
        
        except Exception as e:
            print(f"[错误] 保存失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def calculate_similarity(self, header1: str, header2: str) -> float:
        """计算两个表头之间的相似度"""
        if header1 not in self.header_vectors:
            self.header_vectors[header1] = self.encode_header(header1)
        if header2 not in self.header_vectors:
            self.header_vectors[header2] = self.encode_header(header2)
        
        vec1 = self.header_vectors[header1]
        vec2 = self.header_vectors[header2]
        
        # 余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def find_similar_headers(self, query_header: str, top_k: int = 5) -> List[Dict]:
        """查找与查询表头相似的表头"""
        if not self.header_vectors:
            print("[错误] 请先加载表头")
            return []
        
        query_vec = self.encode_header(query_header)
        similarities = []
        
        for header, vec in self.header_vectors.items():
            if header == query_header:
                continue
            
            sim = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec)))
            
            # 查找表头所属的文件
            files = []
            for filename, headers in self.file_header_vectors.items():
                if header in headers:
                    files.append(filename)
            
            similarities.append({
                'header': header,
                'similarity': sim,
                'file': files[0] if files else '未知'
            })
        
        similarities.sort(key=lambda x: -x['similarity'])
        return similarities[:top_k]
    
    def print_statistics(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("              表头向量化统计")
        print("=" * 60)
        
        print(f"\n📁 处理的文件: {len(self.file_header_vectors)} 个")
        print(f"📊 独特表头数量: {len(self.header_vectors)} 个")
        
        if self.header_vectors:
            first_vec = next(iter(self.header_vectors.values()))
            print(f"🔢 向量维度: {len(first_vec)}")
            print(f"🧠 使用模型: {'BERT-base-chinese' if (TRANSFORMERS_AVAILABLE and self.model) else 'Simple'}")
        
        # 显示部分表头示例
        if self.header_vectors:
            sample_headers = list(self.header_vectors.keys())[:10]
            print(f"\n📝 表头示例 ({min(len(self.header_vectors), 10)} 个):")
            for header in sample_headers:
                print(f"  - {header}")


def main():
    """主函数"""
    print("=" * 60)
    print("        表头向量化编码工具")
    print("=" * 60)
    print("功能: 将数据表头转换为向量表示")
    print("支持: .xlsx, .xls, .csv")
    print("=" * 60)
    
    encoder = HeaderEmbeddingEncoder()
    
    while True:
        try:
            command = input("\n> ").strip()
            if not command:
                continue
            
            parts = command.split()
            cmd = parts[0].lower()
            
            if cmd in ['exit', 'q']:
                print("\n👋 退出程序")
                break
            
            elif cmd == 'encode':
                if len(parts) < 2:
                    print("用法: encode <目录路径>")
                    continue
                directory_path = ' '.join(parts[1:])
                encoder.encode_directory(directory_path)
            
            elif cmd == 'save':
                if len(parts) < 2:
                    print("用法: save <输出目录>")
                    continue
                output_dir = ' '.join(parts[1:])
                encoder.save_embeddings(output_dir)
            
            elif cmd == 'similarity':
                if len(parts) < 3:
                    print("用法: similarity <表头1> <表头2>")
                    continue
                header1 = parts[1]
                header2 = parts[2]
                sim = encoder.calculate_similarity(header1, header2)
                print(f"\n'{header1}' 与 '{header2}' 的相似度: {sim:.4f}")
            
            elif cmd == 'find':
                if len(parts) < 2:
                    print("用法: find <表头> [top_k]")
                    continue
                query = parts[1]
                top_k = int(parts[2]) if len(parts) > 2 else 5
                results = encoder.find_similar_headers(query, top_k)
                print(f"\n与 '{query}' 相似的表头:")
                for i, res in enumerate(results, 1):
                    print(f"  {i}. {res['header']} (相似度: {res['similarity']:.4f})")
            
            elif cmd == 'stats':
                encoder.print_statistics()
            
            elif cmd == 'help':
                print("""
表头向量化编码工具命令:
  encode <目录路径>      - 编码目录中所有文件的表头
  save <输出目录>        - 保存向量化结果
  similarity <h1> <h2>   - 计算两个表头的相似度
  find <表头> [top_k]    - 查找相似表头（默认top_k=5）
  stats                  - 显示统计信息
  help                   - 显示此帮助信息
  exit / q               - 退出程序
""")
            
            else:
                print(f"未知命令: {cmd}")
                print("输入 'help' 查看命令列表")
        
        except KeyboardInterrupt:
            print("\n\n👋 退出程序")
            break
        except Exception as e:
            print(f"[错误] {e}")


if __name__ == '__main__':
    main()
import sys
import os
import json
import re
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp.code import tokenize, encode_texts_with_position
from nlp.clear import TextCleaner
from nlp.understand import SentimentAnalyzer, TransformerGenerator
from nlp.vector_db import VectorDB
from nlp.excel.header_embedding import HeaderEmbeddingEncoder
from nlp.excel.header_matrix import HeaderMatrixAnalyzer
from nlp.excel.table_retriever import TableDataRetriever
import re


class DataFileProcessor:
    """数据文件处理器 - 处理Excel/CSV文件的表头向量化和关联分析"""
    
    def __init__(self):
        self.encoder = HeaderEmbeddingEncoder()
        self.matrix_analyzer = HeaderMatrixAnalyzer()
    
    def process_files(self, input_dir: str, output_dir: str = None):
        """处理目录中的所有数据文件"""
        print(f"\n" + "="*60)
        print("          数据文件向量处理")
        print(f"="*60)
        
        # 加载文件并构建关联矩阵
        self.matrix_analyzer.load_files_from_directory(input_dir)
        self.matrix_analyzer.build_association_matrix()
        
        # 向量化编码
        self.encoder.encode_directory(input_dir)
        
        # 显示统计信息
        total_files = len(self.matrix_analyzer.file_list)
        total_headers = len(self.matrix_analyzer.all_headers)
        
        print(f"\n[统计] 文件数量: {total_files}")
        print(f"[统计] 表头总数: {total_headers}")
        
        # 查找公共表头
        common_headers = self.matrix_analyzer.find_common_headers(min_files=2)
        if common_headers:
            print(f"\n[关联] 公共表头 ({len(common_headers)} 个):")
            for header, count in common_headers:
                print(f"  - {header}: 出现在 {count} 个文件中")
        else:
            print("\n[关联] 无公共表头")
        
        # 分析文件关系
        relationships = self.matrix_analyzer.find_file_relationships()
        if relationships:
            print(f"\n[关系] 文件间关系分析:")
            for rel in relationships[:5]:
                print(f"  - {rel['file1']} | {rel['file2']}")
                print(f"    共享表头: {rel['shared_headers']} 个, 相似度: {rel['similarity']:.2%}")
        
        # 如果指定了输出目录，保存结果
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成混合文件名：health_data+users
            filenames = sorted(self.matrix_analyzer.file_list)
            mixed_name = '+'.join([os.path.splitext(f)[0] for f in filenames])
            
            # 保存矩阵：health_data+users_matrix.csv
            matrix_file = os.path.join(output_dir, f'{mixed_name}_matrix.csv')
            self.matrix_analyzer.save_matrix(matrix_file, 'csv')
            
            # 保存共现矩阵：health_data+users_cooccurrence.csv
            cooccurrence_file = os.path.join(output_dir, f'{mixed_name}_cooccurrence.csv')
            self.matrix_analyzer.save_cooccurrence_matrix(cooccurrence_file)
            
            # 保存向量文件（每个CSV一个npy + 混合文件）
            self.encoder.save_embeddings(output_dir)
            
            print(f"\n[保存] 结果已保存到: {output_dir}")
        
        print(f"\n" + "="*60)
        print("          数据文件处理完成")
        print(f"="*60)
    
    def find_similar_headers(self, query_header: str, top_k: int = 5):
        """查找相似表头"""
        if not self.encoder.header_vectors:
            print("[错误] 请先加载文件")
            return
        
        results = self.encoder.find_similar_headers(query_header, top_k)
        print(f"\n与 '{query_header}' 相似的表头:")
        for i, res in enumerate(results, 1):
            print(f"  {i}. {res['header']} (相似度: {res['similarity']:.4f})")
    
    def compare_headers(self, header1: str, header2: str):
        """比较两个表头的相似度"""
        sim = self.encoder.calculate_similarity(header1, header2)
        print(f"\n'{header1}' 与 '{header2}' 的相似度: {sim:.4f}")


class Chatbot:
    # 表头相似度阈值，高于此值才回调读取表格数据
    HEADER_SIMILARITY_THRESHOLD = 0.3  # 降低阈值，提高召回率

    def __init__(self):
        self.vector_db = VectorDB()
        self.cleaner = TextCleaner()
        self.analyzer = SentimentAnalyzer()
        self.generator = TransformerGenerator()
        self.vocab = self.vector_db.get_vocab()

        # 延迟初始化数据文件处理器（避免重复加载模型）
        self.data_processor = None
        self.data_loaded = False

        # 表格数据回调检索器
        self.table_retriever = None

        print(f"\n[INFO] 知识库对话系统已启动")
        print(f"       数据库记录: {self.vector_db.count()} 条 (段落级)")
        print(f"       词汇表大小: {len(self.vocab)}")
        print(f"       回答生成: 思考式归纳")
        print(f"       数据文件: 按需加载 (含表格数据回调)")

    def _ensure_data_processor(self):
        """确保数据文件处理器和表格检索器已初始化"""
        if self.data_processor is None:
            try:
                self.data_processor = DataFileProcessor()
                data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'excel', 'data')
                if os.path.exists(data_dir):
                    self.data_processor.matrix_analyzer.load_files_from_directory(data_dir)
                    self.data_processor.matrix_analyzer.build_association_matrix()
                    self.data_processor.encoder.encode_directory(data_dir)
                    self.data_loaded = True
                    print(f"[INFO] 已加载数据文件: {len(self.data_processor.matrix_analyzer.file_list)} 个文件")

                    # 初始化表格数据回调检索器
                    self.table_retriever = TableDataRetriever(data_dir)
                    self.table_retriever.load_all()
            except Exception as e:
                print(f"[INFO] 数据文件加载失败: {str(e)[:50]}")
                self.data_processor = None

    def _should_retrieve_table_data(self, data_results: list) -> bool:
        """判断是否需要回调读取表格数据：至少一个表头相似度超过阈值"""
        for res in data_results:
            if res.get('similarity', 0) >= self.HEADER_SIMILARITY_THRESHOLD:
                return True
        return False

    @staticmethod
    def _classify_data_direction(query: str, knowledge_chunks: list = None) -> str:
        """
        动态推断查询方向：从查询语句+知识库内容中自动学习
        返回: 'negative' | 'positive' | 'filter' | 'general'
        """
        # 1. 先从查询关键词推断
        if re.search(r'不适合|不能|禁忌|避免|少吃|不可以|不宜|不可|禁止|有害|危险|排除|剔除', query):
            return 'negative'
        if re.search(r'适合|可以|推荐|适宜|能吃|多吃|好处|优选|选择', query):
            return 'positive'
        if re.search(r'有哪些|什么|列表|全部|统计|情况|状态|身体状况|健康状况|身体情况|健康数据|在校|全员|所有员工', query):
            return 'filter'

        # 2. 如果查询不明确，从知识库内容推断主题倾向
        if knowledge_chunks:
            neg_count = pos_count = 0
            for chunk in knowledge_chunks:
                content = chunk.get('content', '') or chunk.get('preview', '')
                if re.search(r'(?:禁忌|避免|禁止|不宜|风险|有害|危险)', content):
                    neg_count += 1
                if re.search(r'(?:适合|推荐|有益|好处|推荐)', content):
                    pos_count += 1
            if neg_count > pos_count:
                return 'negative'
            elif pos_count > neg_count:
                return 'positive'

        return 'general'

    @staticmethod
    def _apply_common_sense_rules(field_name: str, value: float) -> str:
        """
        应用通用业务规则判断数值字段方向（非固定模板，而是常识性规则）
        这些规则适用于大多数业务场景，不限定特定主题
        """
        field_lower = field_name.lower()
        
        # 年龄类字段：高龄通常需要注意
        if '年龄' in field_name or 'age' in field_lower:
            if value >= 65:
                return 'negative'  # 高龄
            elif value >= 60:
                return 'neutral'   # 老年
            else:
                return 'positive'  # 正常
        
        # 血压类字段：高血压需要注意
        if '血压' in field_name or 'blood_pressure' in field_lower or 'bp' in field_lower:
            # 简单解析：如果是收缩压或舒张压的单一值
            if value >= 140:
                return 'negative'
            elif value >= 130:
                return 'neutral'
            else:
                return 'positive'
        
        # 默认：统计正常范围内即为正常
        return 'positive'

    def _extract_knowledge_insights(self, knowledge_chunks: list) -> list:
        """
        从知识库段落中动态提取业务相关洞察（不限定任何主题）
        返回: [{'text': str, 'direction': 'positive'|'negative'|'neutral', 'source': str}]
        """
        insights = []
        for chunk in knowledge_chunks:
            content = chunk.get('content', '') or chunk.get('preview', '')
            section = chunk.get('chunk_section', '')
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                # 跳过食材/做法类行（避免食材配方被当成建议输出）
                if re.search(r'(?:食材|[食材|原料|材料][\uff1a：]|五花肉|\d+g、|g、|\d+勺|冰糖|\u751f姜|大葟|八角|桂皮|生抽|老抽|料酒)', line):
                    continue
                # 检测是否包含建议/评价类语句
                has_advice = bool(re.search(
                    r'(?:适合|推荐|应|需|避免|控制|限制|禁忌|不宜|可以|有益|适量|严格|禁止|有害|风险|危险|建议|优先|优选)',
                    line
                ))
                if not has_advice:
                    continue
                # 判断方向
                if re.search(r'(?:避免|控制|限制|禁忌|不宜|不可|禁止|有害|风险|危险|超标|警告|不应)', line):
                    direction = 'negative'
                elif re.search(r'(?:适合|推荐|可以|有益|适量|建议|优先|优选|核心获益|好处)', line):
                    direction = 'positive'
                else:
                    direction = 'neutral'
                insights.append({
                    'text': line[:300],
                    'direction': direction,
                    'source': section,
                })
        return insights

    def _build_record_profile(self, record: dict, all_records: list = None) -> dict:
        """
        为一条记录建立数据画像：完全数据驱动，不预设任何业务场景
        自动识别字段类型，用统计学方法判断异常值
        """
        # 排除无关字段（技术字段，非业务字段）
        skip_fields = {'password', 'image', 'created_at', 'updated_at', 'account'}
        
        # 识别名称字段（用于显示）
        name_fields = {'username', 'id', '姓名', 'name', '标题', 'title', '编号', 'code'}
        name = ''
        for nf in ['name', '姓名', 'username', 'title', '标题']:
            if nf in record and record[nf]:
                name = record[nf]
                break

        # 收集有效数据字段
        data_items = []
        for k, v in record.items():
            if k in skip_fields or not v or str(v).strip() == '':
                continue
            data_items.append((k, str(v).strip()))

        # 如果有全部记录，计算统计信息用于异常值检测
        field_stats = {}
        if all_records and len(all_records) > 5:
            for k, v in data_items:
                try:
                    vals = [float(r.get(k, 0)) for r in all_records if r.get(k)]
                    if len(vals) > 5:
                        import numpy as np
                        arr = np.array(vals)
                        field_stats[k] = {
                            'mean': np.mean(arr),
                            'std': np.std(arr),
                            'min': np.min(arr),
                            'max': np.max(arr),
                            'q1': np.percentile(arr, 25),
                            'q3': np.percentile(arr, 75),
                        }
                except (ValueError, TypeError):
                    pass

        # 动态分析每个字段，生成条件标签
        conditions = []
        for k, v in data_items:
            v_str = str(v).strip()
            
            # 特殊处理：血压格式 "118/78"
            if '血压' in k or 'blood_pressure' in k.lower() or 'bp' in k.lower():
                bp_match = re.match(r'(\d+)\s*/\s*(\d+)', v_str)
                if bp_match:
                    systolic = int(bp_match.group(1))
                    diastolic = int(bp_match.group(2))
                    if systolic >= 140 or diastolic >= 90:
                        conditions.append({
                            'label': f'{k}偏高({v_str})',
                            'field': k, 'value': v_str,
                            'direction': 'negative',
                            'detail': f'收缩压{systolic}/舒张压{diastolic}，属高血压',
                        })
                    elif systolic >= 130 or diastolic >= 85:
                        conditions.append({
                            'label': f'{k}偏高({v_str})',
                            'field': k, 'value': v_str,
                            'direction': 'neutral',
                            'detail': f'收缩压{systolic}/舒张压{diastolic}，血压偏高',
                        })
                    else:
                        conditions.append({
                            'label': f'{k}:{v_str}',
                            'field': k, 'value': v_str,
                            'direction': 'positive',
                            'detail': f'收缩压{systolic}/舒张压{diastolic}，正常范围',
                        })
                continue
            
            # 尝试解析为数值
            try:
                num_val = float(v_str)
                
                # 如果有统计信息，用 IQR 方法检测异常值
                if k in field_stats:
                    stats = field_stats[k]
                    iqr = stats['q3'] - stats['q1']
                    lower_bound = stats['q1'] - 1.5 * iqr
                    upper_bound = stats['q3'] + 1.5 * iqr
                    
                    if num_val > upper_bound:
                        conditions.append({
                            'label': f'{k}偏高({v})',
                            'field': k, 'value': v,
                            'direction': 'negative',
                            'detail': f'{k} = {v}，高于正常范围(>{upper_bound:.1f})',
                        })
                    elif num_val < lower_bound:
                        conditions.append({
                            'label': f'{k}偏低({v})',
                            'field': k, 'value': v,
                            'direction': 'negative',
                            'detail': f'{k} = {v}，低于正常范围(<{lower_bound:.1f})',
                        })
                    else:
                        # 在统计正常范围内，但可进一步基于常识判断
                        # 例如：年龄>=60、血压>=130等（这些是通用业务规则，非固定模板）
                        direction = self._apply_common_sense_rules(k, num_val)
                        conditions.append({
                            'label': f'{k}:{v}',
                            'field': k, 'value': v,
                            'direction': direction,
                            'detail': f'{k} = {v}',
                        })
                else:
                    # 无统计信息，仅记录
                    conditions.append({
                        'label': f'{k}:{v}',
                        'field': k, 'value': v,
                        'direction': 'neutral',
                        'detail': f'{k} = {v}',
                    })
            except ValueError:
                # 非数值字段，直接记录
                conditions.append({
                    'label': f'{k}:{v}',
                    'field': k, 'value': v,
                    'direction': 'neutral',
                    'detail': f'{k} = {v}',
                })

        # 判断是否有风险/异常
        has_risk = any(c['direction'] == 'negative' for c in conditions)
        is_normal = not has_risk

        # 数据摘要（排除名称相关字段）
        display_fields = [(k, v) for k, v in data_items if k not in name_fields]
        data_summary = '，'.join(f'{k}:{v}' for k, v in display_fields[:5])

        return {
            'name': name,
            'data_summary': data_summary,
            'conditions': conditions,
            'has_risk': has_risk,
            'is_normal': is_normal,
        }

    def _analyze_data(self, query: str, data_records: dict,
                      knowledge_chunks: list) -> dict:
        """
        数据驱动的记录分析（不限定任何业务场景）
        返回: {
            'direction': str,              # 查询方向
            'total': int,                  # 总记录数
            'knowledge_insights': list,    # 知识库洞察
            'profiles': list,              # 所有记录画像
            'filtered': list,              # 按方向筛选的画像
        }
        """
        records = data_records.get('records', [])
        if not records:
            return None

        # 1. 判断查询方向
        direction = self._classify_data_direction(query, knowledge_chunks)

        # 2. 从知识库动态提取洞察
        knowledge_insights = self._extract_knowledge_insights(knowledge_chunks)

        # 3. 为每条记录建立画像
        profiles = [self._build_record_profile(rec, records) for rec in records]

        # 4. 根据查询方向筛选
        if direction == 'negative':
            filtered = [p for p in profiles if p['has_risk']]
        elif direction == 'positive':
            filtered = [p for p in profiles if p['is_normal']]
        elif direction == 'filter':
            # 显示所有记录，按条件分组
            filtered = profiles
        else:
            filtered = profiles

        return {
            'direction': direction,
            'total': len(records),
            'knowledge_insights': knowledge_insights,
            'profiles': profiles,
            'filtered': filtered,
        }

    def process_query(self, query: str) -> dict:
        cleaned = self.cleaner.clean_knowledge_text(query)
        sentiment = self.analyzer.analyze(query)
        tokens = tokenize(query)
        
        # 提取关键词（用于表头匹配）
        keywords = self._extract_keywords(query)

        # ---- 第一步：文件级别匹配 ----
        # 1. 匹配文档文件名（从vector_db的index.json）
        matched_doc_files = self._match_files_by_name(query, 'knowledge')
        
        # 2. 匹配数据文件名（从excel/output的索引文件）
        matched_data_files = self._match_files_by_name(query, 'data')

        # 保存带评分的匹配文件列表（兜底时按评分排序用）
        matched_doc_files_scored = self._match_files_by_name_scored(query, 'knowledge')

        # ---- 第二步：在匹配的文件内检索 ----
        embedding, _ = encode_texts_with_position(
            [cleaned],
            max_features=5000,
            ngram_range=(1, 2),
            position_weight=0.1,
            vocab=self.vocab
        )

        # 段落级分组检索（只检索匹配的文档）
        grouped_results = self.vector_db.search_grouped_by_doc(
            embedding[0], top_k=5, use_attention=True,
            query_tokens=tokens, max_chunks_per_doc=3
        )
        
        # 如果有匹配的文件，过滤结果
        if matched_doc_files:
            grouped_results = [
                doc for doc in grouped_results
                if any(mf in doc.get('doc_title', '') or mf in doc.get('filename', '')
                       for mf in matched_doc_files)
            ]

        # 数据文件表头检索（只检索匹配的数据文件）
        data_results = []
        self._ensure_data_processor()
        if self.data_processor and self.data_processor.encoder.header_vectors:
            # 优化：只从匹配的数据文件中查找相关表头
            if matched_data_files and keywords:
                # 从匹配的文件中提取所有表头
                matched_headers = []
                for filename in matched_data_files:
                    for file_key, headers in self.data_processor.encoder.file_header_vectors.items():
                        if filename in file_key:
                            matched_headers.extend(headers.keys())
                
                # 用查询的关键词去匹配表头（而不是整个查询语句）
                if matched_headers:
                    # 计算关键词与表头的匹配度
                    for header in matched_headers:
                        # 只要有关键词匹配就加入结果
                        matched_kws = [kw for kw in keywords if kw in header]
                        if matched_kws:
                            # 查找该表头所属的文件
                            source_file = '未知'
                            for file_key, headers in self.data_processor.encoder.file_header_vectors.items():
                                if header in headers:
                                    source_file = file_key
                                    break
                            
                            # 相似度 = 匹配的关键词数量（最少1个）
                            match_count = len(matched_kws)
                            data_results.append({
                                'header': header,
                                'similarity': min(match_count * 0.5, 1.0),  # 1个词=0.5, 2个词=1.0
                                'file': source_file,
                                'match_type': 'keyword',
                                'matched_keywords': matched_kws
                            })
                    
                    # 按相似度排序
                    data_results = sorted(data_results, key=lambda x: -x['similarity'])
            
            # 兼容处理：查询含有数据相关词时，主动对所有数据表做语义检索（不要求知识库命中）
            query_needs_data = bool(re.search(
                r'员工|人员|哪些|谁|哪个|列出|有哪|姓名|名单|人数|多少人'
                r'|身体状况|健康状况|血压|年龄|体重|血糖|身体情况|健康数据|健康信息', query
            ))
            if not data_results and not matched_data_files and query_needs_data:
                try:
                    all_header_results = self.data_processor.encoder.find_similar_headers(
                        query, top_k=10
                    )
                    # 业务相关表头白名单：只有这些表头才真正与健康/业务有关，过滤握 id/password 等无关字段
                    BUSINESS_HEADERS = {
                        '姓名', '年龄', '血压', '体重', '血糖', '心率', '血脂', '胆固醇',
                        '血红蛋白', '白细胞', '血尿酸', '水分', '肏酤甘油', '体脂率',
                        'bmi', '山脸', '性别', '职位', '部门', '工龄', '学历'
                    }
                    for res in all_header_results:
                        header = res['header']
                        sim = res.get('similarity', 0)
                        # 只收录明确业务相关表头（直接在白名单里）
                        if header in BUSINESS_HEADERS and sim >= self.HEADER_SIMILARITY_THRESHOLD:
                            source_file = '未知'
                            for file_key, hdrs in self.data_processor.encoder.file_header_vectors.items():
                                if header in hdrs:
                                    source_file = file_key
                                    break
                            data_results.append({
                                'header': header,
                                'similarity': sim,
                                'file': source_file,
                                'match_type': 'semantic',
                                'matched_keywords': []
                            })
                except Exception:
                    pass

        return {
            'original': query,
            'cleaned': cleaned,
            'tokens': tokens,
            'sentiment': sentiment,
            'matched_doc_files': matched_doc_files,
            'matched_data_files': matched_data_files,
            'grouped_results': grouped_results,
            'data_results': data_results,
            'data_records': None,
            'vector_dim': embedding.shape[1]
        }
    
    def _extract_keywords(self, query: str) -> set:
        """提取查询关键词"""
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                     '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                     '自己', '这', '那', '哪些', '什么', '怎么', '如何', '谁', '做', '制作'}
        
        keywords = set()
        
        # 提取所有2字词语
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', query)
        for i in range(len(chinese_chars) - 1):
            word = ''.join(chinese_chars[i:i+2])
            if word not in stop_words:
                keywords.add(word)
        
        # 提取所有3字词语
        for i in range(len(chinese_chars) - 2):
            word = ''.join(chinese_chars[i:i+3])
            if word not in stop_words:
                keywords.add(word)
        
        # 匹配英文单词
        for match in re.finditer(r'[a-zA-Z]{2,}', query):
            keywords.add(match.group())
        
        # 匹配数字
        for match in re.finditer(r'\d{2,}', query):
            keywords.add(match.group())
        
        return keywords
    
    def _match_files_by_name(self, query: str, file_type: str = 'knowledge') -> list:
        """
        两阶段文件匹配：语义匹配 + 关键词匹配
        file_type: 'knowledge' | 'data'
        """
        import re
        
        # ---- 提取关键词 ----
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                     '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                     '自己', '这', '那', '哪些', '什么', '怎么', '如何', '谁'}
        
        keywords = set()
        for match in re.finditer(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', query):
            word = match.group()
            if word not in stop_words:
                keywords.add(word)
        
        matched_files = []
        
        # ---- 第一阶段：语义匹配（向量相似度） ----
        try:
            # 将查询编码为向量
            cleaned = self.cleaner.clean_knowledge_text(query)
            embedding, _ = encode_texts_with_position(
                [cleaned],
                max_features=5000,
                ngram_range=(1, 2),
                position_weight=0.1,
                vocab=self.vocab
            )
            query_vec = embedding[0]
            
            if file_type == 'knowledge':
                # 从 vector_db/index.json 读取文档
                index_file = os.path.join(self.vector_db.db_path, 'index.json')
                if os.path.exists(index_file):
                    with open(index_file, 'r', encoding='utf-8') as f:
                        index_data = json.load(f)
                    
                    for filename, doc_info in index_data.items():
                        title = doc_info.get('title', '')
                        
                        # 语义匹配：标题向量 vs 查询向量
                        title_embedding, _ = encode_texts_with_position(
                            [title], max_features=5000, ngram_range=(1, 2),
                            position_weight=0.1, vocab=self.vocab
                        )
                        title_vec = title_embedding[0]
                        
                        # 计算余弦相似度
                        dot_product = np.dot(query_vec, title_vec)
                        norm1 = np.linalg.norm(query_vec)
                        norm2 = np.linalg.norm(title_vec)
                        semantic_sim = dot_product / (norm1 * norm2) if (norm1 > 0 and norm2 > 0) else 0
                        
                        # 关键词匹配
                        keyword_score = 0
                        if keywords:
                            match_count = sum(1 for kw in keywords if kw in filename or kw in title)
                            keyword_score = match_count / len(keywords)
                        
                        # 综合得分：语义70% + 关键词30%
                        final_score = semantic_sim * 0.7 + keyword_score * 0.3
                        
                        if final_score >= 0.3:  # 降低阈值，提高召回率
                            matched_files.append({
                                'filename': filename,
                                'title': title,
                                'match_score': final_score,
                                'semantic_score': semantic_sim,
                                'keyword_score': keyword_score
                            })
            
            elif file_type == 'data':
                # 从 excel/output 读取数据文件索引
                output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'excel', 'output')
                if os.path.exists(output_dir):
                    for f in os.listdir(output_dir):
                        if f.endswith('_index.json') and '+' not in f:
                            with open(os.path.join(output_dir, f), 'r', encoding='utf-8') as fp:
                                idx = json.load(fp)
                            
                            csv_filename = idx.get('filename', '')
                            headers = idx.get('headers', [])
                            
                            # 语义匹配：文件名+表头 vs 查询
                            text_to_match = csv_filename + ' ' + ' '.join(headers)
                            text_embedding, _ = encode_texts_with_position(
                                [text_to_match], max_features=5000, ngram_range=(1, 2),
                                position_weight=0.1, vocab=self.vocab
                            )
                            text_vec = text_embedding[0]
                            
                            dot_product = np.dot(query_vec, text_vec)
                            norm1 = np.linalg.norm(query_vec)
                            norm2 = np.linalg.norm(text_vec)
                            semantic_sim = dot_product / (norm1 * norm2) if (norm1 > 0 and norm2 > 0) else 0
                            
                            # 关键词匹配：只看文件名
                            keyword_score = 0
                            if keywords:
                                match_count = sum(1 for kw in keywords if kw in csv_filename)
                                keyword_score = match_count / len(keywords)
                            
                            final_score = semantic_sim * 0.7 + keyword_score * 0.3
                            
                            if final_score >= 0.3:
                                matched_files.append({
                                    'filename': csv_filename,
                                    'headers': headers,
                                    'match_score': final_score,
                                    'semantic_score': semantic_sim,
                                    'keyword_score': keyword_score
                                })
        
        except Exception as e:
            print(f"[警告] 语义匹配失败: {str(e)}，降级到关键词匹配")
        
        # ---- 排序并返回 ----
        matched_files = sorted(matched_files, key=lambda x: -x['match_score'])
        return [f['filename'] for f in matched_files]

    def _match_files_by_name_scored(self, query: str, file_type: str = 'knowledge') -> list:
        """返回带评分的匹配文件列表（兑底时按评分取最佳文件用）"""
        matched_files = []
        try:
            cleaned = self.cleaner.clean_knowledge_text(query)
            embedding, _ = encode_texts_with_position(
                [cleaned], max_features=5000, ngram_range=(1, 2),
                position_weight=0.1, vocab=self.vocab
            )
            query_vec = embedding[0]
            stop_words = {'\u7684', '\u4e86', '\u5728', '\u662f', '\u6211', '\u6709', '\u548c', '\u4e0d', '\u4eba'}
            keywords = {m.group() for m in re.finditer(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', query)
                        if m.group() not in stop_words}

            if file_type == 'knowledge':
                index_file = os.path.join(self.vector_db.db_path, 'index.json')
                if os.path.exists(index_file):
                    with open(index_file, 'r', encoding='utf-8') as f:
                        index_data = json.load(f)
                    for filename, doc_info in index_data.items():
                        title = doc_info.get('title', '')
                        title_emb, _ = encode_texts_with_position(
                            [title], max_features=5000, ngram_range=(1, 2),
                            position_weight=0.1, vocab=self.vocab
                        )
                        title_vec = title_emb[0]
                        n1, n2 = np.linalg.norm(query_vec), np.linalg.norm(title_vec)
                        sem = float(np.dot(query_vec, title_vec) / (n1 * n2)) if n1 > 0 and n2 > 0 else 0
                        kw_score = sum(1 for kw in keywords if kw in filename or kw in title) / len(keywords) if keywords else 0
                        score = sem * 0.7 + kw_score * 0.3
                        if score >= 0.3:
                            matched_files.append({'filename': filename, 'match_score': score})
        except Exception:
            pass
        return sorted(matched_files, key=lambda x: -x['match_score'])

    def chat(self, query: str):
        print("\n" + "="*60)
        print(f"【用户输入】{query}")
        print("="*60)

        # ---- 检索阶段 ----
        result = self.process_query(query)
        tokens = result['tokens']
        grouped = result['grouped_results']
        data_results = result.get('data_results', [])
        matched_doc_files = result.get('matched_doc_files', [])
        matched_data_files = result.get('matched_data_files', [])

        SIMILARITY_THRESHOLD = 0.02

        # 收集所有达标段落
        all_valid_chunks = []
        for doc in grouped:
            for chunk in doc['chunks']:
                if chunk.get('similarity', 0) >= SIMILARITY_THRESHOLD:
                    kw = chunk.get('keyword_matching', {})
                    match_ratio = kw.get('match_ratio', 0.0)
                    doc_title = doc.get('doc_title', '') or doc.get('filename', '')
                    # 如果文件已明确匹配，降低 match_ratio 阈值为 0.0（即直接接受该文件内所有段落）
                    is_matched_file = any(
                        mf in doc_title
                        for mf in matched_doc_files
                    ) if matched_doc_files else False
                    effective_threshold = 0.0 if is_matched_file else 0.1
                    if match_ratio >= effective_threshold:
                        all_valid_chunks.append(chunk)

        # 兑底逻辑：文件名匹配成功但向量检索段落为空，按评分高低直接按文件名取段落
        if not all_valid_chunks and matched_doc_files:
            # 优先取评分最高的匹配文件（而非列表第一个）
            sorted_files = [{'filename': f, 'match_score': 0} for f in matched_doc_files]
            sorted_files = sorted(sorted_files, key=lambda x: -x.get('match_score', 0))
            for item in sorted_files:
                mf = item.get('filename', item) if isinstance(item, dict) else item
                fallback_chunks = self.vector_db.get_chunks_by_filename(
                    mf, max_chunks=5, query_tokens=tokens
                )
                all_valid_chunks.extend(fallback_chunks)
            if all_valid_chunks:
                print(f"[INFO] 向量检索段落为空，已兑底加载 {len(all_valid_chunks)} 个段落")

        # ---- 表格数据回调检索 ----
        data_analysis = None
        data_records_info = None
        if data_results and self._should_retrieve_table_data(data_results) and self.table_retriever:
            # 回调读取表格数据
            data_records_info = self.table_retriever.retrieve(data_results, top_n=200)

            if data_records_info and data_records_info.get('records'):
                # 分析数据，结合知识库
                data_analysis = self._analyze_data(
                    query, data_records_info, all_valid_chunks
                )

        # ---- 生成回答（思考式，含数据分析）----
        # min_match_ratio=0.0: 上面已完成阈值过滤，不需要二次过滤
        response = self.generator.answer_with_context(
            query, all_valid_chunks, data_analysis=data_analysis,
            min_match_ratio=0.0
        )

        thinking = response.get('thinking', '')
        answer = response.get('answer', '')

        # 构建完整的思考过程（包含文件匹配、数据文件检索和数据分析）
        thinking_lines = [line for line in thinking.split('\n') if line.strip()]
        
        # 添加文件匹配信息
        if matched_doc_files or matched_data_files:
            thinking_lines.append("")
            thinking_lines.append("文件匹配结果（语义+关键词）：")
            if matched_doc_files:
                thinking_lines.append(f"   匹配文档: {', '.join(matched_doc_files)}")
            if matched_data_files:
                thinking_lines.append(f"   匹配数据表: {', '.join(matched_data_files)}")

        # 添加数据文件检索信息
        if data_results:
            thinking_lines.append("")
            thinking_lines.append(f"同时从数据文件中检索到 {len(data_results)} 个相关表头：")
            for i, res in enumerate(data_results, 1):
                thinking_lines.append(
                    f"   [{i}] '{res['header']}' "
                    f"(相似度: {res['similarity']:.2%}, 文件: {res['file']})"
                )

        # 添加数据回调分析信息
        if data_records_info:
            thinking_lines.append("")
            thinking_lines.append(
                f"表头相似度超过阈值，回调读取表格数据："
                f"{data_records_info['total']} 条记录"
            )
            if data_records_info.get('join_info'):
                thinking_lines.append(
                    f"   表连接方式: {data_records_info['join_info']}"
                )

        if data_analysis:
            direction_desc = {
                'negative': '负面/排除',
                'positive': '正面/推荐',
                'filter': '筛选/列表',
                'general': '综合'
            }
            thinking_lines.append("")
            thinking_lines.append("数据分析结果：")
            thinking_lines.append(
                f"   读取 {data_analysis['total']} 条记录，"
                f"查询方向：{direction_desc.get(data_analysis['direction'], '综合')}"
            )
            risk_count = sum(1 for p in data_analysis['profiles'] if p['has_risk'])
            normal_count = sum(1 for p in data_analysis['profiles'] if p['is_normal'])
            thinking_lines.append(f"   异常: {risk_count} 条, 正常: {normal_count} 条")
            thinking_lines.append(f"   符合查询条件的: {len(data_analysis['filtered'])} 条")

        # 输出思考过程
        print(f"\n[思考过程]")
        print(f"   " + "─" * 60)
        for line in thinking_lines:
            print(f"   │ {line}")
        print(f"   " + "─" * 60)

        # 输出数据文件检索结果（如果有）
        if data_results:
            print(f"\n[数据文件匹配]")
            print(f"   " + "─" * 60)
            for i, res in enumerate(data_results, 1):
                print(f"   │ [{i}] 表头: {res['header']}")
                print(f"   │     相似度: {res['similarity']:.4f}")
                print(f"   │     来源文件: {res['file']}")
            print(f"   " + "─" * 60)

        # 输出最终回答
        print(f"\n[回答]")
        print(f"   " + "─" * 60)
        for line in answer.split('\n'):
            try:
                print(f"   │ {line}")
            except UnicodeEncodeError:
                # Windows 终端编码兼容处理
                print(f"   │ {line.encode('utf-8', errors='replace').decode('gbk', errors='replace')}")
        print(f"   " + "─" * 60)

        print("\n" + "="*60)


def print_help():
    """打印帮助信息"""
    help_text = """
NLP 综合处理系统

命令行参数:
  --chat                - 启动知识库对话模式（默认）
  --data <输入目录> [输出目录]  - 处理数据文件（Excel/CSV表头向量化）
  
示例:
  python total.py                    # 默认启动对话模式
  python total.py --chat             # 启动知识库对话
  python total.py --data ./data      # 处理数据文件，不保存结果
  python total.py --data ./data ./output  # 处理数据文件并保存结果

对话模式命令:
  q / quit              - 退出
  help                  - 显示帮助

数据文件处理功能:
  - 表头提取
  - 关联矩阵构建
  - 向量化编码存储
  - 相似表头查找
"""
    print(help_text)


def main():
    import sys
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    # 如果没有参数或 --chat，启动对话模式
    if not args or args[0] == '--chat':
        vector_db = VectorDB()

        if vector_db.count() == 0:
            print("[错误] 知识库为空，请先运行 process_knowledge.py 构建索引")
            return

        if not vector_db.get_vocab():
            print("[错误] 词汇表为空，请重新构建索引")
            return

        chatbot = Chatbot()

        print("\n" + "="*60)
        print("           知识库对话系统 (思考式回答)")
        print("="*60)
        print("输入问题进行查询，输入 'q' 退出")
        print("="*60)

        while True:
            try:
                query = input("\n您: ").strip()

                if not query:
                    continue

                if query.lower() in ['q', 'quit']:
                    print("\n👋 对话结束")
                    break

                if query.lower() == 'help':
                    print_help()
                    continue

                chatbot.chat(query)

            except EOFError:
                print("\n\n👋 对话结束 (EOF)")
                break
            except KeyboardInterrupt:
                print("\n\n👋 对话结束")
                break
    
    # 处理数据文件模式
    elif args[0] == '--data':
        if len(args) < 2:
            print("[错误] 请指定输入目录")
            print("用法: python total.py --data <输入目录> [输出目录]")
            return
        
        input_dir = args[1]
        output_dir = args[2] if len(args) > 2 else None
        
        processor = DataFileProcessor()
        processor.process_files(input_dir, output_dir)
    
    # 显示帮助
    elif args[0] == '--help' or args[0] == '-h':
        print_help()
    
    else:
        print(f"未知参数: {args[0]}")
        print("使用 --help 查看帮助")


if __name__ == '__main__':
    main()

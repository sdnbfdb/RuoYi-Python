from typing import List, Dict, Union
import os

os.environ['TRANSFORMERS_OFFLINE'] = '0'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class SentimentAnalyzer:
    def __init__(self, model_name: str = "uer/roberta-base-finetuned-dianping-chinese"):
        self.use_bert = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        
        if not TRANSFORMERS_AVAILABLE:
            print("[ERROR] Transformers is NOT installed!")
            print("        Please run: pip install transformers torch")
            return
        
        try:
            nlp_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(nlp_dir, 'model_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            print("[INFO] Loading model: {}".format(model_name))
            print("[INFO] Cache directory: {}".format(cache_dir))
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False
            )
            self.model.to(self.device)
            self.model.eval()
            
            self.use_bert = True
            print("[OK] Loaded BERT model successfully")
            
        except Exception as e:
            print("[ERROR] Failed to load BERT model: {}".format(str(e)[:200]))
            print("[INFO] Trying to download model manually...")
            
            try:
                from huggingface_hub import snapshot_download
                print("[INFO] Downloading model from HF Mirror...")
                snapshot_download(
                    repo_id=model_name,
                    local_dir=cache_dir,
                    local_dir_use_symlinks=False,
                    resume_download=True
                )
                print("[OK] Model downloaded successfully")
                
                self.tokenizer = AutoTokenizer.from_pretrained(
                    cache_dir,
                    local_files_only=True
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    cache_dir,
                    local_files_only=True
                )
                self.model.to(self.device)
                self.model.eval()
                self.use_bert = True
                print("[OK] Loaded BERT model from local files")
                
            except Exception as download_e:
                print("[ERROR] Failed to download model: {}".format(str(download_e)[:200]))
                print("[INFO] Falling back to dictionary-based analysis")
                print("=" * 60)
                print("[MANUAL DOWNLOAD GUIDE]")
                print("Please manually download the model files from:")
                print("  https://hf-mirror.com/{}".format(model_name))
                print("And place them in:")
                print("  {}".format(cache_dir))
                print("Required files:")
                print("  - config.json")
                print("  - pytorch_model.bin")
                print("  - vocab.txt")
                print("=" * 60)
                raise RuntimeError("BERT model is required but not available!")

    def _analyze_bert(self, text: str) -> Dict:
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=512,
            padding='max_length',
            return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
            scores = probabilities.cpu().numpy()[0]

        label_map = {0: '负面', 1: '正面'}
        predicted_label = torch.argmax(logits, dim=1).cpu().item()
        sentiment = label_map[predicted_label]
        confidence = float(scores[predicted_label])

        return {
            'text': text,
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': {
                '负面': float(scores[0]),
                '中性': 0.0,
                '正面': float(scores[1])
            },
            'method': 'BERT'
        }

    def analyze(self, texts: Union[str, List[str]]) -> Union[Dict, List[Dict]]:
        if not self.use_bert:
            raise RuntimeError("BERT model is required but not available!")
        
        if isinstance(texts, str):
            return self._analyze_bert(texts)
        else:
            results = []
            for text in texts:
                results.append(self._analyze_bert(text))
            return results

    def batch_analyze(self, texts: List[str]) -> List[Dict]:
        return self.analyze(texts)


class TransformerGenerator:
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-zh-en"):
        self.use_transformer = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        
        if not TRANSFORMERS_AVAILABLE:
            print("[ERROR] Transformers is NOT installed!")
            print("        Please run: pip install transformers torch")
            return
        
        try:
            nlp_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(nlp_dir, 'model_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            print("[INFO] Loading Transformer generator model: {}".format(model_name))
            print("[INFO] Cache directory: {}".format(cache_dir))
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False
            )
            self.model.to(self.device)
            self.model.eval()
            
            self.use_transformer = True
            print("[OK] Loaded Transformer generator successfully")
            
        except Exception as e:
            print("[ERROR] Failed to load Transformer generator: {}".format(str(e)[:200]))
            print("[INFO] Falling back to rule-based generation")

    def generate(self, query: str, context: str = "", max_length: int = 200) -> str:
        if not self.use_transformer:
            return self._rule_based_generate(query, context)
        
        try:
            input_text = f"问题: {query} 上下文: {context}" if context else query
            
            inputs = self.tokenizer(
                input_text,
                truncation=True,
                max_length=512,
                padding='max_length',
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=4,
                    early_stopping=True,
                    no_repeat_ngram_size=2
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response
            
        except Exception as e:
            print("[ERROR] Transformer generation failed: {}".format(str(e)[:100]))
            return self._rule_based_generate(query, context)

    def _rule_based_generate(self, query: str, context: str = "") -> str:
        if context:
            return "根据知识库内容，关于\"{}\"的信息如下：\n{}".format(query, context[:300])
        else:
            return "已收到您的问题：\"{}\"，我将为您查询相关信息。".format(query)

    # ------------------------------------------------------------------
    #  思考式回答生成
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """去除 Markdown 格式符号，保留纯文本"""
        import re
        text = re.sub(r'#{1,6}\s+', '', text)          # 标题
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **加粗**
        text = re.sub(r'\*(.+?)\*', r'\1', text)        # *斜体*
        text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)  # 列表
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _extract_key_points(content: str) -> list:
        """从一段内容中提取关键要点"""
        import re
        points = []
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 跳过纯标题行（只有标题没有内容的行，如 "1. 儿童与青少年"）
            if re.match(r'^#{1,6}\s+', line):
                continue
            # 跳过纯数字编号的子标题行（如 "1. 儿童与青少年"）
            if re.match(r'^#{0,1}\s*\d+\.\s+[\u4e00-\u9fa5]+$', line):
                continue
            # 跳过纯标题行（如 "二、不同人群吃猪肉的好处"）
            if re.match(r'^[一二三四五六七八九十]+、.+', line) and len(line) < 30:
                continue
            # 提取 - 或 • 开头的要点
            m = re.match(r'^[-•*]\s+(.+)', line)
            if m:
                text = m.group(1).strip()
                # 去掉 **加粗** 标记
                text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
                if len(text) > 3:
                    points.append(text)
            elif not line.startswith('#') and len(line) > 8:
                # 非标题、非短行 → 作为补充信息
                text = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
                points.append(text)
        return points

    @staticmethod
    def _classify_query(query: str) -> str:
        """简单判断查询类型，用于选择回答模板"""
        import re
        if re.search(r'怎么|做法|如何做|菜谱|食谱|烹饪', query):
            return 'how_to'
        if re.search(r'好处|坏处|好处和坏处|利弊|优缺点|适合|可以|不适合|不能吃|不宜吃|忘记吃|少吃|禁忌|哪些人|哪些员工|什么人适合|什么人不适合', query):
            return 'pros_cons'
        if re.search(r'营养|成分|含有|维生素|矿物质', query):
            return 'nutrition'
        if re.search(r'什么|哪些|介绍|是什么', query):
            return 'what'
        return 'general'

    def _think_and_answer(self, query: str, documents: List[Dict],
                           data_analysis: dict = None) -> dict:
        """
        思考式回答：分析检索结果 → 归纳要点 → 组织自然语言回答
        返回 {'thinking': str, 'answer': str}
        """
        import random
        import re

        # ---- 1. 分析每个文档，提取结构化信息 ----
        doc_summaries = []     # 每个文档的摘要
        all_key_points = []   # 所有关键要点
        doc_titles = set()

        for doc in documents:
            content = doc.get('content', '') or doc.get('preview', '')
            section = doc.get('chunk_section', '')
            doc_title = doc.get('doc_title', doc.get('title', '未知'))
            doc_titles.add(doc_title)
            kw = doc.get('keyword_matching', {})
            matched_kw = kw.get('matched_keywords', [])
            match_ratio = kw.get('match_ratio', 0)

            # 清理内容
            clean_content = self._strip_markdown(content)

            # 提取要点
            points = self._extract_key_points(clean_content)

            doc_summaries.append({
                'doc_title': doc_title,
                'section': section,
                'matched_keywords': matched_kw,
                'match_ratio': match_ratio,
                'similarity': doc.get('similarity', 0),
                'points': points,
                'raw_content': clean_content,
            })

            all_key_points.extend(points)

        # ---- 2. 构建思考过程 ----
        thinking_lines = []
        thinking_lines.append(f"用户问的是：{query}")
        thinking_lines.append("")
        if documents:
            thinking_lines.append(f"我从知识库中检索到 {len(documents)} 个相关段落，来自 {len(doc_titles)} 篇文档：")
            for i, ds in enumerate(doc_summaries, 1):
                thinking_lines.append(
                    f"  [{i}] \u300a{ds['doc_title']}\u300b的\u300c{ds['section']}\u300d段落 "
                    f"(匹配词: {', '.join(ds['matched_keywords']) or '无'}, "
                    f"匹配度: {ds['match_ratio']:.0%})"
                )
        else:
            thinking_lines.append("知识库中没有相关文档，将直接分析数据表。")
        thinking_lines.append("")
        
        # 分析查询类型
        q_type = self._classify_query(query)
        type_desc = {
            'how_to': '做法/烹饪类问题',
            'pros_cons': '利弊/适合性类问题',
            'nutrition': '营养/成分类问题',
            'what': '介绍/科普类问题',
            'general': '综合性问题',
        }
        thinking_lines.append(f"问题类型判断：{type_desc.get(q_type, '综合性问题')}")
        thinking_lines.append("")
        thinking_lines.append("让我从检索结果中提取关键信息，整理成回答：")
        
        thinking = '\n'.join(thinking_lines)
        
        # ---- 3. 根据查询类型组织回答 ----
        answer_parts = []
        
        # 开头：纯数据查询时不要说“根据知识库”
        if documents:
            intro = random.choice([
                f'关于「{query}」，我根据知识库整理了以下信息：',
                f'让我来回答您关于「{query}」的问题：',
                f'根据知识库中的资料，关于「{query}」：',
            ])
        else:
            intro = f'关于「{query}」，以下是数据分析结果：'
        answer_parts.append(intro)
        answer_parts.append("")

        if q_type == 'pros_cons':
            # 利弊类：分好处/坏处组织
            benefit_points = []
            risk_points = []
            other_points = []

            for ds in doc_summaries:
                section_lower = ds['section'].lower()
                for pt in ds['points']:
                    if any(w in pt for w in ['核心获益', '好处', '益处', '推荐']):
                        benefit_points.append(pt)
                    elif any(w in pt for w in ['风险', '坏处', '禁忌', '避免', '禁止', '控制']):
                        risk_points.append(pt)
                    else:
                        other_points.append(pt)

            if benefit_points:
                answer_parts.append("【好处/获益】")
                for pt in benefit_points:
                    answer_parts.append(f"  • {pt}")
                answer_parts.append("")
            if risk_points:
                answer_parts.append("【风险/禁忌】")
                for pt in risk_points:
                    answer_parts.append(f"  • {pt}")
                answer_parts.append("")
            if other_points and not (benefit_points or risk_points):
                # 只有无分类信息时才显示补充信息，避免冗余
                answer_parts.append("【补充信息】")
                for pt in other_points:
                    answer_parts.append(f"  • {pt}")
                answer_parts.append("")

        elif q_type == 'how_to':
            # 做法类：展示做法要点
            found_recipe = False
            for ds in doc_summaries:
                raw = ds['raw_content']
                # 找做法步骤
                steps = re.findall(r'\d+\.\s+(.+)', raw)
                ingredients = re.findall(r'(?:食材|材料|原料)[：:]\s*(.+)', raw)
                if ingredients or steps:
                    found_recipe = True
                    answer_parts.append(f"来自《{ds['doc_title']}》的「{ds['section']}」：")
                    if ingredients:
                        answer_parts.append(f"  所需食材：{ingredients[0]}")
                    if steps:
                        answer_parts.append("  做法步骤：")
                        for j, step in enumerate(steps, 1):
                            answer_parts.append(f"    {j}. {step}")
                    answer_parts.append("")
            if not found_recipe:
                for ds in doc_summaries:
                    for pt in ds['points']:
                        answer_parts.append(f"  • {pt}")
                    answer_parts.append("")

        elif q_type == 'nutrition':
            # 营养类：展示营养成分要点
            for ds in doc_summaries:
                if ds['points']:
                    answer_parts.append(f"关于「{ds['section']}」：")
                    for pt in ds['points']:
                        answer_parts.append(f"  • {pt}")
                    answer_parts.append("")

        else:
            # 通用：按文档/段落组织要点
            for ds in doc_summaries:
                if ds['points']:
                    answer_parts.append(f"关于「{ds['section']}」：")
                    for pt in ds['points']:
                        answer_parts.append(f"  • {pt}")
                    answer_parts.append("")

        # ---- 3.5 如果有数据分析，根据查询方向动态生成数据段 ----
        if data_analysis and data_analysis.get('filtered'):
            direction = data_analysis.get('direction', 'general')
            total = data_analysis.get('total', 0)
            filtered = data_analysis['filtered']
            profiles = data_analysis.get('profiles', [])
            insights = data_analysis.get('knowledge_insights', [])

            answer_parts.append("=" * 40)
            answer_parts.append("")

            # 根据查询方向动态组织数据段（通用模板，不限定业务场景）
            if direction == 'negative':
                # 负面/排除：列出有异常的记录
                answer_parts.append(
                    f"根据数据表 {total} 条记录，"
                    f"以下 {len(filtered)} 条需注意："
                )
                answer_parts.append("")
                for rec in filtered:
                    cond_str = '；'.join(c['label'] for c in rec['conditions']
                                         if c['direction'] == 'negative')
                    answer_parts.append(
                        f"  • {rec['name']}（{rec['data_summary']}）— {cond_str}"
                    )
                answer_parts.append("")

                # 从知识库洞察中提取对应建议
                negative_insights = [i for i in insights if i['direction'] == 'negative']
                if negative_insights:
                    answer_parts.append("知识库建议：")
                    for ins in negative_insights:
                        clean = self._strip_markdown(ins['text'])
                        answer_parts.append(f"  • {clean}")
                    answer_parts.append("")

            elif direction == 'positive':
                # 正面/推荐：列出正常的记录
                answer_parts.append(
                    f"根据数据表 {total} 条记录，"
                    f"以下 {len(filtered)} 条符合条件："
                )
                answer_parts.append("")
                for rec in filtered:
                    answer_parts.append(
                        f"  • {rec['name']}（{rec['data_summary']}）— 各项指标正常"
                    )
                answer_parts.append("")

                # 知识库中关于正面方向的建议
                positive_insights = [i for i in insights if i['direction'] == 'positive']
                if positive_insights:
                    answer_parts.append("相关建议：")
                    for ins in positive_insights:
                        clean = self._strip_markdown(ins['text'])
                        answer_parts.append(f"  • {clean}")
                    answer_parts.append("")

            elif direction == 'filter':
                # 筛选/列表：列出所有记录，按状态分组
                negative_recs = [p for p in profiles if p['has_risk']]
                normal_recs = [p for p in profiles if p['is_normal']]
                other_recs = [p for p in profiles if not p['has_risk'] and not p['is_normal']]

                if negative_recs:
                    answer_parts.append(f"需关注的记录（{len(negative_recs)} 条）：")
                    for rec in negative_recs:
                        cond_str = '；'.join(c['label'] for c in rec['conditions']
                                             if c['direction'] == 'negative')
                        answer_parts.append(
                            f"  • {rec['name']}（{rec['data_summary']}）— {cond_str}"
                        )
                    answer_parts.append("")

                if other_recs:
                    answer_parts.append(f"需留意的记录（{len(other_recs)} 条）：")
                    for rec in other_recs:
                        cond_str = '；'.join(c['label'] for c in rec['conditions']
                                             if c['direction'] == 'neutral')
                        answer_parts.append(
                            f"  • {rec['name']}（{rec['data_summary']}）— {cond_str}"
                        )
                    answer_parts.append("")

                if normal_recs:
                    answer_parts.append(f"正常的记录（{len(normal_recs)} 条）：")
                    for rec in normal_recs:
                        answer_parts.append(
                            f"  • {rec['name']}（{rec['data_summary']}）— 各项指标正常"
                        )
                    answer_parts.append("")

            else:
                # 综合：按状态分组列出
                negative_recs = [p for p in profiles if p['has_risk']]
                normal_recs = [p for p in profiles if p['is_normal']]
                other_recs = [p for p in profiles if not p['has_risk'] and not p['is_normal']]

                if negative_recs:
                    answer_parts.append(f"需关注的记录（{len(negative_recs)} 条）：")
                    for rec in negative_recs:
                        cond_str = '；'.join(c['label'] for c in rec['conditions']
                                             if c['direction'] == 'negative')
                        answer_parts.append(
                            f"  • {rec['name']}（{rec['data_summary']}）— {cond_str}"
                        )
                    answer_parts.append("")

                if other_recs:
                    answer_parts.append(f"需留意的记录（{len(other_recs)} 条）：")
                    for rec in other_recs:
                        cond_str = '；'.join(c['label'] for c in rec['conditions']
                                             if c['direction'] == 'neutral')
                        answer_parts.append(
                            f"  • {rec['name']}（{rec['data_summary']}）— {cond_str}"
                        )
                    answer_parts.append("")

                if normal_recs:
                    answer_parts.append(f"正常的记录（{len(normal_recs)} 条）：")
                    for rec in normal_recs:
                        answer_parts.append(
                            f"  • {rec['name']}（{rec['data_summary']}）— 各项指标正常"
                        )
                    answer_parts.append("")

        # 结尾
        conclusion = random.choice([
            "希望以上信息对您有帮助！如有其他问题欢迎继续提问。",
            "如果您还有其他疑问，欢迎随时问我。",
            "以上是根据知识库整理的信息，如需了解更多细节请告诉我。",
        ])
        answer_parts.append(conclusion)

        answer = '\n'.join(answer_parts)
        return {'thinking': thinking, 'answer': answer}

    def answer_with_context(self, query: str, documents: List[Dict],
                            min_match_ratio: float = 0.1,
                            data_analysis: dict = None) -> dict:
        """
        思考式回答入口，返回 {'thinking': str, 'answer': str}
        data_analysis: 员工数据分析结果（可选）
        """
        if not documents:
            # 如果有数据分析结果，就算没有知识库内容也可以生成回答
            if data_analysis:
                return self._think_and_answer(query, [], data_analysis=data_analysis)
            return {
                'thinking': '知识库中没有找到相关文档。',
                'answer': '未找到相关信息来回答您的问题。'
            }
            
        valid_docs = []
        for doc in documents:
            keyword_matching = doc.get('keyword_matching', {})
            match_ratio = keyword_matching.get('match_ratio', 0.0)
            if match_ratio >= min_match_ratio:
                valid_docs.append(doc)
            
        if not valid_docs:
            # 有数据分析时不返回失败，直接以纯数据回答
            if data_analysis:
                return self._think_and_answer(query, [], data_analysis=data_analysis)
            return {
                'thinking': f'检索到 {len(documents)} 个结果，但关键词匹配度均低于阈值，无法提取有效信息。',
                'answer': f'抒歉，我无法从知识库中找到与“{query}”相关的信息。'
            }
            
        return self._think_and_answer(query, valid_docs, data_analysis=data_analysis)
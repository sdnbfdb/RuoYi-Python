import numpy as np
import re
import math
from collections import defaultdict
from typing import List, Union, Tuple, Optional


def tokenize(text: str, ngram_range: tuple = (1, 2)) -> List[str]:
    text = re.sub(r'[，。！？；：、（）【】《》‘’“”·…—～·\s]+', ' ', text)
    text = text.strip()

    tokens = []
    pattern = r'[\u4e00-\u9fa5]+|[a-zA-Z]+'
    words = re.findall(pattern, text)

    for word in words:
        if len(word) >= 1:
            tokens.append(word)

        if len(word) > 1:
            min_n, max_n = ngram_range
            for n in range(max(min_n, 2), min(max_n + 1, len(word) + 1)):
                for i in range(len(word) - n + 1):
                    tokens.append(word[i:i+n])

    return tokens


def encode_texts_with_position(texts: Union[str, List[str]],
                               max_features: int = 5000,
                               ngram_range: tuple = (1, 2),
                               position_weight: float = 0.1,
                               vocab: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
    if isinstance(texts, str):
        texts = [texts]

    n_texts = len(texts)

    all_tokens = []
    all_positions = []

    for text in texts:
        tokens = tokenize(text, ngram_range)
        all_tokens.append(tokens)

        positions = []
        for idx, token in enumerate(tokens):
            pos_weight = 1.0 - (idx / len(tokens)) * position_weight if len(tokens) > 0 else 1.0
            positions.append(pos_weight)

        all_positions.append(positions)

    if vocab is None:
        doc_freq = defaultdict(int)
        for tokens in all_tokens:
            for token in set(tokens):
                doc_freq[token] += 1

        sorted_tokens = sorted(doc_freq.items(), key=lambda x: -x[1])[:max_features]
        vocab = {token: idx for idx, (token, _) in enumerate(sorted_tokens)}

    n_features = len(vocab)

    if vocab:
        n_docs = max(len(texts), 1)
        idf = np.zeros(n_features)
        for token, idx in vocab.items():
            df = sum(1 for tokens in all_tokens if token in tokens)
            idf[idx] = math.log((n_docs + 1) / (df + 1)) + 1
    else:
        idf = np.zeros(n_features)

    embeddings = np.zeros((n_texts, n_features))

    for i, (tokens, positions) in enumerate(zip(all_tokens, all_positions)):
        if not tokens:
            continue

        tf = defaultdict(int)
        token_positions = defaultdict(list)

        for idx, token in enumerate(tokens):
            tf[token] += 1
            token_positions[token].append(positions[idx])

        matched_tokens = 0
        for token, count in tf.items():
            if token in vocab:
                idx = vocab[token]
                tf_val = count / len(tokens)

                avg_pos_weight = np.mean(token_positions[token])
                pos_factor = 1.0 + avg_pos_weight * position_weight

                embeddings[i, idx] = tf_val * idf[idx] * pos_factor
                matched_tokens += 1

        if matched_tokens == 0 and vocab:
            embeddings[i, 0] = 0.0001

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    return embeddings, vocab


def save_embeddings(embeddings: np.ndarray, filename: str = 'embeddings.npy'):
    import os
    filepath = os.path.join(os.path.dirname(__file__), filename)
    np.save(filepath, embeddings)
    print(f"✅ 向量已保存到: {filepath}")


def load_embeddings(filename: str = 'embeddings.npy') -> np.ndarray:
    import os
    filepath = os.path.join(os.path.dirname(__file__), filename)
    return np.load(filepath)


if __name__ == '__main__':
    documents = [
        "红烧肉的做法：五花肉切块，焯水后炒糖色，加调料炖煮",
        "鱼香肉丝：里脊肉切丝，用郫县豆瓣酱炒制",
        "宫保鸡丁：鸡肉切丁，搭配花生和干辣椒",
        "麻婆豆腐：嫩豆腐切块，用牛肉末和豆瓣酱烧制",
        "北京烤鸭：鸭子腌制后挂炉烤制，皮脆肉嫩"
    ]

    print("=== 文本向量编码（带位置信息）===")
    print(f"输入文档数量: {len(documents)}")

    print("\n1. 分词示例:")
    tokens = tokenize(documents[0])
    print(f"文档1分词结果: {tokens[:10]}... (共{len(tokens)}个词)")

    print("\n2. 向量化（带位置信息）...")
    embeddings, vocab = encode_texts_with_position(
        documents,
        max_features=100,
        ngram_range=(1, 2),
        position_weight=0.3
    )
    print(f"向量形状: {embeddings.shape}")
    print(f"向量维度: {embeddings.shape[1]}")
    print(f"词汇表大小: {len(vocab)}")

    save_embeddings(embeddings, 'position_embeddings.npy')

    loaded = load_embeddings('position_embeddings.npy')
    print(f"\n加载的向量形状: {loaded.shape}")

    print("\n3. 使用已有词汇表编码新文本...")
    query_text = "怎么做红烧肉？"
    query_embedding, _ = encode_texts_with_position(query_text, vocab=vocab)
    print(f"查询文本: {query_text}")
    print(f"查询向量形状: {query_embedding.shape}")

    print("\n💡 提示：向量文件已保存在 nlp 目录下，不会自动清理")
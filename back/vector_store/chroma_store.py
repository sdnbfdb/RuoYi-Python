import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from typing import List, Dict, Optional, Any
import os
import requests
import numpy as np

class DashScopeEmbeddings(Embeddings):
    def __init__(self, api_key: str = None, model: str = "text-embedding-v1"):
        self.api_key = api_key or os.getenv('API_KEY')
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/embedding/text-embedding"
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        embeddings = []
        for text in texts:
            try:
                payload = {
                    "model": self.model,
                    "input": text
                }
                response = requests.post(self.base_url, headers=headers, json=payload, verify=False)
                result = response.json()
                
                if result.get("status") == "OK":
                    embedding = result.get("output", {}).get("embedding", [])
                    embeddings.append(embedding)
                else:
                    embeddings.append([0.0] * 768)
            except Exception as e:
                print(f"嵌入失败: {e}")
                embeddings.append([0.0] * 768)
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

class CharmDBStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self.embeddings = DashScopeEmbeddings()
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.collections = {}
    
    def get_or_create_collection(self, collection_name: str):
        if collection_name not in self.collections:
            self.collections[collection_name] = Chroma(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embeddings
            )
        return self.collections[collection_name]
    
    def add_documents(self, collection_name: str, documents: List[str], 
                      metadatas: List[Dict], ids: List[str]):
        collection = self.get_or_create_collection(collection_name)
        collection.add_texts(
            texts=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def similarity_search(self, collection_name: str, query: str, 
                          k: int = 5, filter: Dict = None):
        collection = self.get_or_create_collection(collection_name)
        return collection.similarity_search(
            query=query,
            k=k,
            filter=filter
        )
    
    def similarity_search_with_score(self, collection_name: str, query: str, 
                                     k: int = 5, filter: Dict = None):
        collection = self.get_or_create_collection(collection_name)
        return collection.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter
        )
    
    def delete_collection(self, collection_name: str):
        if collection_name in self.collections:
            del self.collections[collection_name]
        self.client.delete_collection(name=collection_name)
    
    def reset(self):
        self.client.reset()
        self.collections = {}
    
    def get_collection_stats(self, collection_name: str) -> Dict:
        collection = self.get_or_create_collection(collection_name)
        underlying_collection = self.client.get_collection(name=collection_name)
        return {
            'count': underlying_collection.count(),
            'name': collection_name
        }
    
    def get_all_collections(self) -> List[str]:
        return [col.name for col in self.client.list_collections()]

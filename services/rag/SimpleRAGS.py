import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings  
from langchain_community.vectorstores import Chroma  
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

from ..base import BaseService

class SimpleRAGService(BaseService):
    """
    简单的RAG服务，使用Chroma向量数据库
    """
    def __init__(self, service_name: str = "rag", config: Dict[str, Any] = None):
        config_default = {
            "knowledge_base_path": "data/knowledge_base.txt",
            "chroma_db_path": "data/chroma_db",
            "collection_name": "knowledge_base",
            "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "chunk_size": 500,
            "chunk_overlap": 50,
            "top_k": 3
        }
        if config is None:
            config = {}
        config = {**config_default, **config}
        super().__init__(service_name, config)
        
        self.embeddings = None
        self.vectorstore = None
        self.text_splitter = None

    async def initialize(self):
        """初始化RAG服务"""
        self.logger.info("Initializing Simple RAG service...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_components)
        self.set_ready()

    def _get_default_knowledge(self) -> str:
        """获取默认知识内容"""
        return "欢迎使用AI虚拟主播！擅长角色扮演、闲聊。"

    def _init_components(self):
        """初始化组件"""
        # 初始化嵌入模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config["embedding_model"]
        )
        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"],
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
        )
        # 初始化Chroma向量数据库
        persist_directory = str(Path(self.config["chroma_db_path"]))
        # 检查是否已有数据库
        chroma_path = Path(persist_directory)
        if chroma_path.exists() and any(chroma_path.iterdir()):
            # 加载现有数据库
            self.vectorstore = Chroma(
                collection_name=self.config["collection_name"],
                embedding_function=self.embeddings,
                persist_directory=persist_directory
            )
            self.logger.info("Loaded existing Chroma database")
        else:
            # 创建新数据库
            self._create_vectorstore(persist_directory)

    def _create_vectorstore(self, persist_directory: str):
        """创建向量数据库"""
        knowledge_path = Path(self.config["knowledge_base_path"])
        if knowledge_path.exists():
            with open(knowledge_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = self._get_default_knowledge()
            knowledge_path.parent.mkdir(parents=True, exist_ok=True)
            with open(knowledge_path, 'w', encoding='utf-8') as f:
                f.write(content)
        # 分割文本
        chunks = self.text_splitter.split_text(content)
        documents = [Document(page_content=chunk, metadata={"source": "knowledge_base"}) for chunk in chunks]
        # 创建向量数据库
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            collection_name=self.config["collection_name"],
            persist_directory=persist_directory
        )
        
        # 持久化
        self.vectorstore.persist()
        self.logger.info(f"Created Chroma database with {len(documents)} documents")

    async def process(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """检索相关知识"""
        if not self.is_ready():
            return []
        
        loop = asyncio.get_running_loop()
        
        def _search():
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query, 
                k=self.config["top_k"]
            )
            return docs_with_scores
        
        docs_with_scores = await loop.run_in_executor(None, _search)
        
        results = []
        for i, (doc, score) in enumerate(docs_with_scores):
            results.append({
                "id": i,
                "content": doc.page_content,
                "similarity_score": float(score),
                "metadata": doc.metadata
            })
        return results

    async def add_knowledge(self, content: str):
        """添加新知识"""
        if not self.is_ready():
            return
        
        loop = asyncio.get_running_loop()
        
        def _add():
            chunks = self.text_splitter.split_text(content)
            documents = [Document(page_content=chunk, metadata={"source": "user_added"}) for chunk in chunks]
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()
        
        await loop.run_in_executor(None, _add)
        self.logger.info("Added new knowledge to vector store")
import os
from dotenv import load_dotenv
from llama_index.callbacks import LlamaDebugHandler, CallbackManager
import boto3
import pinecone
import openai
from llama_index.storage.docstore import MongoDocumentStore
from llama_index.node_parser import SimpleNodeParser
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.storage.index_store import MongoIndexStore
from llama_index.llm_predictor.chatgpt import LLMPredictor
from langchain.chat_models import ChatOpenAI
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
)
from llama_index import download_loader

load_dotenv()

MONGO_DB_URL = os.environ["MONGO_DB_URL"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_REGION = os.environ["PINECONE_REGION"]

openai.api_key = os.environ["OPENAI_API_KEY"]

class DocumentManager:
    def __init__(self):
        pinecone.init(
            api_key=PINECONE_API_KEY,
            environment=PINECONE_REGION,
        )

        self.docstore = MongoDocumentStore.from_uri(uri=MONGO_DB_URL)
        self.index_store = MongoIndexStore.from_uri(uri=MONGO_DB_URL)
        self.llama_debug = LlamaDebugHandler(print_trace_on_end=True)
        self.callback_manager = CallbackManager([self.llama_debug])
        self.PptxReader = download_loader("PptxReader")
        self.loader = self.PptxReader()
        self.index = None

    def initialize_index(self, namespace: str):
        llm_predictor = LLMPredictor(
            llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)
        )
        service_context = ServiceContext.from_defaults(
            chunk_size_limit=512,
            llm_predictor=llm_predictor,
            callback_manager=self.callback_manager,
        )

        pinecone_index = pinecone.Index("pptx-index")
        vector_store = PineconeVectorStore(
            pinecone_index=pinecone_index,
            namespace=namespace
        )
        storage_context = StorageContext.from_defaults(
            docstore=self.docstore,
            index_store=self.index_store,
            vector_store=vector_store,
        )
        self.index = VectorStoreIndex.from_documents(
            [], storage_context=storage_context, service_context=service_context
        )

    def query_stream(self, query: str, namespace: str):
        streaming_response = self.index.as_query_engine(
            streaming=True, similarity_top_k=1
        ).query(query)
        for text in streaming_response.response_gen:
            # do something with text as they arrive.
            print(text)
            yield text

    def query_index(self, query_text: str, namespace: str) -> str:
        self.initialize_index(namespace)
        response = self.index.as_query_engine().query(query_text)
        return response

    def insert_into_index(self, doc_file_path, doc_id=None):
        self.initialize_index(doc_id)
        document = self.loader.load_data(file=doc_file_path)[0]
        parser = SimpleNodeParser()
        nodes = parser.get_nodes_from_documents([document])
        self.docstore.add_documents(nodes)

        if doc_id is not None:
            document.doc_id = doc_id
        self.index.insert(document)

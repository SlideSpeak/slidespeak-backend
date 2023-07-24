from queue import Queue
import os
from threading import Thread
from dotenv import load_dotenv
from llama_index.callbacks import LlamaDebugHandler, CallbackManager

load_dotenv()

import boto3
import pinecone
from multiprocessing.managers import BaseManager

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

boto3.set_stream_logger("botocore", level="DEBUG")

AWS_KEY = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET = os.environ["AWS_SECRET_ACCESS_KEY"]
MONGO_DB_URL = os.environ["MONGO_DB_URL"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_REGION = os.environ["PINECONE_REGION"]

pinecone.init(
    api_key=PINECONE_API_KEY,
    environment=PINECONE_REGION,
)

import openai

openai.api_key = os.environ["OPENAI_API_KEY"]

index = None
stored_docs = {}
docstore = MongoDocumentStore.from_uri(uri=MONGO_DB_URL)
index_store = MongoIndexStore.from_uri(uri=MONGO_DB_URL)
llama_debug = LlamaDebugHandler(print_trace_on_end=True)
callback_manager = CallbackManager([llama_debug])

PptxReader = download_loader("PptxReader")
loader = PptxReader()


def initialize_index(namespace):
    print("start to initialize index")
    """Create a new global index, or load one from the pre-set path."""
    global index, stored_docs, docstore, index_store

    llm_predictor = LLMPredictor(
        llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", streaming=True)
    )
    service_context = ServiceContext.from_defaults(
        chunk_size_limit=512, llm_predictor=llm_predictor,callback_manager=callback_manager
    )
    print(namespace)
    # TODO: Move this to an env variable
    pinecone_index = pinecone.Index("pptx-index")
    vector_store = PineconeVectorStore(
        pinecone_index=pinecone_index,
        namespace=namespace,
    )
    storage_context = StorageContext.from_defaults(
        docstore=docstore, index_store=index_store, vector_store=vector_store
    )
    index = VectorStoreIndex.from_documents(
        [], storage_context=storage_context, service_context=service_context
    )
    print("index initialized")


def worker(queue, query_text, name):
    """Query the global index."""
    initialize_index(name)
    global index
    streaming_response = index.as_query_engine(
        streaming=True, similarity_top_k=1
    ).query(query_text)
    for text in streaming_response.response_gen:
        # do something with text as they arrive.
        print(text)
        queue.put(text)  # Put the text into the queue
    queue.put(None)  # Signal the end of the stream


def start_worker(query_text, name):
    print("start_worker")
    print(name)
    queue = Queue()
    t = Thread(target=worker, args=(queue, query_text, name))
    t.start()
    return queue


def query_index(query_text, name):
    """Query the global index."""
    print("querying index...")
    global index
    response = index.as_query_engine().query(query_text)
    return response


def insert_into_index(doc_file_path, doc_id=None):
    """Insert new document into global index."""
    global index, stored_docs, docstore
    initialize_index(doc_id)
    document = loader.load_data(file=doc_file_path)[0]

    # create parser and parse document into nodes
    parser = SimpleNodeParser()
    nodes = parser.get_nodes_from_documents([document])
    docstore.add_documents(nodes)

    if doc_id is not None:
        document.doc_id = doc_id

    index.insert(document)
    # TODO: Check if this limits the entire document that is parsed to 200 chars
    stored_docs[document.doc_id] = document.text[0:200]  # only take the first 200 chars
    return


def get_documents_list():
    """Get the list of currently stored documents."""
    global stored_docs
    documents_list = []
    for doc_id, doc_text in stored_docs.items():
        documents_list.append({"id": doc_id, "text": doc_text})
    return documents_list


if __name__ == "__main__":
    # init the global index
    print("initializing index...")
    # initialize_index()

    # setup server
    # NOTE: you might want to handle the password in a less hardcoded way
    manager = BaseManager(("", 5602), b"password")
    manager.register("query_index", query_index)
    manager.register("insert_into_index", insert_into_index)
    manager.register("get_documents_list", get_documents_list)
    manager.register("get_queue")
    manager.register("initialize_index")
    manager.register("start_worker", start_worker)

    server = manager.get_server()

    print("server started...")
    server.serve_forever()

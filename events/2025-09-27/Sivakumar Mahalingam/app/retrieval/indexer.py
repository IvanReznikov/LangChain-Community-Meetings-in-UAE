import json
import os
from datetime import date
from typing import Any, Dict, List, Tuple

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import require_openai_key

embeddings = OpenAIEmbeddings(openai_api_key=require_openai_key())

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "policies")
MANIFEST_PATH = os.path.join(DATA_DIR, "docs_manifest.json")

def load_manifest() -> List[Dict[str, Any]]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_vectorstore():
    manifest = load_manifest()
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for entry in manifest:
        file_path = os.path.join(DATA_DIR, entry["file"])
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        for chunk in splitter.split_text(content):
            texts.append(chunk)
            md = {k: v for k, v in entry.items() if k != "file"}
            metadatas.append(md)

    embeddings = OpenAIEmbeddings()
    vs = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
    return vs

# Build at import for simplicity
VECTORSTORE = build_vectorstore()

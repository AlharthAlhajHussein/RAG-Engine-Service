from typing import List
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text(file_extension: str, temp_filename: str):
    # --- 2. EXTRACT TEXT ---
    if file_extension == "pdf":
        loader = PyMuPDFLoader(temp_filename)
    elif file_extension == "txt":
        loader = TextLoader(temp_filename, encoding='utf-8')
    elif file_extension == "docx":
        loader = Docx2txtLoader(temp_filename)
    else:
        raise ValueError(f"Unsupported extension: {file_extension}")
        
    file_content = loader.load()
    
    return file_content

def chunking_text(file_content: List[dict]):
    # --- 3. CHUNK TEXT ---
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", "?", "؟", "!", " "],
        chunk_size=500,
        chunk_overlap=50,
        length_function=len
    )
    
    # Extract plain text strings from Langchain documents
    raw_texts = [doc.page_content for doc in file_content]
    chunks = text_splitter.create_documents(raw_texts)
    
    return chunks
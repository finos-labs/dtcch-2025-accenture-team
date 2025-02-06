"""
This script provides a class `Embeddings` to process PDF documents, generate embeddings using
AWS Bedrock services, and create a vector store using FAISS for efficient document retrieval.

Key Features:
- PDF document ingestion and loading using `PyPDFDirectoryLoader`.
- Text splitting into manageable chunks using `RecursiveCharacterTextSplitter`.
- Embedding generation leveraging AWS Bedrock with the `cohere.embed-english-v3` model.
- FAISS vector store creation for fast similarity search and retrieval.
- Error handling with `try-except` blocks for robust execution.
- Logging for tracing and debugging the process flow.

Classes:
- `Embeddings`: Handles the entire workflow, from document processing to vector store creation.

Usage:
1. Initialize the `Embeddings` class with the file path of the PDF and the target folder for the vector store.
2. Call the `main()` method to process the document and save the vector store.

"""

import boto3
import os
import logging
from PyPDF2 import PdfReader
from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
from langchain.llms.bedrock import Bedrock

class Embeddings:
    """
    A class to handle document ingestion, processing, and vector store creation using Bedrock embeddings.
    """
    def __init__(self, folder_path, vectordb_folder_path):
        """
        Initializes the Embeddings class with required parameters.

        Args:
            folder_path (str): Path to the PDF files folder.
            vectordb_folder_path (str): Path to store the vector database.
        """
        self.region = "us-west-2"
        self.embedding_model_id = "cohere.embed-english-v3"
        self.folder_path = folder_path
        self.index_folder_path = vectordb_folder_path
        self.bedrock_embeddings = BedrockEmbeddings(region_name=self.region, model_id=self.embedding_model_id)
    def data_ingestion(self):
        """
        Ingests the PDF documents, splits it into chunks, and returns the processed documents.

        Returns:
            List[Document]: List of processed document chunks.
        """
        try:
            loader = PyPDFDirectoryLoader(self.folder_path)
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=100)
            docs = text_splitter.split_documents(documents)
            return docs
        except:
            logging.error('Error during data ingestion')
            raise
    def get_vector_store(self, docs):
        """
        Creates a vector store using the Bedrock embeddings and saves it locally.

        Args:
            docs (List[Document]): List of processed document chunks.
        """
        try:
            logging.info("Creating FAISS vector store.")
            vectorstore_faiss=FAISS.from_documents(
                docs,
                self.bedrock_embeddings
            )
            vectorstore_faiss.save_local(self.index_folder_path)
            logging.info(f"Vector store saved locally at {self.index_folder_path}.")
        except:
            logging.error("Error during vector store creation")
            raise

    def run_vectorstore(self):
        """
        Main function to execute data ingestion and vector store creation.
        """
        try:
            logging.info("Starting the main process.")
            docs = self.data_ingestion()
            self.get_vector_store(docs)
            logging.info("Process completed successfully.")
        except:
            logging.error("Error in main process")
            raise



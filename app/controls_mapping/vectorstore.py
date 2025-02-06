import pandas as pd
import boto3

from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain_community.embeddings import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .utils import load_config

def create_vector_store(user_session):
    """
    Creates a FAISS-based vector database from policy statement data stored in an Excel file.
    
    Steps:
    1. Load configuration settings.
    2. Read the input Excel file and preprocess the data.
    3. Initialize the embedding model using AWS Bedrock.
    4. Split text into manageable chunks to optimize embedding quality.
    5. Convert processed text into a FAISS vector store.
    6. Save the vector store locally for future retrieval.
    
    Returns:
        None
    """

    folder_path = f"./{user_session}/controls_mapping"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    ### Commented out code used for demo purposes
    # # Load configuration settings
    # config = load_config()
        
    # # Extract paths and model parameters from config
    # input_data_path = config["paths"]["input_data_path"]
    # input_sheet_name = config["paths"]["input_sheet_name"]
    # vector_db_path = config["paths"]["vector_db_path"]

    vector_db_path = f"./{user_session}/controls_mapping/faiss_vectorstore"
    region = config["bedrock"]["region"] # replace with your desired region
    embedding_model_id = config["bedrock"]["embedding_model_id"] # replace with your desired bedrock model id

    ### Commented code used for demo purposes
    # # Read the Excel file into a Pandas DataFrame
    # df = pd.read_excel(input_data_path, sheet_name=input_sheet_name, index_col=None)
    
    # # Remove any unnecessary columns (e.g., unnamed index columns)
    # df = df.drop(columns=['Unnamed: 0'], errors='ignore')


    df = pd.read_excel(f"./{user_session}/controls_mapping/input/extracted_structure_<Name of the latest file>.xlsx")  ### This is assuming dora regulation
    # Initialize Bedrock embeddings model
    embeddings = BedrockEmbeddings(region_name=region, model_id=embedding_model_id)
    
    # Define the text splitter to segment large policy texts into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2048,  # Maximum length allowed by Bedrock for embeddings
        chunk_overlap=200  # Overlapping ensures context retention across chunks
    )
    
    # Prepare the documents for vectorization
    documents = []
    for _, row in df.iterrows():
        # Combine relevant fields into a single text input
        text = f"Theme: {row['Theme']} \n Policy statement wording: {row['Policy statement wording']}"
        
        # Convert remaining metadata into a dictionary
        metadata = row.to_dict()
        
        # Split long text into smaller chunks
        chunks = text_splitter.split_text(text)
        
        # Create Document objects for each chunk and store them
        for chunk in chunks:
            documents.append(Document(page_content=chunk, metadata=metadata))
    
    # Create a FAISS vector store from the processed documents
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Save the FAISS vector store locally
    vector_store.save_local(vector_db_path)
    
    print("Vector store created and saved successfully!")

# if __name__ == "__main__":
#     create_vector_store()
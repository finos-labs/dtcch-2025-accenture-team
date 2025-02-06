import os
import json
import boto3
import time
import pandas as pd
import re

from langchain.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings

from .utils import load_config, load_prompt, bedrock_client, chatbedrock_llm

def run_similarity_matching(user_session,control_filter):
    """
    Runs similarity matching on filtered control data using a vector database and LLM.
    
    Returns:
        pd.DataFrame: DataFrame containing the similarity matching results.
    """

    vector_db_path = f"./{user_session}/controls_mapping/faiss_vectorstore"
    output_folder_path = f"./{user_session}/controls_mapping/output"
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    config = load_config()
    
    
    top_k = int(config["parameters"]["similarity_top_k"]) # change according to your need
    prompt_path = config["prompt"]["prompt_file"]
    
    ### Commented out code used for demo purposes
    # vector_db_path = config["paths"]["vector_db_path"]
    # control_data_path = config["paths"]["control_data_path"]
    # control_sheet_name = config["paths"]["control_sheet_name"]
    # output_folder_path = config["paths"]["output_folder_path"]
    # control_filter = eval(config["control_filter"]["control_filter"])
    
    region = config["bedrock"]["region"] # replace with your desired region
    embedding_model_id = config["bedrock"]["embedding_model_id"] # replace with your desired bedrock model id
    model_id = config["bedrock"]["model_id"] # replace with your desired bedrock model id
    temperature = float(config["bedrock"]["temperature"]) # replace with your desired value

    # Load Embedding and LLM Model
    embedding_model = BedrockEmbeddings(region_name=region, model_id=embedding_model_id)
    llm = chatbedrock_llm(bedrock_client(region), model_id, temperature)
    
    # Load vector store
    vectorstore = FAISS.load_local(vector_db_path, embeddings=embedding_model, allow_dangerous_deserialization=True)

    # Load filtered data
        df = pd.read_excel(f"./{user_session}/controls_mapping/input/extracted_structure_<Name of the latest file>.xlsx")  ### This is assuming DORA regulations

    ### Commented out code used in demo
    # df = pd.read_excel(control_data_path, sheet_name=control_sheet_name, index_col=None)
    # df = df.drop(columns=['Unnamed: 0', 'BCSer performing mappings'], errors='ignore')
    filtered_df = df[df['L2 Control ID'].isin(control_filter)]
    print(f"Filtered Controls: {control_filter}")
    print(f"Filtered DataFrame Shape: {filtered_df.shape}")

    # Load LLM prompt
    prompt_template = load_prompt(prompt_path)
    final_output = []
    
    for index, row in filtered_df.iterrows():
        search_list = {
            'L1 Control ID': row['L1 Control ID'],
            'L1 Control Title': row['L1 Control Title'],
            'L2 Control ID': row['L2 Control ID'],
            'L2 Control Title': row['L2 Control Title']
        }
    
        query = f"Control Activity : {row['L2 Control Activity']}"
        results = vectorstore.similarity_search(query, k=top_k)

        for res in results:
            loop_start_time = time.time()
            
            prompt = prompt_template.format(
                original_objective=query,
                matched_objective=res.metadata.get("Policy statement wording", res.page_content)
            )

            response = llm.invoke(prompt).content
    
            try:
                # Ensure LLM response contains expected tags
                start_tag, end_tag = "<json>", "</json>"
    
                if start_tag in response and end_tag in response:
                    refined_response = response.split(start_tag)[1].split(end_tag)[0].strip()
                else:
                    raise ValueError("JSON tags not found in LLM response")
    
                # Remove invalid control characters
                refined_response = re.sub(r'[\x00-\x1F\x7F]', '', refined_response)
    
                # Ensure valid JSON format
                refined_response_final = json.loads(refined_response)
    
                if isinstance(refined_response_final, dict):
                    search_list.update(res.metadata)
                    search_list.update(refined_response_final)
                else:
                    search_list.update(res.metadata)
                    search_list["error"] = "Unexpected response format"
    
            except Exception as e:
                search_list.update(res.metadata)
                search_list["error"] = f"Parsing error: {str(e)}"
    
            final_output.append(search_list.copy())  # Prevents overwriting data
    
            loop_end_time = time.time()
            print(f"{index} - Time taken: {loop_end_time - loop_start_time:.2f} seconds")

    # Save results as CSV
    df_output = pd.DataFrame(final_output)
    df_output.to_csv(f"{output_folder_path}/output_filter.csv", index=False)
    print("CSV file saved successfully!")
    print("Similarity matching completed!")
    return df_output

def get_controls(user_session,control_filter):
    """
    Runs similarity matching and returns the resulting DataFrame.
    
    Returns:
        pd.DataFrame: DataFrame containing matched control data.
    """
    return run_similarity_matching(user_session,control_filter)
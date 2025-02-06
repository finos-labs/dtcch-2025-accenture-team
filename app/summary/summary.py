#!/usr/bin/env python3
import os
import json
import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import boto3
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Load environment variables from .env file
# -----------------------------------------------------------------------------
load_dotenv()

# -----------------------------------------------------------------------------
# Logging configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# -----------------------------------------------------------------------------
# Constants and AWS Client Initialization
# -----------------------------------------------------------------------------
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

# Initialize AWS Bedrock runtime client
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# -----------------------------------------------------------------------------
# LLM Invocation Function (Do not change any prompts)
# -----------------------------------------------------------------------------
def invoke_sonnet_3_5(prompt, model_id=BEDROCK_MODEL_ID, temperature=0, max_tokens=100000):
    """
    Invokes the Claude 3.5 Sonnet model on AWS Bedrock.

    :param prompt: The input text prompt.
    :param model_id: The Bedrock model ID for Claude 3.5 Sonnet.
    :param temperature: Controls randomness in response (0 = deterministic, 1 = more creative).
    :param max_tokens: Maximum number of tokens to generate in response.
    :return: The model's response as a string.
    """
    try:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read().decode("utf-8"))
        return result.get("content", [{"text": "No response generated"}])[0]["text"].strip()
    except Exception as e:
        logging.error(f"Error invoking the model: {str(e)}")
        return f"Error invoking the model: {str(e)}"

# -----------------------------------------------------------------------------
# Function to Identify the Closest Matching Sub-Theme
# -----------------------------------------------------------------------------
def get_identified_sub_theme(theme, sub_theme, list_old_sub_theme):
    """
    Identifies the closest matching sub-theme from an old document using an LLM (Large Language Model) call.

    This function takes a given theme and sub-theme from a latest document and attempts to find the 
    most similar sub-theme from a provided list of old sub-themes using an LLM.

    Args:
        theme (str): The main theme associated with the sub-theme.
        sub_theme (str): The sub-theme from the latest document.
        list_old_sub_theme (list): A list of sub-themes from the old document.

    Returns:
        tuple: A tuple containing:
            - theme (str): The original theme.
            - sub_theme (str): The sub-theme from the latest document (converted to lowercase).
            - ident_sub_theme (str): The identified closest matching sub-theme from the old document 
              or 'None' if no match is found.

    """
    sub_theme = sub_theme.lower()
    logging.info(f"Processing Theme: {theme}, Sub-theme: {sub_theme}")
    logging.debug(f"List of old sub-themes: {list_old_sub_theme}")
    
    identify_sub_theme_prompt = f"""
    You are given a list of sub-themes from an old document and a sub-theme from the latest document.
    Please return the sub-theme that closely matches from the list. If none match, return 'None'.

    List of old sub-theme list:
    {list_old_sub_theme}z

    Sub-theme from latest document:
    {sub_theme}

    Final output should be just the sub-theme name or 'None'.
    """
    
    ident_sub_theme = invoke_sonnet_3_5(identify_sub_theme_prompt)
    logging.info(f"Identified sub-theme: {ident_sub_theme}")
    time.sleep(random.uniform(0.1, 0.3))
    return theme, sub_theme, ident_sub_theme

# -----------------------------------------------------------------------------
# Main processing function
# -----------------------------------------------------------------------------
def main(old_excel_path, new_excel_path, output_dir):
    """
    Compares old and new versions of DORA (Digital Operational Resilience Act) proposal documents and generates detailed analysis at sub-theme, theme,
    and document levels.

    This function performs the following tasks:
    1. Loads two Excel files: one for the old proposal and another for the new DORA document.
    2. Normalizes and processes the theme and sub-theme fields in both documents.
    3. Performs sub-theme comparison by checking matching sub-themes between the old and new documents.
    4. Uses a language model (Sonnet 3.5) to analyze the differences and impacts between old and new content at sub-theme, theme, and document levels.
    5. Saves the generated analysis to Excel and text files in the specified output directory.

    Parameters:
    old_excel_path (str): The file path for the old DORA proposal Excel document.
    new_excel_path (str): The file path for the new DORA Excel document.
    output_dir (str): The directory path where the analysis results will be saved.

    Returns:
    tuple: A tuple containing:
        - document_level_summary_response (str): The analysis at the document level.
        - theme_df (pd.DataFrame): A DataFrame containing the analysis at the theme level.
        - comp_analyis_df (pd.DataFrame): A DataFrame containing the analysis at the sub-theme level.
    
    Logs are generated to track the loading of files, comparison progress, and output saving.
    """
    # Load the new DORA Excel file
    try:
        logging.info(f"Loading new DORA Excel file: {new_excel_path}")
        dora_extract = pd.read_excel(new_excel_path, engine="openpyxl")
        logging.info("New DORA Excel file loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading {new_excel_path}: {str(e)}")
        return

    # Load the old proposal Excel file
    try:
        logging.info(f"Loading old proposal Excel file: {old_excel_path}")
        dora_proposal = pd.read_excel(old_excel_path, engine="openpyxl")
        logging.info("Old proposal Excel file loaded successfully.")
    except Exception as e:
        logging.error(f"Error loading {old_excel_path}: {str(e)}")
        return

    # Normalize theme and sub-theme fields (lowercase conversion)
    dora_proposal['Theme'] = dora_proposal['Theme'].str.lower()
    dora_extract['Theme'] = dora_extract['Theme'].str.lower()

    # Get unique themes (after stripping punctuation)
    old_theam = [x.replace('.', '').strip().lower() for x in dora_proposal['Theme'].unique().tolist()]
    new_theam = [x.replace('.', '').strip().lower() for x in dora_extract['Theme'].unique().tolist()]

    sub_theme_not_found = []
    comp_analyis = []

    # Process each theme from the new document
    for theme in new_theam:
        theme = theme.lower()
        logging.info(f"🔍 Checking Theme: {theme}")

        # Get the list of old and new sub-themes for the theme
        list_old_sub_theme = dora_proposal[dora_proposal['Theme'].str.contains(theme, na=False)]['Sub-theme'].unique().tolist()
        new_sub_theme_list = dora_extract[dora_extract['Theme'].str.contains(theme, na=False)]['Sub-theme'].unique().tolist()

        # Process sub-themes concurrently
        with ThreadPoolExecutor(max_workers=1) as executor:
            results = list(executor.map(lambda sub_theme: get_identified_sub_theme(theme, sub_theme, list_old_sub_theme),
                                        new_sub_theme_list))

        # Process the LLM results for each sub-theme
        for theme_val, sub_theme, ident_sub_theme in results:
            new_content_series = dora_extract[dora_extract['Sub-theme'].str.lower() == sub_theme]['Policy statement wording']
            new_proposed_content = new_content_series.values[0] if not new_content_series.empty else "No content found"

            if ident_sub_theme == 'None':
                sub_theme_not_found.append({
                    'theme': theme_val,
                    'sub_theme': sub_theme,
                    'new_proposed_content': new_proposed_content
                })
                logging.info(f"❌ Sub-theme not found: {sub_theme} (in theme {theme_val})")
                continue  # Skip analysis if no matching sub-theme is found

            logging.info(f"✅ Sub-theme match found: {sub_theme} → Matched with old sub-theme: {ident_sub_theme}")

            old_content_series = dora_proposal[dora_proposal['Sub-theme'].str.lower() == ident_sub_theme.lower()]['Policy statement wording']
            old_proposed_content = old_content_series.values[0] if not old_content_series.empty else "No content found"

            # LLM Comparison Prompt
            comp_analyis_prompt = f"""
            You are an expert in DORA regulation documents.
            Your task is to compare two sub-theme sections (old vs. new) and highlight:
            1. What are the major changes happened between the old and the new version and highlight 
            them
            2. Do an impact analysis of the identified changes. 
            3. The analysis should contain any change in legal interpretation or regulatory impact.

            Old proposed content:
            {old_proposed_content}

            New proposed content:
            {new_proposed_content}

            Provide a concise and structured analysis of regulatory changes that have a tangible impact on implementation, compliance, regulatory interpretation, or operational execution. The summary should be organized under clear headings. Avoid bullet points and ensure the content is written in a continuous, narrative style. Focus on modifications that influence practical outcomes, decision-making, or enforcement while eliminating redundancy and superficial comparisons. Minor structural, formatting, or linguistic adjustments should be ignored unless they materially affect meaning or obligations. The analysis should clearly articulate the real-world implications of these changes in a direct and precise manner. overall response should be strictly within 200 words.
            """
            analysis_response = invoke_sonnet_3_5(comp_analyis_prompt)
            comp_analyis.append({
                'theme': theme_val,
                'old_sub_theme': ident_sub_theme,
                'new_sub_theme': sub_theme,
                'analysis': analysis_response
            })
            logging.info(f"✅ Analysis completed for sub-theme: {sub_theme}")
            time.sleep(random.uniform(0.1, 0.3))  # Throttle LLM calls

    # Create DataFrame for sub-theme level analysis
    comp_analyis_df = pd.DataFrame(comp_analyis)
    
    # -----------------------------------------------------------------------------
    # Theme-Level Analysis
    # -----------------------------------------------------------------------------
    sections = comp_analyis_df['theme'].unique().tolist()
    theme_dict = []
    for sec in sections:
        filtered_df = comp_analyis_df[comp_analyis_df['theme'] == sec][['theme', 'new_sub_theme', 'analysis']]
        summary_prompt = f"""
        You are an expert in DORA regulation documents.
            Your task is to provide an insightful summary of the analysis based on the 
            following parameters.
            1. What are the major changes happened between the old and the new version and highlight 
            them
            2. Do an impact analysis of the identified changes. 
            3. The analysis should contain any change in legal interpretation or regulatory impact.

            analysis:
            {filtered_df.to_dict(orient='records')}

Provide a concise and structured analysis of regulatory changes that have a tangible impact on implementation, compliance, regulatory interpretation, or operational execution. The summary should be organized under clear headings. Avoid bullet points and ensure the content is written in a continuous, narrative style. Focus on modifications that influence practical outcomes, decision-making, or enforcement while eliminating redundancy and superficial comparisons. Minor structural, formatting, or linguistic adjustments should be ignored unless they materially affect meaning or obligations. The analysis should clearly articulate the real-world implications of these changes in a direct and precise manner. overall response should be strictly within 200 words.
        """
        summary_response = invoke_sonnet_3_5(summary_prompt)
        theme_dict.append({
            'theme': sec,
            'analysis': summary_response
        })
        logging.info(f"✅ Theme level analysis completed for theme: {sec}")
        time.sleep(random.uniform(0.1, 0.3))

    theme_df = pd.DataFrame(theme_dict)

    # -----------------------------------------------------------------------------
    # Document-Level Analysis
    # -----------------------------------------------------------------------------
    document_level_summary_prompt = f"""
    You are an expert in analyzing regulatory documents, specifically DORA regulations.
 
    Your task is to generate a structured and insightful document-level summary of the regulations. The summary should follow these key points:
     
    Overview of the Enacted Regulation: Begin with a concise summary of the new regulatory document, outlining its scope, objectives, and key themes.
     
    Major Changes and Regulatory Priorities: Identify and highlight the most significant modifications. Focus on changes in regulatory requirements, 
    compliance obligations, enforcement priorities, and any shifts in legislative intent.
     
    Impact Analysis: Assess the implications of these changes, considering their effect on compliance, enforcement, and operational execution. 
    This should include any shifts in legal interpretation, regulatory burden, or strategic adjustments that organizations must undertake.
     
    Analysis Data:
    {theme_df.to_dict(orient='records')}
     
    The summary should be written in a structured, narrative format under clear headings, avoiding bullet points. Prioritize substantial regulatory changes that
    have a tangible impact on implementation, decision-making, and enforcement. Minor modifications related to formatting, structure, or wording should be 
    ignored unless they materially alter obligations or regulatory intent. Ensure the analysis is direct, precise, and focused on the real-world consequences of 
    these regulatory updates. overall response should be strictly within 500 words.
    """
    document_level_summary_response = invoke_sonnet_3_5(document_level_summary_prompt)
    logging.info("✅ Document level analysis completed.")

    # -----------------------------------------------------------------------------
    # Save Outputs
    # -----------------------------------------------------------------------------
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    sub_theme_output_path = os.path.join(output_dir, "sub_theme_level.xlsx")
    theme_level_output_path = os.path.join(output_dir, "theme_level.xlsx")
    doc_level_output_path = os.path.join(output_dir, "document_level.txt")

    try:
        comp_analyis_df.to_excel(sub_theme_output_path, index=False)
        logging.info(f"Sub-theme level summary saved to {sub_theme_output_path}")
    except Exception as e:
        logging.error(f"Error saving sub-theme level summary: {str(e)}")
    
    try:
        theme_df.to_excel(theme_level_output_path, index=False)
        logging.info(f"Theme level summary saved to {theme_level_output_path}")
    except Exception as e:
        logging.error(f"Error saving theme level summary: {str(e)}")
    
    try:
        with open(doc_level_output_path, "w") as f:
            f.write(document_level_summary_response)
        logging.info(f"Document level summary saved to {doc_level_output_path}")
    except Exception as e:
        logging.error(f"Error saving document level summary: {str(e)}")

    return document_level_summary_response,theme_df, comp_analyis_df


def get_summary(old_excel_path, new_excel_path,user_session):
    """
    Generates a structured summary of the comparison between the old and new DORA proposal documents.

    This function reads the analysis results saved from the previous comparison process (sub-theme, theme, and document level) and constructs a nested dictionary structure that includes the following:
    1. Document-level summary: A concise analysis of the overall changes between the old and new versions.
    2. Theme-level summary: Detailed analysis for each theme.
    3. Sub-theme-level summary: Specific analysis for each sub-theme within each theme.

    Parameters:
    old_excel_path (str): The file path for the old DORA proposal Excel document (used for reference).
    new_excel_path (str): The file path for the new DORA Excel document (used for comparison).
    user_session (str): A string identifier for the user session, which is used to organize output directories and files (not currently used in the demo version).

    Returns:
    dict: A dictionary
    """
    ###Commented out for demo purpose
    output_dir=f"./{user_session}/comparison_output"
    document_level_summary_response,theme_df, comp_analysis_df= main(old_excel_path, new_excel_path,output_dir)

    ### Commented code was used for demo purpose
    # with open('./summary/comparison_output/document_level.txt', 'r') as file:
    #     document_level_summary_response = file.read()

    # theme_df = pd.read_excel('./summary/comparison_output/theme_level.xlsx',engine='openpyxl')
    # comp_analysis_df = pd.read_excel('./summary/comparison_output/sub_theme_level.xlsx',engine='openpyxl')
    
    structure = {
    'document summary': document_level_summary_response,
    'themes': []
}

# Loop through the theme-level dataframe and construct the structure
    for _, theme_row in theme_df.iterrows():
        theme_name = theme_row['theme']
        theme_analysis = theme_row['analysis']
    
        # Filter the sub-theme dataframe for the current theme
        sub_themes = comp_analysis_df[comp_analysis_df['theme'] == theme_name]
    
        # Create the sub-theme list
        sub_theme_list = []
        for _, sub_theme_row in sub_themes.iterrows():
            sub_theme_list.append({
                'name': sub_theme_row['new_sub_theme'],
                'summary': sub_theme_row['analysis']
            })
    
        # Add the theme and its sub-themes to the structure
        structure['themes'].append({
            'name': theme_name,
            'summary': theme_analysis,
            'subThemes': sub_theme_list
        })

    return structure

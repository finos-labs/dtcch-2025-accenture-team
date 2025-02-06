import os
import boto3
import time
import pandas as pd
import io
import re
from datetime import datetime
from io import BytesIO

# AWS Configuration
AWS_REGION = "us-west-2"

# Initialize AWS clients
textract_client = boto3.client("textract", region_name=AWS_REGION)
s3_client = boto3.client("s3", region_name=AWS_REGION)

def start_textract_job(bucket, document):
    """
    Starts an AWS Textract text detection job to process a document stored in an S3 bucket.
    
    Args:
        bucket (str): Name of the S3 bucket where the document is stored.
        document (str): The file path of the document within the S3 bucket.
    
    Returns:
        str: Job ID of the initiated Textract job.
    """
    try:
        response = textract_client.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": bucket, "Name": document}}
        )
        return response["JobId"]
    except Exception as e:
        print(f"Error starting Textract job: {e}")
        raise


def wait_for_textract_job(job_id):
    """
    Waits for an Amazon Textract job to complete.

    This function continuously checks the status of a Textract job using 
    the provided job ID. It prints the job status and waits for it to 
    either succeed or fail. If the job fails, an exception is raised.

    Args:
        job_id (str): The unique identifier of the Textract job.

    Raises:
        Exception: If the Textract job fails or encounters an error.

    """
    try:
        while True:
            response = textract_client.get_document_text_detection(JobId=job_id)
            job_status = response["JobStatus"]
            print(f"🔄 Textract Job Status: {job_status}")

            if job_status == "SUCCEEDED":
                break
            elif job_status == "FAILED":
                raise Exception("❌ Textract job failed!")

            time.sleep(5)
    except Exception as e:
        print(f"Error waiting for Textract job: {e}")
        raise

def fetch_textract_results(job_id):
    """
    Fetches the extracted text results from an Amazon Textract job.

    Args:
        job_id (str): The unique identifier of the Textract job.

    Returns:
        list: A list of detected text blocks from the document.
    """
    pages = []
    next_token = None

    try:
        while True:
            response = (
                textract_client.get_document_text_detection(JobId=job_id, NextToken=next_token)
                if next_token
                else textract_client.get_document_text_detection(JobId=job_id)
            )
            if "Blocks" in response and response["Blocks"]:
                pages.extend(response["Blocks"])
            if "NextToken" in response:
                next_token = response["NextToken"]
            else:
                break
    except Exception as e:
        print(f"Error fetching Textract results: {e}")
        raise

    return pages

import re

def parse_text_blocks(blocks):
    """
    Parses text blocks to extract structured content from a document.

    Args:
        blocks (list): A list of text blocks extracted by Amazon Textract.

    Returns:
        list: A structured list where each entry contains:
            - Chapter number (str)
            - Chapter name (str or None)
            - Article number (str or None)
            - Article name (str or None)
            - Extracted content (str)
    """
    extracted_data = []
    current_chapter, current_chapter_name, current_article, current_article_name, content = None, None, None, None, []
    next_is_chapter_name, next_is_article_name, is_processing = False, False, False

    ### Search pattern decided based on DORA regulation document.
    chapter_pattern = re.compile(r"\bCHAPTER\s+[IVXLCDM]+\b", re.IGNORECASE)
    article_pattern = re.compile(r"\bArticle\s+\d+\b", re.IGNORECASE)
    sub_article_pattern = re.compile(r"\bArticle\s+\d+\(\d+\)\b", re.IGNORECASE)

    try:
        for block in blocks:
            if block["BlockType"] == "LINE":
                text = block["Text"].strip()

                if next_is_chapter_name:
                    current_chapter_name = text
                    next_is_chapter_name = False
                    continue

                if next_is_article_name:
                    current_article_name = text
                    next_is_article_name = False
                    continue

                if chapter_pattern.match(text):
                    is_processing = True
                    if current_article and content:
                        extracted_data.append([current_chapter, current_chapter_name, current_article, current_article_name, " ".join(content)])
                        content = []
                    current_chapter, current_chapter_name, current_article, current_article_name = text, None, None, None
                    next_is_chapter_name = True

                elif is_processing and article_pattern.match(text):
                    if current_article and content:
                        extracted_data.append([current_chapter, current_chapter_name, current_article, current_article_name, " ".join(content)])
                        content = []
                    current_article, current_article_name = text, None
                    next_is_article_name = True

                elif is_processing and sub_article_pattern.match(text):
                    if current_article:
                        content.append(f"[Sub-Article: {text}]")
                    continue

                elif is_processing and current_chapter:
                    if current_article:
                        content.append(text)

        if current_article and content:
            extracted_data.append([current_chapter, current_chapter_name, current_article, current_article_name, " ".join(content)])
    except Exception as e:
        print(f"Error parsing text blocks: {e}")
        raise

    return extracted_data

import pandas as pd
import io
import boto3

s3_client = boto3.client("s3")

def save_to_s3(data, bucket, output_path):
    """
    Saves extracted data to an Amazon S3 bucket as an Excel file.

    Args:
        data (list): A list of extracted data, where each entry contains:
            - Chapter number (str)
            - Chapter name (str or None)
            - Article number (str or None)
            - Article name (str or None)
            - Extracted content (str)
        bucket (str): The name of the S3 bucket.
        output_path (str): The S3 key (file path) where the Excel file will be saved.

    Returns:
        None
    """
    try:
        df = pd.DataFrame(data, columns=["Chapter", "Chapter Name", "Article", "Article Name", "Content"])
        output_buffer = io.BytesIO()
        df.to_excel(output_buffer, index=False, engine='xlsxwriter')
        s3_client.put_object(
            Bucket=bucket,
            Key=output_path,
            Body=output_buffer.getvalue(),
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        print(f"✅ Extracted data saved to S3: s3://{bucket}/{output_path}")
    except Exception as e:
        print(f"Error saving file to S3: {e}")
        raise

def process_pdf(bucket_name, file_path, output_path):
    """
    Processes a PDF file from an Amazon S3 bucket, extracts text using Textract, 
    and saves the structured results back to S3 as an Excel file.

    Args:
        bucket_name (str): The name of the S3 bucket containing the PDF file.
        file_path (str): The key (file path) of the PDF file in the S3 bucket.
        output_path (str): The S3 key (file path) where the extracted results will be saved.

    Returns:
        None
    """
    try:
        job_id = start_textract_job(bucket_name, file_path)
        wait_for_textract_job(job_id)
        text_blocks = fetch_textract_results(job_id)
        structured_data = parse_text_blocks(text_blocks)
        save_to_s3(structured_data, bucket_name, output_path)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        raise


def merge_sub_articles(bucket_name, input_file_key, output_file_key, sheet_name=0):
    """
    Merges sub-articles in the extracted document by handling article numbers, themes, and sub-themes.
    Reads an Excel file from S3, processes its structure, and saves a cleaned version back to S3.

    Args:
        bucket_name (str): Name of the S3 bucket.
        input_file_key (str): Path to the input Excel file in S3.
        output_file_key (str): Path to save the cleaned Excel file in S3.
        sheet_name (int, optional): Sheet index to read from the Excel file. Defaults to 0.

    Returns:
        pd.DataFrame: Cleaned DataFrame containing structured articles.
    """
    # Initialize S3 client
    s3 = boto3.client('s3')
    
    # Read file from S3
    obj = s3.get_object(Bucket=bucket_name, Key=input_file_key)
    df = pd.read_excel(BytesIO(obj['Body'].read()), sheet_name=sheet_name)
    
    # Splitting the "Article" column into three separate columns
    if "Article" in df.columns:
        df["Article"] = df["Article"].astype(str)
        df[["Article Word", "Article Number", "Article Extra"]] = df["Article"].str.extract(r"(Article)\s*(\d+)\s*(.*)")
    
    # Convert Article Number to numeric
    df["Article Number"] = pd.to_numeric(df["Article Number"], errors='coerce')
    
    # Identify articles that are not in ascending order or have extra content in "Article Extra"
    df["Out of Order"] = df["Article Extra"].str.strip().ne("")
    
    # Ensure Chapter and Chapter Name forward-fill correctly
    if "Chapter" in df.columns and "Chapter Name" in df.columns:
        df["Chapter"].replace("", pd.NA, inplace=True)  # Convert empty strings to NaN
        df["Chapter Name"].replace("", pd.NA, inplace=True)
        df["Chapter"] = df["Chapter"].ffill()
        df["Chapter Name"] = df["Chapter Name"].ffill()
    else:
        df["Chapter"] = None
        df["Chapter Name"] = None
    
    # Initialize storage for cleaned data
    merged_data = []
    current_chapter_name = ""
    current_article = ""
    current_article_extra = ""
    current_article_name = ""
    current_content = ""
    
    for _, row in df.iterrows():
        chapter_name = row.get("Chapter Name", "")
        article_word = row.get("Article Word", "")
        article_number = row.get("Article Number", "")
        article_extra = row.get("Article Extra", "")
        article_name = row.get("Article Name", "")
        content = row.get("Content", "")
        out_of_order = row.get("Out of Order", False)
        
        article = f"{article_word} {article_number} {article_extra}".strip() if pd.notna(article_number) else ""
        
        if pd.notna(article_number) and not out_of_order:  # New main article found
            if current_article:
                merged_data.append([current_chapter_name, current_article, current_article_name, current_content])
            current_chapter_name = "Amendments" if re.search(r'^Amendments to Regulation', article_name, re.IGNORECASE) else chapter_name
            current_article = article
            current_article_extra = article_extra
            current_article_name = article_name
            current_content = content
        else:  # Sub-article found or flagged as out of order
            current_content += f" {article}{article_name}: {content}" if pd.notna(content) else ""
    
    # Append last article
    if current_article:
        merged_data.append([current_chapter_name, current_article, current_article_name, current_content])
    
    # Create a cleaned DataFrame with reordered columns
    cleaned_df = pd.DataFrame(merged_data, columns=["Title", "Theme", "Sub-Theme", "Content"])
    
    # Save cleaned data back to S3
    output_buffer = BytesIO()
    cleaned_df.to_excel(output_buffer, index=False)
    output_buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=output_file_key, Body=output_buffer.getvalue())
    
    return cleaned_df








    
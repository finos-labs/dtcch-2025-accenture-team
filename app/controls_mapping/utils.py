import configparser
import logging
import boto3

from langchain_aws import ChatBedrock

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_config(config_path="./controls_mapping/config.cfg"):
    """
    Loads configuration from a configuration file.
    
    Args:
        config_path (str): Path to the configuration file.
    
    Returns:
        configparser.ConfigParser: Parsed configuration object.
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def load_prompt(prompt_path):
    """
    Loads the prompt template from a specified file.
    
    Args:
        prompt_path (str): Path to the prompt template file.
    
    Returns:
        str: Contents of the prompt template.
    """
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def bedrock_client(region):
    """
    Creates and returns a Bedrock client session.
    
    Args:
        region (str): AWS region where Bedrock is deployed.
    
    Returns:
        boto3.client: Initialized Bedrock runtime client.
    """
    try:
        session = boto3.session.Session()
        bedrock = session.client(
            service_name='bedrock-runtime',
            region_name=region
        )
        return bedrock
    except Exception as e:
        logging.error(f"Error initializing Bedrock client: {e}")
        return None

def chatbedrock_llm(bedrock_client, model_id, temperature):
    """
    Initializes and returns a ChatBedrock model.
    
    Args:
        bedrock_client (boto3.client): Initialized Bedrock client.
        model_id (str): ID of the model to be used.
        temperature (float): Temperature setting for response generation.
    
    Returns:
        ChatBedrock: Initialized ChatBedrock model.
    """
    try:
        llm = ChatBedrock(
            client=bedrock_client,
            model_id=model_id,
            model_kwargs={"temperature": temperature},
        )
        return llm
    except Exception as e:
        logging.error(f"Error initializing ChatBedrock model: {e}")
        return None

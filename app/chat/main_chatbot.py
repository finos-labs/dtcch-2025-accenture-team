
import boto3
import logging
from langchain_aws import ChatBedrock
from langchain.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_aws import BedrockEmbeddings
from langchain_aws import BedrockLLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from .prompt_templates import contextualize_q_prompt, response_prompt
import os

print(os.path.isdir('./chat/faiss_index'))

logging.info("Script initialized.")
class ChatBot:
    """
    ChatBot class for handling query embeddings, reformulations, and responses.

    Attributes:
        region (str): AWS region for Bedrock services.
        model_id (str): Identifier for the Bedrock language model.
        model_kwargs (dict): Configuration for the model, such as temperature.
        embedding_model_id (str): Identifier for the embedding model.
        vector_store (FAISS): FAISS vector store for similarity searches.
        chat_history (list): Maintains a list of user and bot interactions.
    """
    def __init__(self):
        """
        Initializes the ChatBot with required configurations and embeddings.
        """
        self.region = "us-west-2"
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.model_kwargs = {"temperature": 0.0}
        self.embedding_model_id = "cohere.embed-english-v3"
            # Initialize embeddings
        self.bedrock_embeddings = BedrockEmbeddings(region_name=self.region, model_id=self.embedding_model_id)
        self.vector_store = FAISS.load_local("./chat/faiss_index", self.bedrock_embeddings,allow_dangerous_deserialization=True)
        self.llm = self.chatbedrock_llm()
        self.llm_chain_que = contextualize_q_prompt | self.llm
        self.llm_chain_resp = response_prompt | self.llm
        self.chat_history = []
    def bedrock_client(self):
        """
        Creates a Bedrock client session.

        Returns:
            boto3.client: Bedrock client instance.
        """
        try:
            session = boto3.session.Session()
            logging.info("Establishing Bedrock client session.")
            bedrock = session.client(
                service_name = 'bedrock-runtime',
                region_name = self.region
            )
            return bedrock
        except:
            logging.error(f"Error initializing Bedrock client")
            raise

    def chatbedrock_llm(self):
        """
        Initializes the ChatBedrock model with the required configurations.

        Returns:
            ChatBedrock: ChatBedrock instance with specified configurations.
        """
        try:
            logging.info("Initializing ChatBedrock LLM.")
            llm = ChatBedrock(
                client = self.bedrock_client(),
                model_id = self.model_id,
                model_kwargs = self.model_kwargs,
                guardrails={"guardrailIdentifier": 'e2l0e6q9m2qj' , "guardrailVersion": '1', "trace": True}
            )
            return llm
        except:
            logging.error(f"Error initializing ChatBedrock LLM")
            raise

    def rephrase_question(self, query):
        """
        Rephrases the user query into a standalone question.

        Args:
            query (str): User query to be reformulated.

        Returns:
            str: Reformulated question.
        """
        try:
            logging.info("Rephrasing user query.")
            if len(self.chat_history) > 2:
                self.chat_history = self.chat_history[-2:]
            reformulated_question = self.llm_chain_que.invoke({'input': query, 'chat_history': self.chat_history})
            ##if the llm fails to output a question , we are regenrating using a logic that it does not contain question mark
            if '?' not in reformulated_question.content:
                chat_history = self.chat_history[-1:]
                reformulated_question = self.llm_chain_que.invoke({'input': query, 'chat_history': chat_history})
            if '?' not in reformulated_question.content:
                #returning the orignal query , if it fails to reformulate question twice
                return query
            return reformulated_question.content
        except:
            logging.error(f"Error in rephrasing question")
            raise
    

    def response(self, context, query):
        """
        Generates a response based on the context and query.

        Args:
            context (list): Context retrieved from FAISS similarity search.
            query (str): Reformulated query from the user.

        Returns:
            str: Generated response content.
        """
        try:
            logging.info("Generating response.")
            resp = self.llm_chain_resp.invoke({'context': context, 'input': query})
            return resp.content
        except:
            logging.error(f"Error in response generation")
            raise
    def main(self,user_query):
        """
        Main function to handle user query and return the response.

        Args:
            user_query (str): Original query input by the user.

        Returns:
            str: Final response generated for the user query.
        """
        try:
            logging.info("Processing user query.")
            user_query = self.rephrase_question(user_query)
            question_embedding = self.bedrock_embeddings.embed_query(user_query)
            ##retrieveing the embeddings from both documents seprately for bettr comparision
            match1 = self.vector_store.similarity_search_by_vector(question_embedding, k = 6, filter={"source": "data/EUR_Lex_V2.pdf"})
            match2 = self.vector_store.similarity_search_by_vector(question_embedding, k = 6, filter={"source": "data/Dora_Latest_V2.pdf"})
            match = match1 + match2
            result = self.response(match, user_query)
            self.chat_history.extend([HumanMessage(content=user_query)])
            return result
        except:
            logging.error(f"Error in main processing")
            raise


            
"""
This script defines and utilizes prompt templates for language generation tasks 
using LangChain's `ChatPromptTemplate`. It includes two main functionalities:
1. Reformulating user questions into standalone queries that do not rely on chat history.
2. Generating detailed answers based on provided context, with citations.

Modules:
- langchain_core.prompts: Provides the `ChatPromptTemplate` and `MessagesPlaceholder` 
  classes for constructing and using prompt templates.
"""
import logging
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

contextualize_q_system_prompt = """Given a chat history of user questions and bot responses, and the latest user question:
Reformulate the latest user question into a standalone question that can be understood independently, without relying on the chat history for context.
Do not answer the question.
Do not ask for clarification regarding the question.
Do not incorporate or reference any data from the chat history.
Do not extract or use any data from the chat history that is not explicitly present in the latest user question. Simply reframe or return the latest user question as is if no rephrasing is required.
Penalty: Any response that includes extra content like "Here is the reformulated standalone question:",
"repharsed query" other than a reformulated question or fails to meet the above criteria will be considered invalid."""

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

logging.info("ChatPromptTemplate for question contextualization initialized.")
# Prompt for generating an answer with citations
answer_generation_prompt = """
Use the following pieces of context to provide a 
concise answer to the question at the end but usse atleast summarize with 
250 words with detailed explaantions. If you don't know the answer, 
just say that you don't know, don't try to make up an answer.
Provide in-text citations directly after references in the format (Document_Name, page X). Additionally, list all the citations at the end of the answer under a "Citations" section in the format:
- Document_Name, pages X, Y, Z
<context>
{context}
</context
"""
response_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", answer_generation_prompt),
        ("human", "{input}"),
    ]
)
logging.info("ChatPromptTemplate for response generation initialized.")
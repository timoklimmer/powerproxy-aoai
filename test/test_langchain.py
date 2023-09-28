"""Script to test the proxy's support for langchain."""

from langchain.agents import AgentType, initialize_agent, tool
from langchain.llms import AzureOpenAI

OPENAI_API_BASE = "http://localhost"
OPENAI_API_KEY = "04ae14bc78184621d37f1ce57a52eb7"
OPENAI_API_DEPLOYMENT_NAME = "gpt-35-turbo"
OPENAI_API_VERSION = "2023-03-15-preview"


@tool(return_direct=True)
def search_events(question: str) -> str:
    """
    An events search engine. Use this when the question is about events, like 'What is the next
    game of Barcelona?' or 'When is the next game of 1. FC Kaiserslautern?'
    """
    return "TODO: Pass this to AOAI and have it generate a query for ElasticSearch..."


@tool(return_direct=True)
def glossary(question: str) -> str:
    """
    A glossary. Use this when the question about a term, like 'What is a handicap market?' or
    'Tell me what a handicap bet is!'
    """
    return "TODO: Pass this to the Glossary API and give a response from the glossary."


@tool(return_direct=True)
def default(question: str) -> str:
    """
    Use this when no other tool is applicable or no other tool has returned a response.
    """
    return f"Sorry, I could not find any applicable tool for question '{question}'."


agent = initialize_agent(
    tools=[search_events, glossary, default],
    llm=AzureOpenAI(
        openai_api_base=OPENAI_API_BASE,
        openai_api_key=OPENAI_API_KEY,
        openai_api_version=OPENAI_API_VERSION,
        deployment_name=OPENAI_API_DEPLOYMENT_NAME,
        temperature=0,
    ),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
)


# ---
questions_to_ask = [
    "When is the next game of 1. FC Kaiserslautern?",
    "What is a handicap market?",
    "Who was president of the United States in 1955?",
]

for question in questions_to_ask:
    print("------")
    print(f"Question: {question}")
    print(f"Answer: {agent.run(question)}")
    print()

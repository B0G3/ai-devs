import os
import re

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from tools import TOOLS

load_dotenv()

HUB_URL = os.getenv("HUB_URL")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")

FLAG_PATTERN = re.compile(r"\{FLG:([^}]+)\}")

_SYSTEM_PROMPT = """You are analysing a power-plant failure log to find the root cause of an incident.
Call one tool at a time.
Stop when you receive flag from the hub.
"""


def solve_agentic():
    llm = ChatOpenAI(
        model="gpt-4o",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=4096,
    )
    agent = create_agent(llm, TOOLS, system_prompt=_SYSTEM_PROMPT)

    result = agent.invoke(
        {"messages": [("human",
            "Analyse the failure log and find the flag. "
            "Submit the compressed critical logs to the hub. "
            "If the hub requests more components, include them and resubmit until you receive a {FLG:...} flag."
        )]},
        config={"recursion_limit": 200},
    )

    output = result["messages"][-1].content
    flag = FLAG_PATTERN.search(output)
    if flag:
        print(f"\nFlag found: {flag.group()}")
    else:
        print("\nAgent output:\n", output)


def main():
    solve_agentic()


if __name__ == "__main__":
    main()

import os
import re

from dotenv import load_dotenv

load_dotenv()

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from tools import TOOLS

HUB_URL = os.getenv("HUB_URL", "")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")

FLAG_PATTERN = re.compile(r"\{FLG:([^}]+)\}")

_SYSTEM_PROMPT = """You are a mail API interaction agent.
You can freely interact with all the tools the API has to offer.
Call call_api_action with action="help" and no additional params to discover available actions.

Inbox behaviour:
- The inbox is dynamic — new messages may arrive at any time during your search.
- Account for pagination and re-check the inbox if you suspect new messages have arrived.

Search syntax (Gmail-style operators are supported):
- from:<address or domain>  — filter by sender
- to:<address>              — filter by recipient
- subject:<text>            — filter by subject
- OR, AND                   — combine conditions

Always call one tool at a time.
"""


def solve_agentic():
    llm = ChatOpenAI(
        model="gpt-5-nano-2025-08-07",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=4096,
    )
    agent = create_agent(llm, TOOLS, system_prompt=_SYSTEM_PROMPT)

    result = agent.invoke(
        {"messages": [("human",
            """Search the zmail inbox to find three pieces of information:

1. date - the date (YYYY-MM-DD format) when the security department plans an attack on our power plant
2. password - a password to the employee system that was sent to this mailbox
3. confirmation_code - a ticket confirmation code from the security department (format: SEC- followed by 32 characters, 36 characters total)

Start by calling the help action to understand available API actions.
Then search for emails from Wiktor, who sent a message from the proton.me domain (use: from:proton.me).
Search broadly: look at all emails for attack/security planning dates, passwords, and SEC- codes.
Once you have all three values, report them clearly as:
- date: YYYY-MM-DD
- password: <value>
- confirmation_code: SEC-<32 chars>

Then submit the answer using the verify_answer tool with the three values.
If the verify answer returns a FLG / flag - we've succeeded.
"""
        )]},
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

import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOLS

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a reasoning agent. You work by thinking step by step and using tools to achieve a goal.

You must always respond in this exact format:

Thought: [write your thinking here — what do you know, what do you need, what should you do next]
Action: [write only the tool name here — either: search, summarise, save_to_file, or finish]
Action Input: [write the input for the tool here]

The tools available to you are:
- search: use this to search the web for information. Action Input should be a search query.
- summarise: use this to compress large amounts of text into clean bullet points. Action Input should be the text you want summarised.
- save_to_file: use this to save any important content to a file. Action Input should be the content you want saved.
- finish: use this when you have enough information to answer the goal completely. Action Input should be your complete final answer.

Rules:
- Always think before acting
- Always use search before anything else — gather information first
- Use summarise when search results are too long or complex to work with directly
- Only use finish when you are genuinely satisfied with what you have found
- Never make up information — only use what you find through search
- Never add a year to your search queries — always search without years so you get the most recent results
- Always do at least two searches before finishing — never finish after just one search
"""


def parse_llm_output(llm_output):
    # This function reads the agent's response and extracts:
    # 1. The action name — which tool to use
    # 2. The action input — what to pass to the tool
    # It handles multi-line inputs correctly

    action = None
    action_input = None

    lines = llm_output.split("\n")

    for i, line in enumerate(lines):
        if line.startswith("Action:"):
            action = line.replace("Action:", "").strip().lower()

        if line.startswith("Action Input:"):
            first_line = line.replace("Action Input:", "").strip()
            remaining_lines = lines[i+1:]
            all_input_lines = [first_line] + remaining_lines
            action_input = "\n".join(all_input_lines).strip()
            break

    return action, action_input


def run_agent(goal):
    # This function is now a generator
    # Instead of printing to the terminal it yields updates
    # Each yield sends one piece of information to the Flask stream
    # The webpage receives each update instantly as it happens
    #
    # Think of yield like a live reporter sending updates from the field
    # Instead of waiting until the story is complete and sending it all at once
    # He sends each update the moment it happens
    # "Breaking news — Step 1 starting..."
    # "Breaking news — Agent searched for X..."
    # "Breaking news — Agent found these results..."

    yield f"GOAL: {goal}\n"
    yield "=" * 50 + "\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Your goal is: {goal}"}
    ]

    max_steps = 10

    for step in range(1, max_steps + 1):
        yield f"\n--- Step {step} ---\n"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        llm_output = response.choices[0].message.content

        # Send the agent's thought and action to the webpage
        yield llm_output + "\n"

        messages.append({"role": "assistant", "content": llm_output})

        action, action_input = parse_llm_output(llm_output)

        if not action:
            yield "\nAgent did not return a valid action. Stopping.\n"
            break

        if action == "finish":
            TOOLS["finish"](action_input)
            yield "\n" + "=" * 50 + "\n"
            yield "FINAL ANSWER:\n"
            yield action_input + "\n"
            yield "=" * 50 + "\n"
            break

        if action in TOOLS:
            tool_function = TOOLS[action]

            if action == "search":
                action_input = re.sub(r'\b(19|20)\d{2}\b', '', action_input).strip()

            observation = tool_function(action_input)

            # Send the observation to the webpage
            yield f"\nOBSERVATION:\n{observation}\n"

            messages.append({
                "role": "user",
                "content": f"Observation: {observation}"
            })

        else:
            messages.append({
                "role": "user",
                "content": f"Observation: Tool '{action}' does not exist. Please use only: search, summarise, save_to_file, or finish."
            })

    else:
        yield "\nMax steps reached. Agent did not finish in time.\n"


# This is kept for testing in the terminal if needed
if __name__ == "__main__":
    goal = input("Enter your goal: ")
    for update in run_agent(goal):
        print(update, end="")
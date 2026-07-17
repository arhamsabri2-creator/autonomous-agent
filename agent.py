import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOLS
from memory import search_memory, get_memory_count, save_to_memory

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a reasoning agent with memory. You work by thinking step by step and using tools to achieve a goal.

You must always respond in this exact format:

Thought: [write your thinking here — what do you know, what do you need, what should you do next]
Action: [write only the tool name here — either: search, summarise, remember, save_to_file, check_court_cause_list, deep_research, fill_form, or finish]
Action Input: [write the input for the tool here]

The tools available to you are:
- search: use this for quick lookups, simple facts, or when you only need a short snippet of information. Action Input should be a search query.
- summarise: use this to compress large amounts of text into clean bullet points. Action Input should be the actual text you want summarised — never a placeholder.
- remember: use this to save important findings to memory for future use. Action Input should be the key findings you want to remember.
- save_to_file: use this to save any important content to a file. Action Input should be the content you want saved.
- check_court_cause_list: use this to check today's Delhi High Court cause list for hearings, case listings, or judgments. Action Input can be left empty or contain a specific case name/number you're looking for.
- deep_research: use this when the goal explicitly asks for deep, comprehensive, thorough, or in-depth research on a topic, or when short search snippets would not be enough to properly answer the goal. This reads the full content of top web pages, not just short previews. Prefer this over multiple rounds of search when the goal needs real depth. Action Input should be the research topic.
- fill_form: use this when the goal explicitly asks to fill out or submit a form with specific details. Action Input must be formatted as "name | comment" — the name first, then a pipe character, then the comment or message to submit.
- finish: use this when you have enough information to answer the goal completely. Action Input should be your complete final answer.

Rules:
- Always think before acting
- If memory context is provided at the start — read it carefully and use it
- Only search for information that is missing from memory
- Only plan ONE action at a time — never write multiple Action and Action Input pairs in one response
- Always wait for the Observation before deciding the next action
- When using summarise — always pass the actual text from the Observation, never a placeholder like [text from search]
- Use remember to save important findings before finishing
- Only use finish when you are genuinely satisfied with what you have found
- Never make up information — only use what you find through search, deep_research, or memory
- Never add a year to your search queries — always search without years so you get the most recent results
- If the goal asks for deep, comprehensive, or thorough research, use deep_research instead of doing multiple rounds of search
- If using search instead of deep_research, do at least two searches before finishing
- If the goal asks to fill out or submit a form, use fill_form with the exact "name | comment" format
"""


def parse_llm_output(llm_output):
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
    yield f"GOAL: {goal}\n"
    yield "=" * 50 + "\n"

    memory_count = get_memory_count()
    memory_context = ""

    if memory_count > 0:
        yield f"\nChecking memory... ({memory_count} memories stored)\n"
        relevant_memories = search_memory(goal)

        if relevant_memories:
            memory_context = relevant_memories
            yield f"\nFOUND RELEVANT MEMORY:\n{memory_context}\n"
            yield "=" * 50 + "\n"
        else:
            yield "\nNo relevant memories found. Starting fresh research.\n"
            yield "=" * 50 + "\n"
    else:
        yield "\nNo memories stored yet. Starting fresh research.\n"
        yield "=" * 50 + "\n"

    if memory_context:
        initial_user_message = f"""Your goal is: {goal}

Here is relevant context from your memory of past research:

{memory_context}

Use this memory as a foundation. Only search for information that is missing or needs updating."""
    else:
        initial_user_message = f"Your goal is: {goal}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": initial_user_message}
    ]

    max_steps = 10

    for step in range(1, max_steps + 1):
        yield f"\n--- Step {step} ---\n"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        llm_output = response.choices[0].message.content
        yield llm_output + "\n"

        messages.append({"role": "assistant", "content": llm_output})

        action, action_input = parse_llm_output(llm_output)

        if not action:
            yield "\nAgent did not return a valid action. Stopping.\n"
            break

        if action == "finish":
            save_to_memory(goal, action_input)
            yield "\nSaving to memory...\n"

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

            yield f"\nOBSERVATION:\n{observation}\n"

            messages.append({
                "role": "user",
                "content": f"Observation: {observation}"
            })

        else:
            messages.append({
                "role": "user",
                "content": f"Observation: Tool '{action}' does not exist. Please use only: search, summarise, remember, save_to_file, check_court_cause_list, deep_research, fill_form, or finish."
            })

    else:
        yield "\nMax steps reached. Agent did not finish in time.\n"


if __name__ == "__main__":
    goal = input("Enter your goal: ")
    for update in run_agent(goal):
        print(update, end="")
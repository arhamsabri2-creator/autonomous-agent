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
    #
    # The problem before was that Action Input can span multiple lines
    # For example the finish answer might be 5 lines long
    # The old code only read the first line
    # This new parser reads everything after "Action Input:" until the end
    
    action = None
    action_input = None
    
    lines = llm_output.split("\n")
    
    for i, line in enumerate(lines):
        # Find the Action line and extract the tool name
        if line.startswith("Action:"):
            action = line.replace("Action:", "").strip().lower()
        
        # Find the Action Input line
        # Then collect everything from that line onwards
        # This captures multi-line inputs correctly
        if line.startswith("Action Input:"):
            # Get the first line of the input
            first_line = line.replace("Action Input:", "").strip()
            
            # Get all remaining lines after this one
            remaining_lines = lines[i+1:]
            
            # Combine first line with all remaining lines
            # This captures the full multi-line input
            all_input_lines = [first_line] + remaining_lines
            
            # Join them back together and strip empty space
            action_input = "\n".join(all_input_lines).strip()
            
            # Stop reading once we have the action input
            break
    
    return action, action_input


def run_agent(goal):
    print(f"\nGOAL: {goal}\n")
    print("=" * 50)

    # This list stores the entire conversation history
    # Every thought, action, and observation gets added here
    # The LLM reads all of it each time so it remembers everything
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Your goal is: {goal}"}
    ]

    # Maximum number of steps before we force stop
    # This prevents the agent from running forever
    max_steps = 10

    for step in range(1, max_steps + 1):
        print(f"\n--- Step {step} ---")

        # Send the full conversation history to the LLM
        # It reads everything that has happened so far and decides the next move
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        # Extract the text the LLM returned
        llm_output = response.choices[0].message.content
        print(llm_output)

        # Add the LLM response to conversation history
        # So next time it remembers what it just said
        messages.append({"role": "assistant", "content": llm_output})

        # Use the new parser to extract action and action input
        # This correctly handles multi-line inputs
        action, action_input = parse_llm_output(llm_output)

        # If the LLM did not follow the format stop gracefully
        if not action:
            print("\nAgent did not return a valid action. Stopping.")
            break

        # If the agent chose finish we are done
        # We call the finish tool first so it saves the answer to output.txt
        # Then we print the final answer and break out of the loop
        if action == "finish":
            TOOLS["finish"](action_input)
            print("\n" + "=" * 50)
            print("FINAL ANSWER:")
            print(action_input)
            print("=" * 50)
            break

        # If the agent chose a tool that exists call it
        if action in TOOLS:
            tool_function = TOOLS[action]

            # If the agent is searching strip any years from the query
            # This is a filter between the agent and Tavily
            # It removes years like 2023 or 2024 automatically
            # So the agent always gets the most recent results
            if action == "search":
                action_input = re.sub(r'\b(19|20)\d{2}\b', '', action_input).strip()

            observation = tool_function(action_input)

            print(f"\nOBSERVATION:\n{observation}")

            # Add the observation to conversation history
            # So the LLM can read the results and decide what to do next
            messages.append({
                "role": "user",
                "content": f"Observation: {observation}"
            })

        else:
            # The agent tried to use a tool that does not exist
            messages.append({
                "role": "user",
                "content": f"Observation: Tool '{action}' does not exist. Please use only: search, summarise, save_to_file, or finish."
            })

    else:
        # This runs if the loop completes all 10 steps without finishing
        print("\nMax steps reached. Agent did not finish in time.")


# Entry point — when you run python3 agent.py
# it asks you to type a goal and runs the agent
if __name__ == "__main__":
    goal = input("Enter your goal: ")
    run_agent(goal)
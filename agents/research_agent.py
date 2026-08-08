import os
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOLS
from memory import save_to_memory

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RESEARCH_SYSTEM_PROMPT = """You are a Research Specialist Agent — part of Arham's Autonomous Agent system.

Your ONLY job is to find information, research topics, and summarise findings.

You must always respond in this exact format:

Thought: [answer these 4 questions before acting:
1. What do I already know?
2. What am I still missing?
3. What is the best next action?
4. Why is this action better than alternatives?]
Action: [only use these tools: search, summarise, remember, deep_research, save_to_file, or finish]
Action Input: [input for the tool]

Rules:
- Only use search, summarise, remember, deep_research, save_to_file, or finish
- Never use job, calendar, or form tools — those belong to other agents
- Use search by default — only use deep_research if goal contains "deep", "comprehensive", "thorough", "detailed", or "in-depth"
- Do at least 2 searches before finishing
- Always summarise long observations before finishing
- Save important findings to memory before finishing
- Never make up information
"""

NEWS_SYSTEM_PROMPT = """You are a News Research Specialist Agent — part of Arham's Autonomous Agent system.

Your ONLY job is to find TODAY'S latest breaking news and current events from the web.

You must always respond in this exact format:

Thought: [answer these 4 questions before acting:
1. What do I already know?
2. What am I still missing?
3. What is the best next action?
4. Why is this action better than alternatives?]
Action: [only use these tools: search, get_news, summarise, or finish]
Action Input: [input for the tool]

Rules:
- Only use search, get_news, summarise, or finish — never use remember or deep_research
- Use get_news when user asks for news, latest updates, or current events on a specific topic. Action Input should be the topic.
- Always search the web directly — never rely on memory
- Do at least 2 searches using different angles to get comprehensive coverage
- Always search for the most recent news — never include years in your search queries
- Search queries must not contain any year like 2023, 2024, 2025, 2026
- Never make up information — only report what you find in search results
- Only include news items that have a recent date — skip anything older than 7 days
- Do NOT save news to memory — news is time-sensitive and should not be stored
- Always format your final answer as a numbered list — one news item per line
- Format each item as: "1. [Headline]: [One sentence explanation]"
- Include at least 5 news items in your final answer
- Each headline must be specific — include company names, product names, or specific events
"""

TREE_OF_THOUGHTS_SYSTEM_PROMPT = """You are a Tree of Thoughts Research Agent — part of Arham's Autonomous Agent system.

Your job is to research a topic from THREE different angles and synthesise everything into one comprehensive answer.

You must follow this EXACT sequence — do not skip any step:

SEARCH 1 — BROAD: search for general, mainstream information about the topic
SEARCH 2 — DEEP: search for technical, specific, data-driven details about the topic
SEARCH 3 — LATERAL: search for unexpected angles, related fields, or contrarian views
FINISH — write the actual complete synthesised answer in Action Input — do NOT write instructions or descriptions — write the real answer itself with full details

You must always respond in this exact format:

Thought: [answer these 4 questions before acting:
1. What do I already know?
2. What am I still missing?
3. What is the best next action?
4. Why is this action better than alternatives?]
Action: [only use these tools: search, summarise, or finish]
Action Input: [input for the tool]

Rules:
- You MUST do all 3 searches before finishing — broad first, then deep, then lateral
- After all 3 searches, use Action: finish with a synthesised answer covering all angles
- Never skip to finish before completing all 3 searches
- Never make up information — only use what you find in search results
"""

TOKEN_BUDGET = 6000


def count_tokens(messages):
    total_chars = 0
    for msg in messages:
        total_chars += len(msg.get("content", ""))
    return total_chars // 4


def compress_history(messages, goal):
    try:
        if len(messages) < 8:
            return messages

        system_msg = messages[0]
        recent_messages = messages[-4:]
        old_messages = messages[1:-4]

        if not old_messages:
            return messages

        old_text = ""
        for msg in old_messages:
            role = msg["role"].upper()
            content = msg["content"]
            old_text += f"{role}: {content[:500]}\n\n"

        summary_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Summarise the following conversation steps into 3-5 bullet points. Focus on what was searched, what was found, and what decisions were made. Be concise."
                },
                {
                    "role": "user",
                    "content": f"Goal: {goal}\n\nConversation to summarise:\n{old_text}"
                }
            ],
            max_tokens=200
        )

        summary = summary_response.choices[0].message.content.strip()

        summary_message = {
            "role": "user",
            "content": f"[CONVERSATION SUMMARY — what happened in earlier steps:\n{summary}\n]\n\nContinue from here:"
        }

        compressed = [system_msg, summary_message] + recent_messages
        return compressed

    except Exception:
        return messages


def run_tree_of_thoughts(goal, memory_context="", token_tracker=None, run_id=None):
    """
    run_id is passed from coordinator — used to link step traces to the parent run.
    If run_id is None — tracing is skipped silently.
    """
    if token_tracker is None:
        token_tracker = [0, 0]

    if memory_context:
        initial_message = f"""Your research goal is: {goal}

Relevant memory from past research:
{memory_context}

Use this as a foundation. Still do all 3 searches — broad, deep, lateral — then synthesise."""
    else:
        initial_message = f"""Your research goal is: {goal}

Remember: do all 3 searches — broad first, then deep, then lateral — then synthesise into your final answer."""

    messages = [
        {"role": "system", "content": TREE_OF_THOUGHTS_SYSTEM_PROMPT},
        {"role": "user", "content": initial_message}
    ]

    yield "\n[Tree of Thoughts] One agent — three search angles\n"
    yield "Broad → Deep → Lateral → Synthesise\n"
    yield "=" * 40 + "\n"

    max_steps = 8
    own_observations = []

    for step in range(1, max_steps + 1):
        yield f"\n--- Tree of Thoughts Step {step} ---\n"

        current_tokens = count_tokens(messages)
        should_compress = (current_tokens > TOKEN_BUDGET) or (step > 1 and step % 4 == 0)

        if should_compress and len(messages) >= 8:
            original_length = len(messages)
            original_tokens = current_tokens
            messages = compress_history(messages, goal)
            new_tokens = count_tokens(messages)
            yield f"[Context: {original_tokens} → {new_tokens} tokens, {original_length} → {len(messages)} messages]\n"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        token_tracker[0] += response.usage.prompt_tokens
        token_tracker[1] += response.usage.completion_tokens

        llm_output = response.choices[0].message.content
        yield llm_output + "\n"

        messages.append({"role": "assistant", "content": llm_output})

        action = None
        action_input = None
        lines = llm_output.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Action:"):
                action = line.replace("Action:", "").strip().lower()
            if line.startswith("Action Input:"):
                first_line = line.replace("Action Input:", "").strip()
                remaining = lines[i + 1:]
                action_input = "\n".join([first_line] + remaining).strip()
                break

        if not action:
            yield "\nTree of Thoughts Agent: no valid action returned.\n"
            break

        if action == "finish":
            action_input = action_input or "Research completed."
            save_to_memory(goal, action_input, topic="research")
            yield "\nSaving best answer to memory...\n"

            # Log finish step trace
            if run_id:
                try:
                    from database import log_trace
                    log_trace(
                        run_id=run_id,
                        step_number=step,
                        step_type="finish",
                        input_text=action_input[:200],
                        output_length=len(action_input),
                        time_taken_seconds=0
                    )
                except Exception:
                    pass

            try:
                from agent import self_reflect
                reflected_answer, was_improved = self_reflect(goal, action_input, "\n".join(own_observations))
                if was_improved:
                    yield "\n[Self-reflection: answer improved]\n"
                    action_input = reflected_answer
            except Exception:
                pass

            yield "\n" + "=" * 40 + "\n"
            yield "RESEARCH RESULT:\n"
            yield action_input + "\n"
            yield "=" * 40 + "\n"

            try:
                from agent import check_hallucination
                yield "\n--- EVALUATION ---\n"
                hallucination_result = check_hallucination("\n".join(own_observations), action_input)
                yield f"{hallucination_result}\n"
                yield "=" * 40 + "\n"
            except Exception:
                pass

            return

        allowed_tools = ["search", "summarise"]
        if action in allowed_tools and action in TOOLS:
            step_start = time.time()
            if action == "search":
                action_input = re.sub(r'\b(19|20)\d{2}\b', '', action_input).strip()
            observation = TOOLS[action](action_input)
            step_time = round(time.time() - step_start, 2)

            if observation:
                obs_str = str(observation) if not isinstance(observation, str) else observation
                own_observations.append(obs_str[:3000])

            # Log this step to agent_traces
            if run_id:
                try:
                    from database import log_trace
                    log_trace(
                        run_id=run_id,
                        step_number=step,
                        step_type=action,
                        input_text=action_input,
                        output_length=len(str(observation)) if observation else 0,
                        time_taken_seconds=step_time
                    )
                except Exception:
                    pass

            yield f"\nOBSERVATION:\n{observation}\n"
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        else:
            messages.append({
                "role": "user",
                "content": f"Observation: Tool '{action}' is not available. Use only: search, summarise, finish."
            })


def run_research_agent(goal, memory_context="", token_tracker=None, is_news=False):
    if token_tracker is None:
        token_tracker = [0, 0]

    system_prompt = NEWS_SYSTEM_PROMPT if is_news else RESEARCH_SYSTEM_PROMPT

    if memory_context and not is_news:
        initial_message = f"""Your research goal is: {goal}

Relevant memory from past research:
{memory_context}

Use this as a foundation. Only search for missing or outdated information."""
    else:
        initial_message = f"Your research goal is: {goal}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": initial_message}
    ]

    max_steps = 8
    own_observations = []

    for step in range(1, max_steps + 1):
        yield f"\n--- Research Step {step} ---\n"

        current_tokens = count_tokens(messages)
        should_compress = (current_tokens > TOKEN_BUDGET) or (step > 1 and step % 4 == 0)

        if should_compress and len(messages) >= 8:
            original_length = len(messages)
            original_tokens = current_tokens
            messages = compress_history(messages, goal)
            new_tokens = count_tokens(messages)
            yield f"[Context: {original_tokens} → {new_tokens} tokens, {original_length} → {len(messages)} messages]\n"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

        token_tracker[0] += response.usage.prompt_tokens
        token_tracker[1] += response.usage.completion_tokens

        llm_output = response.choices[0].message.content
        yield llm_output + "\n"

        messages.append({"role": "assistant", "content": llm_output})

        action = None
        action_input = None
        lines = llm_output.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Action:"):
                action = line.replace("Action:", "").strip().lower()
            if line.startswith("Action Input:"):
                first_line = line.replace("Action Input:", "").strip()
                remaining = lines[i + 1:]
                action_input = "\n".join([first_line] + remaining).strip()
                break

        if not action:
            yield "\nResearch Agent: no valid action returned.\n"
            break

        if action == "finish":
            action_input = action_input or "Research completed."
            if not is_news:
                save_to_memory(goal, action_input, topic="research")
                yield "\nResearch Agent saving to memory...\n"
            else:
                yield "\nNews goal — not saving to memory.\n"

            combined_obs = "\n".join(own_observations)
            is_list_answer = action_input.count("\n") > 10 if action_input else False

            if not is_list_answer and not is_news:
                try:
                    from agent import self_reflect
                    reflected_answer, was_improved = self_reflect(goal, action_input, combined_obs)
                    if was_improved:
                        yield "\n[Self-reflection: answer improved]\n"
                        action_input = reflected_answer
                except Exception:
                    pass

            yield "\n" + "=" * 40 + "\n"
            yield "RESEARCH RESULT:\n"
            yield action_input + "\n"
            yield "=" * 40 + "\n"

            if not is_list_answer and not is_news:
                try:
                    from agent import check_hallucination
                    yield "\n--- EVALUATION ---\n"
                    hallucination_result = check_hallucination(combined_obs, action_input)
                    yield f"{hallucination_result}\n"
                    yield "=" * 40 + "\n"
                except Exception:
                    pass

            return

        if is_news:
            allowed_tools = ["search", "summarise"]
        else:
            allowed_tools = ["search", "summarise", "remember", "deep_research", "save_to_file"]

        if action in allowed_tools and action in TOOLS:
            if action == "search":
                action_input = re.sub(r'\b(19|20)\d{2}\b', '', action_input).strip()
            observation = TOOLS[action](action_input)
            if observation:
                obs_str = str(observation) if not isinstance(observation, str) else observation
                own_observations.append(obs_str[:3000])
            yield f"\nOBSERVATION:\n{observation}\n"
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        else:
            messages.append({
                "role": "user",
                "content": f"Observation: Tool '{action}' is not available. Use only the allowed tools."
            })
import os
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOLS
from memory import search_memory, get_memory_count, save_to_memory

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are Arham's Autonomous Agent — a smart, focused AI assistant built by Arham Sabri. You are professional, direct, and efficient. You never waste steps. You always think before acting. You work by thinking step by step and using tools to achieve a goal.

You must always respond in this exact format:

Thought: [answer these 4 questions before acting:
1. What do I already know? (from memory, previous steps, or general knowledge)
2. What am I still missing? (what information do I need to answer the goal)
3. What is the best next action? (which tool will get me what I need)
4. Why is this action better than alternatives? (briefly justify your choice)]
Action: [write only the tool name here — either: search, summarise, remember, save_to_file, check_court_cause_list, deep_research, fill_form, evaluate_job, fill_test_login, search_internshala, apply_internshala, save_report, get_calendar, create_calendar_event, get_news, or finish]
Action Input: [write the input for the tool here]

The tools available to you are:
- search: use this for ALL goals by default. Use this for quick lookups, facts, news, and any topic where the user has not explicitly asked for deep or comprehensive research. Action Input should be a search query.
- summarise: use this to compress large amounts of text into clean bullet points. Action Input should be the actual text you want summarised — never a placeholder.
- remember: use this to save important findings to memory for future use. Action Input should be the key findings you want to remember.
- save_to_file: use this to save any important content to a file. Action Input should be the content you want saved.
- check_court_cause_list: use this to check today's Delhi High Court cause list for hearings, case listings, or judgments. Action Input can be left empty or contain a specific case name/number you're looking for.
- deep_research: use this ONLY when the goal explicitly contains one of these words: "deep", "comprehensive", "thorough", "detailed", or "in-depth". If none of these words appear in the goal — never use deep_research, use search instead. This reads the full content of top web pages. Action Input should be the research topic.
- fill_form: use this when the goal explicitly asks to fill out or submit a form with specific details. Action Input must be formatted as "name | comment" — the name first, then a pipe character, then the comment or message to submit.
- evaluate_job: use this when the goal involves checking whether a job posting is worth applying to. Action Input must be formatted as "company | job title | posting text".
- fill_test_login: use this when the goal explicitly asks to log into or test the practice login page. Action Input must be formatted as "username | password".
- search_internshala: use this to search for remote internships on Internshala on any topic. Action Input should be the topic keyword only.
- apply_internshala: use this to apply to a specific internship on Internshala. Action Input must be the full internship link.
- save_report: use this at the end of every Internshala run to save a summary of what was done. No Action Input needed.
- get_calendar: use this to get today's calendar events. No Action Input needed.
- create_calendar_event: use this to create a new calendar event. Action Input must be formatted as "title | date | time".
- get_news: use this to get latest news on any topic. Action Input should be the topic you want news about (e.g. "AI", "India tech", "cricket").
- finish: use this when you have enough information to answer the goal completely. Action Input should be your complete final answer.

Rules:
- Always think before acting — answer all 4 questions in your Thought before every action
- Only plan ONE action at a time — never write multiple Action and Action Input pairs in one response
- Always wait for the Observation before deciding the next action
- GUARDRAIL: Only use deep_research if the goal contains: "deep", "comprehensive", "thorough", "detailed", or "in-depth". For all other goals — use search only.
- If using search, do at least two searches before finishing
- Never make up information — only use what you find through search, deep_research, or memory
- Never add a year to your search queries
"""


def detect_topic(goal):
    goal_lower = goal.lower()
    if any(word in goal_lower for word in ["job", "internship", "internshala", "apply", "hiring", "work", "career"]):
        return "job_search"
    if any(word in goal_lower for word in ["gmail", "email", "mail", "inbox", "send email", "draft"]):
        return "gmail"
    if any(word in goal_lower for word in ["research", "find out", "deep research", "investigate", "study", "analyse", "analyze"]):
        return "research"
    return "general"


def rewrite_query(goal):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a search query optimizer. Rewrite the goal into a short clean search query of 3 to 6 words. Return only the rewritten query. Never include a year."
                },
                {
                    "role": "user",
                    "content": f"Rewrite this into a clean search query: {goal}"
                }
            ],
            max_tokens=30
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return goal


def check_hallucination(observations, final_answer):
    try:
        if not observations:
            return "UNKNOWN — no observations to check against"
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI answer evaluator.
HALLUCINATION RISK: LOW/MEDIUM/HIGH
FAITHFULNESS SCORE: 0-100%
REASON: one sentence
Respond in exactly this format."""
                },
                {
                    "role": "user",
                    "content": f"OBSERVATIONS:\n{observations[:3000]}\n\nFINAL ANSWER:\n{final_answer}"
                }
            ],
            max_tokens=120
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Evaluation failed: {str(e)}"


def self_reflect(goal, answer, observations):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a self-reflection engine.
If answer is complete: respond with exactly: REFLECTION: No improvements needed.
If needs improvement: respond with: REFLECTION: [improved answer]"""
                },
                {
                    "role": "user",
                    "content": f"GOAL:\n{goal}\n\nOBSERVATIONS:\n{observations[:2000]}\n\nANSWER:\n{answer}"
                }
            ],
            max_tokens=500
        )
        result = response.choices[0].message.content.strip()
        if "No improvements needed" in result:
            return answer, False
        improved = result.replace("REFLECTION:", "").strip()
        return improved, True
    except Exception:
        return answer, False


def calculate_cost(total_input_tokens, total_output_tokens):
    input_cost_usd = (total_input_tokens / 1_000_000) * 2.50
    output_cost_usd = (total_output_tokens / 1_000_000) * 10.00
    total_cost_usd = input_cost_usd + output_cost_usd
    total_cost_inr = total_cost_usd * 96.38
    return total_cost_usd, total_cost_inr


def run_agent(goal, user_id=None):
    from agents.coordinator import run_coordinator
    for update in run_coordinator(goal, user_id=user_id):
        yield update


if __name__ == "__main__":
    goal = input("Enter your goal: ")
    for update in run_agent(goal):
        if isinstance(update, str):
            print(update, end="")
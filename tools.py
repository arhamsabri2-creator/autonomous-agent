from internshala_search import search_internshala_jobs
from internshala_apply import apply_to_internship
import os
import re
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI
from memory import save_to_memory, search_memory
from court_tool import check_court_cause_list
from research_tool import deep_research
from form_tool import fill_government_form
from job_evaluator import evaluate_job
from form_tool_2 import fill_test_login

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def search(query):
    try:
        response = tavily_client.search(query=query, max_results=5, days=365)
        results = response.get("results", [])

        if not results:
            return "No results found for this search query."

        output = ""
        for i, result in enumerate(results, start=1):
            title = result.get("title", "No title")
            content = result.get("content", "No content")
            output += f"Result {i}:\nTitle: {title}\nContent: {content}\n\n"

        return output.strip()

    except Exception as e:
        return f"Search failed with error: {str(e)}"


def summarise(text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a summarisation assistant. Take the text given to you and compress it into clear, concise bullet points. Keep only the most important facts and insights. Remove all fluff."
                },
                {
                    "role": "user",
                    "content": f"Summarise this text into bullet points:\n\n{text}"
                }
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Summarise failed with error: {str(e)}"


def remember(content):
    try:
        result = save_to_memory(content, content)
        return f"Saved to memory: {result}"

    except Exception as e:
        return f"Remember failed with error: {str(e)}"


def save_to_file(content):
    try:
        filename = "output.txt"
        with open(filename, "w") as f:
            f.write(content)
        return f"Answer saved to {filename}"

    except Exception as e:
        return f"Save failed with error: {str(e)}"


def finish(answer):
    save_to_file(answer)
    return answer



def search_internshala(action_input):
    topic = action_input.strip().strip('"').strip("'") if action_input and action_input != 'None' else 'artificial-intelligence'
    return search_internshala_jobs(topic)

def apply_internshala(link):
    link = link.strip().strip('"').strip("'")
    return apply_to_internship(link)

TOOLS = {
    "search": search,
    "summarise": summarise,
    "remember": remember,
    "save_to_file": save_to_file,
    "check_court_cause_list": check_court_cause_list,
    "deep_research": deep_research,
    "fill_form": fill_government_form,
    "evaluate_job": evaluate_job,
    "fill_test_login": fill_test_login,
    "finish": finish,
    "search_internshala": search_internshala,
    "apply_internshala": apply_internshala,
}
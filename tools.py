import os
import re
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI

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
    # This tool takes a large block of text and compresses it
    # Think of it as a junior assistant who reads everything
    # and hands back only the most important points
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


def save_to_file(content):
    # This tool saves the agent's final answer to a text file
    # Think of it as the filing cabinet in Raza's office
    # Every closed case gets a written record automatically
    try:
        filename = "output.txt"
        with open(filename, "w") as f:
            f.write(content)
        return f"Answer saved to {filename}"

    except Exception as e:
        return f"Save failed with error: {str(e)}"


def finish(answer):
    # Signal that the task is complete
    # Also automatically saves the answer to a file
    save_to_file(answer)
    return answer


TOOLS = {
    "search": search,
    "summarise": summarise,
    "save_to_file": save_to_file,
    "finish": finish,
}
import os
import chromadb
from dotenv import load_dotenv
from chromadb.utils import embedding_functions

# Load environment variables first before anything else
# This ensures OPENAI_API_KEY is available when creating the embedding function
load_dotenv()

client = chromadb.PersistentClient(path="./memory_store")

embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

collection = client.get_or_create_collection(
    name="agent_memory",
    embedding_function=embedding_function
)


def save_to_memory(goal, result):
    # Saves a research run to memory
    # Think of it as Meera filing a new case in the warehouse
    try:
        memory_id = goal[:50].replace(" ", "_").replace("?", "").replace(",", "")
        document = f"Goal: {goal}\n\nFindings: {result}"

        collection.upsert(
            ids=[memory_id],
            documents=[document],
            metadatas=[{"goal": goal}]
        )

        return f"Memory saved successfully for goal: {goal[:50]}"

    except Exception as e:
        return f"Memory save failed: {str(e)}"


def search_memory(query, n_results=3):
    # Searches memory for relevant past research
    # Think of it as asking Meera — have you seen anything like this before?
    try:
        if collection.count() == 0:
            return None

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count())
        )

        if not results["documents"][0]:
            return None

        output = "RELEVANT MEMORIES FROM PAST RESEARCH:\n\n"
        for i, doc in enumerate(results["documents"][0], start=1):
            output += f"Memory {i}:\n{doc}\n\n"

        return output.strip()

    except Exception as e:
        return None


def get_memory_count():
    # Returns how many memories are stored
    try:
        return collection.count()
    except:
        return 0
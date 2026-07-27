import os
import uuid
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("agent-memory")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embedding(text):
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def save_to_memory(goal, result):
    try:
        memory_id = str(uuid.uuid4())
        document = f"Goal: {goal}\n\nFindings: {result}"
        embedding = get_embedding(document)

        index.upsert(vectors=[{
            "id": memory_id,
            "values": embedding,
            "metadata": {"goal": goal, "text": document}
        }])

        return f"Memory saved successfully for goal: {goal[:50]}"
    except Exception as e:
        return f"Memory save failed: {str(e)}"


def search_memory(query, n_results=3):
    try:
        stats = index.describe_index_stats()
        if stats["total_vector_count"] == 0:
            return None

        query_embedding = get_embedding(query)

        results = index.query(
            vector=query_embedding,
            top_k=min(n_results, stats["total_vector_count"]),
            include_metadata=True
        )

        if not results["matches"]:
            return None

        output = "RELEVANT MEMORIES FROM PAST RESEARCH:\n\n"
        for i, match in enumerate(results["matches"], start=1):
            output += f"Memory {i}:\n{match['metadata']['text']}\n\n"

        return output.strip()
    except Exception:
        return None


def get_memory_count():
    try:
        stats = index.describe_index_stats()
        return stats["total_vector_count"]
    except Exception:
        return 0

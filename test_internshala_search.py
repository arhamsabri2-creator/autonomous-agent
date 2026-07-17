from internshala_search import search_internshala_jobs

results = search_internshala_jobs()

if isinstance(results, str):
    print("Error:", results)
else:
    print("Found", len(results), "internships:\n")
    for i, job in enumerate(results):
        print(f"--- {i+1} ---")
        print("Title:", job["title"])
        print("Company:", job["company"])
        print("Stipend:", job["stipend"])
        print("Link:", job["link"])
        print()

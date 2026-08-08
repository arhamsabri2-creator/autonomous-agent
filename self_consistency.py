import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def run_with_self_consistency(goal, runs=3):
    from agents.research_agent import run_research_agent
    answers = []
    for i in range(runs):
        output = ''
        for update in run_research_agent(goal):
            if isinstance(update, str):
                output += update
        answers.append(output.strip())
    if len(set(answers)) == 1:
        return answers[0]
    comparison_prompt = f'''You ran the same task {runs} times and got these answers:

{chr(10).join([f'Answer {i+1}: {a[-500:]}' for i, a in enumerate(answers)])}

Pick the most accurate and consistent answer. Return only the best answer, no explanation.'''
    response = client.chat.completions.create(
        model='gpt-4o',
        messages=[{'role': 'user', 'content': comparison_prompt}],
        max_tokens=500
    )
    return response.choices[0].message.content

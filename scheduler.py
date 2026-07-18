import schedule
import time
import subprocess
from datetime import datetime

def run_agent():
    print("Starting scheduled run at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    goal = "find AI remote internships on internshala and apply to 3 of them then save a report"
    process = subprocess.Popen(["python3", "agent.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate(input=goal)
    print(stdout)
    print("Run complete at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

schedule.every().day.at("09:00").do(run_agent)
print("Scheduler running - agent will run daily at 9AM")
print("Keep this terminal open. Ctrl+C to stop.")
while True:
    schedule.run_pending()
    time.sleep(60)

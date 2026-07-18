import os
import csv
from datetime import datetime
from gmail_tool import send_email

def save_daily_report(applications=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.now().strftime("%Y-%m-%d")
    
    todays_applications = []
    try:
        with open("applied_jobs.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                todays_applications.append(row)
    except Exception:
        pass

    lines = []
    lines.append("=" * 50)
    lines.append("DAILY JOB APPLICATION REPORT")
    lines.append("Date: " + timestamp)
    lines.append("=" * 50)

    if not todays_applications:
        lines.append("No applications made in this run.")
    else:
        lines.append("Total applications so far: " + str(len(todays_applications)))
        lines.append("")
        for i, app in enumerate(todays_applications):
            lines.append(str(i+1) + ". " + app.get("title", "N/A") + " at " + app.get("company", "N/A"))
        lines.append("")

    lines.append("=" * 50)
    report = "\n".join(lines)

    with open("daily_report.txt", "a") as f:
        f.write(report + "\n\n")

    try:
        send_email(
            to="arhamsabri2@gmail.com",
            subject="Daily Job Report - " + today,
            body=report
        )
        email_status = "Email sent successfully"
    except Exception as e:
        email_status = "Email failed: " + str(e)

    return "Report saved to daily_report.txt — " + str(len(todays_applications)) + " total applications logged. " + email_status
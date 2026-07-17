import csv
import os

TRACKER_FILE = "applied_jobs.csv"


def has_applied(company, title):
    if not os.path.exists(TRACKER_FILE):
        return False

    with open(TRACKER_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["company"].strip().lower() == company.strip().lower() and \
               row["title"].strip().lower() == title.strip().lower():
                return True

    return False


def log_application(company, title):
    file_exists = os.path.exists(TRACKER_FILE)

    with open(TRACKER_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["company", "title"])
        writer.writerow([company, title])

    return f"Logged application: {company} - {title}"
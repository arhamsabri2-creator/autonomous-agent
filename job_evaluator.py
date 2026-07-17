from job_matcher import is_match
from job_tracker import has_applied, log_application


def evaluate_job(details):
    parts = details.split("|")
    if len(parts) < 3:
        return "Error: input must be 'company | title | posting_text'"

    company = parts[0].strip()
    title = parts[1].strip()
    posting_text = parts[2].strip()

    if not is_match(posting_text):
        return f"SKIP - not a skills match: {company} - {title}"

    if has_applied(company, title):
        return f"SKIP - already applied: {company} - {title}"

    log_application(company, title)
    return f"PROCEED - matched and logged, ready to apply: {company} - {title}"
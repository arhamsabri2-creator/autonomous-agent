MY_SKILLS = [
    "Python",
    "Flask",
    "Web Scraping",
    "AI",
    "Machine Learning",
    "Automation",
]


def is_match(posting_text, skills=None):
    if skills is None:
        skills = MY_SKILLS

    posting_lower = posting_text.lower()

    for skill in skills:
        if skill.lower() in posting_lower:
            return True

    return False
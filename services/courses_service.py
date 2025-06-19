import json
import os

COURSES_FILE = "data/courses.json"

def load_courses():
    if not os.path.exists(COURSES_FILE):
        return []
    with open(COURSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_courses(courses):
    with open(COURSES_FILE, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

def add_course(name, description):
    courses = load_courses()
    courses.append({
        "name": name,
        "description": description,
        "active": True
    })
    save_courses(courses)

def get_courses():
    return load_courses()

import csv
import json
import os
from datetime import date
from typing import Literal

import instructor
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

client = instructor.from_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))

TODAY = date.today()
PEOPLE_CSV = os.path.join(os.path.dirname(__file__), "people.csv")

Tag = Literal[
    "IT",
    "transport",
    "edukacja",
    "medycyna",
    "praca z ludźmi",
    "praca z pojazdami",
    "praca fizyczna",
]

class TaggedPerson(BaseModel):
    name: str
    surname: str
    tags: list[Tag]


class TaggedPeople(BaseModel):
    people: list[TaggedPerson]


def load_people(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def age(birth_date_str: str) -> int:
    bd = date.fromisoformat(birth_date_str)
    return TODAY.year - bd.year - ((TODAY.month, TODAY.day) < (bd.month, bd.day))


def filter_people(people: list[dict]) -> list[dict]:
    return [
        p for p in people
        if p["gender"] == "M"
        and 20 <= age(p["birthDate"]) <= 40
        and p["birthPlace"] == "Grudziądz"
    ]


def tag_people(people: list[dict]) -> list[TaggedPerson]:
    people_payload = [
        {"name": p["name"], "surname": p["surname"], "job": p["job"]}
        for p in people
    ]

    result = client.chat.completions.create(
        model="gpt-4o-mini",
        response_model=TaggedPeople,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a job classifier. For each person assign one or more tags "
                    "based on their job description. Only use tags defined in the schema."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(people_payload, ensure_ascii=False),
            },
        ],
    )

    return result.people


def main():
    print("[1/4] Loading and filtering people...")
    people = load_people(PEOPLE_CSV)
    results = filter_people(people)
    print(f"      → {len(results)} people matched (M, age 20-40, Grudziądz)")

    print("[2/4] Tagging with OpenAI...")
    tagged = tag_people(results)

    print("[3/4] Filtering by 'transport' tag...")
    filtered = [p for p in tagged if "transport" in p.tags]
    print(f"      → {len(filtered)} people with transport tag")

    original = {(p["name"], p["surname"]): p for p in results}

    output = [
        {
            "name": p.name,
            "surname": p.surname,
            "gender": original[(p.name, p.surname)]["gender"],
            "born": original[(p.name, p.surname)]["birthDate"][:4],
            "city": original[(p.name, p.surname)]["birthPlace"],
            "tags": p.tags,
        }
        for p in filtered
    ]

    print("[4/4] Posting to hub...")
    payload = {
        "apikey": os.getenv("AGENT_API_KEY"),
        "task": "people",
        "answer": output,
    }

    response = requests.post(os.getenv("HUB_URL"), json=payload)
    print(f"      → {response.status_code}: {response.json()}")


if __name__ == "__main__":
    main()

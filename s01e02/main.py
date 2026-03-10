import json
import math
import os

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

HUB_URL = os.getenv("HUB_URL")
API_KEY = os.getenv("AGENT_API_KEY")

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


COORDS_CACHE = os.path.join(os.path.dirname(__file__), "coords.json")


def get_city_coordinates(cities: list[str]) -> dict[str, dict]:
    if os.path.exists(COORDS_CACHE):
        print("      → loading coords from cache (coords.json)")
        with open(COORDS_CACHE, encoding="utf-8") as f:
            return json.load(f)

    prompt = (
        "Return a JSON object mapping each city name to its latitude and longitude. "
        "Use this exact format: {\"CityName\": {\"lat\": 0.0, \"lng\": 0.0}, ...}. "
        "Only return the JSON object, no explanation.\n\n"
        f"Cities: {', '.join(cities)}"
    )
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    coords = json.loads(response.choices[0].message.content)

    with open(COORDS_CACHE, "w", encoding="utf-8") as f:
        json.dump(coords, f, ensure_ascii=False, indent=2)
    print(f"      → coords saved to {COORDS_CACHE}")

    return coords


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_power_plant(lat: float, lng: float, plants: list[dict]) -> dict:
    closest = min(plants, key=lambda p: haversine_km(lat, lng, p["lat"], p["lng"]))
    distance = haversine_km(lat, lng, closest["lat"], closest["lng"])
    return {"code": closest["code"], "city": closest["city"], "distance_km": round(distance, 2)}


def main():
    # Step 1: fetch locations
    print("[1/4] Fetching power plant locations...")
    loc_response = requests.get(f"{HUB_URL}/data/{API_KEY}/findhim_locations.json")
    loc_response.raise_for_status()
    locations_data = loc_response.json()
    power_plants_raw = locations_data["power_plants"]

    city_names = list(power_plants_raw.keys())
    print(f"      → {len(city_names)} cities: {city_names}")

    # Step 2: get lat/lng for each city via OpenAI
    print("[2/4] Resolving city coordinates via OpenAI...")
    city_coords = get_city_coordinates(city_names)

    power_plants = [
        {
            "city": city,
            "lat": city_coords[city]["lat"],
            "lng": city_coords[city]["lng"],
            "code": power_plants_raw[city]["code"],
            "is_active": power_plants_raw[city]["is_active"],
        }
        for city in city_names
        if city in city_coords
    ]
    print(f"      → resolved {len(power_plants)} plants")

    # Step 3: load people and fetch their locations (result of s01e01)
    print("[3/4] Loading people and fetching their locations...")
    people_path = os.path.join(os.path.dirname(__file__), "people.json")
    with open(people_path, encoding="utf-8") as f:
        people = json.load(f)
    print(f"      → {len(people)} people loaded")

    results = []
    for person in people:
        loc_resp = requests.post(
            f"{HUB_URL}/api/location",
            json={"apikey": API_KEY, "name": person["name"], "surname": person["surname"]},
        )
        loc_resp.raise_for_status()
        coords_list = loc_resp.json()

        for coord in coords_list:
            plant = nearest_power_plant(coord["latitude"], coord["longitude"], power_plants)
            results.append({
                "name": person["name"],
                "surname": person["surname"],
                "latitude": coord["latitude"],
                "longitude": coord["longitude"],
                "power_plant": plant,
            })

    # Step 4: find top 5 people closest to any power plant
    print("[4/6] Finding top 5 people closest to a power plant...")
    top5 = sorted(results, key=lambda r: r["power_plant"]["distance_km"])[:5]
    for i, candidate in enumerate(top5):
        print(f"      → #{i+1} {candidate['name']} {candidate['surname']} @ {candidate['power_plant']['distance_km']} km from {candidate['power_plant']['code']}")

    # Step 5 & 6: for each candidate, fetch access level and attempt submission
    for i, candidate in enumerate(top5):
        print(f"\n[5/6] Fetching access level for candidate #{i+1}: {candidate['name']} {candidate['surname']}...")
        person_data = next(p for p in people if p["name"] == candidate["name"] and p["surname"] == candidate["surname"])
        access_resp = requests.post(
            f"{HUB_URL}/api/accesslevel",
            json={
                "apikey": API_KEY,
                "name": candidate["name"],
                "surname": candidate["surname"],
                "birthYear": int(person_data["birthYear"]),
            },
        )
        access_resp.raise_for_status()
        access_data = access_resp.json()
        print(f"      → accessLevel: {access_data['accessLevel']}")

        print(f"[6/6] Submitting candidate #{i+1} to hub...")
        payload = {
            "apikey": API_KEY,
            "task": "findhim",
            "answer": {
                "name": candidate["name"],
                "surname": candidate["surname"],
                "accessLevel": access_data["accessLevel"],
                "powerPlant": candidate["power_plant"]["code"],
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        verify_resp = requests.post(f"{HUB_URL}/verify", json=payload)
        print(f"      → {verify_resp.status_code}: {verify_resp.json()}")
        if verify_resp.status_code == 200:
            print("      → Accepted! Stopping.")
            break
        print(f"      → Not accepted, trying next candidate...")


if __name__ == "__main__":
    main()

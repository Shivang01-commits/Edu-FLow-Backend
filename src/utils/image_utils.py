import requests
import random

PEXELS_API_KEY = "YOUR_API_KEY"


def get_image_url(query: str) -> str:
    url = "https://api.pexels.com/v1/search"

    headers = {"Authorization": PEXELS_API_KEY}

    params = {
        "query": query,
        "per_page": 5,  # get multiple options
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        photos = data.get("photos", [])
        if not photos:
            return None

        # pick random image for variety
        image = random.choice(photos)

        return image["src"]["large"]

    except Exception as e:
        print("PEXELS ERROR:", e)
        return None

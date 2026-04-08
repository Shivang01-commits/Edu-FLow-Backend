import os
import httpx
import random
import asyncio
from src.utils.image_utils import get_image_url

PRESENTON_BASE_URL = "https://api.presenton.ai"
PRESENTON_API_KEY = os.getenv("PRESENTON_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {PRESENTON_API_KEY}",
    "Content-Type": "application/json",
}

SUBJECT_KEYWORDS = {
    "physics": [
        "physics classroom experiment",
        "motion graph velocity time diagram",
        "pendulum experiment setup",
        "newton laws illustration",
        "force and motion diagram",
        "wave motion diagram physics",
        "electric circuit basic diagram",
        "magnetism field lines illustration",
    ],
    "chemistry": [
        "chemical reaction experiment lab",
        "molecular structure 3d model",
        "periodic table classroom chart",
        "acid base reaction diagram",
        "laboratory glassware setup",
        "chemical bonding diagram",
        "organic chemistry structure diagram",
        "solution mixing experiment",
    ],
    "biology": [
        "cell structure labeled diagram",
        "human body organ system illustration",
        "plant cell chloroplast diagram",
        "photosynthesis process diagram",
        "ecosystem food chain diagram",
        "microscope biology lab",
        "dna double helix model",
        "respiratory system diagram human",
    ],
    "geography": [
        "earth layers cross section diagram",
        "mountain formation diagram tectonic",
        "river system map illustration",
        "climate zones world map",
        "landforms labeled diagram",
        "globe classroom geography",
        "natural resources map illustration",
        "water cycle diagram labeled",
    ],
    "math": [
        "geometry shapes labeled diagram",
        "algebra equations on board classroom",
        "coordinate graph x y axis plot",
        "trigonometry unit circle diagram",
        "calculus graph curve illustration",
        "math teacher explaining equation",
        "statistics bar graph chart",
        "angles triangle geometry diagram",
    ],
    "default": [
        "students classroom learning",
        "teacher explaining concept board",
        "education concept illustration",
        "school classroom environment",
        "learning process illustration",
        "books and study desk",
        "online education concept",
        "academic presentation background",
    ],
}


def get_smart_keyword(subject, title, description):
    base_keywords = SUBJECT_KEYWORDS.get(subject, SUBJECT_KEYWORDS["default"])
    text = (title + " " + description).lower()

    for kw in base_keywords:
        if any(word in kw for word in text.split()):
            return kw

    return random.choice(base_keywords)


def detect_subject(text: str):
    text = text.lower()

    if any(word in text for word in ["motion", "speed", "pendulum", "time"]):
        return "physics"
    if any(word in text for word in ["landform", "mountain", "earth"]):
        return "geography"
    if any(word in text for word in ["cell", "plant", "animal"]):
        return "biology"
    if any(word in text for word in ["equation", "math", "geometry"]):
        return "math"

    return "default"


IMAGE_CACHE = {}


async def build_image(title: str, description: str):
    subject = detect_subject(title + " " + description)
    keyword = get_smart_keyword(subject, title, description)

    if keyword in IMAGE_CACHE:
        image_url = IMAGE_CACHE[keyword]
    else:
        # ✅ run blocking function in thread
        image_url = await asyncio.to_thread(get_image_url, keyword)
        if image_url:
            IMAGE_CACHE[keyword] = image_url

    if not image_url:
        image_url = "https://via.placeholder.com/1600x900?text=Education"

    prompt = f"{title}, {keyword}"[:50]

    if len(prompt) < 10:
        prompt += " education"

    return {
        "__image_url__": image_url,
        "__image_prompt__": prompt,
    }


async def transform_ppt_structure(
    ppt_structure: dict,
    template: str = "general",
    theme: str = "professional-dark",
    language: str = "en",
    export_as: str = "pptx",
):
    slides = []

    for slide in ppt_structure["ppt"]["slides"]:
        slide_type = slide.get("slide_type", "content")

        title = slide.get("title", "Untitled")[:40]

        if slide_type == "title":
            description = slide.get("subtitle", "Introduction")
        else:
            bullets = slide.get("bullet_points", [])
            description = " ".join(bullets)

        description = description.strip()[:140]

        if len(description) < 10:
            description = "Key concepts explained clearly."

        image = await build_image(title, description)

        slides.append(
            {
                "layout": "general:general-intro-slide"
                if slide_type == "title"
                else "general:basic-info-slide",
                "content": {
                    **(
                        {
                            "title": title,
                            "description": description,
                            "presenterName": "Teacher",
                            "presentationDate": "2026",
                            "image": image,
                        }
                        if slide_type == "title"
                        else {
                            "title": title,
                            "description": description,
                            "image": image,
                        }
                    )
                },
            }
        )

    return {
        "title": ppt_structure.get("heading", "Presentation"),
        "template": template,
        "theme": theme,
        "language": language,
        "export_as": export_as,
        "slides": slides,
    }


async def create_presentation_from_json(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{PRESENTON_BASE_URL}/api/v1/ppt/presentation/create/from-json",
            json=payload,
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.json()


# ⚠️ KEEP THIS ONLY IF REALLY NEEDED
async def download_pptx_bytes(download_url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(download_url)
        response.raise_for_status()
        return response.content


async def get_template_layouts(template_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{PRESENTON_BASE_URL}/api/v1/ppt/template/{template_id}",
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.json()

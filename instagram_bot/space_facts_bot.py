"""
Instagram Space Facts Bot
Posts a daily space fact image to Instagram using the Graph API.

Setup:
  1. Create a Facebook Developer app with Instagram Graph API access.
  2. Connect an Instagram Business/Creator account to a Facebook Page.
  3. Generate a long-lived Page Access Token.
  4. Set environment variables (see .env.example).

Usage:
  python space_facts_bot.py
"""

import os
import sys
import math
import random
import hashlib
import textwrap
import datetime
import requests
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

# ---------------------------------------------------------------------------
# Space facts (one chosen deterministically per calendar day)
# ---------------------------------------------------------------------------

SPACE_FACTS = [
    "The Sun contains 99.86% of all the mass in our Solar System.",
    "A day on Venus is longer than a year on Venus.",
    "Neutron stars can spin at up to 716 rotations per second.",
    "The Milky Way galaxy is about 105,700 light-years wide.",
    "There are more stars in the universe than grains of sand on all of Earth's beaches.",
    "The footprints left on the Moon by Apollo astronauts will last for millions of years — there's no wind to erase them.",
    "Saturn's rings are made mostly of ice and rock and are only about 30 feet thick on average.",
    "One million Earths could fit inside the Sun.",
    "The largest known star, UY Scuti, is about 1,700 times the radius of our Sun.",
    "Light from the Sun takes about 8 minutes and 20 seconds to reach Earth.",
    "Jupiter's Great Red Spot is a storm that has been raging for over 350 years.",
    "The temperature at the Sun's core is about 27 million degrees Fahrenheit (15 million °C).",
    "Olympus Mons on Mars is the tallest volcano in the Solar System — nearly 3 times the height of Everest.",
    "A black hole with the mass of the Sun would be only about 6 km (3.7 miles) in diameter.",
    "The Andromeda Galaxy is on a collision course with the Milky Way — expected in about 4.5 billion years.",
    "Water has been found on the Moon in the form of ice in permanently shadowed craters.",
    "There are about 2 trillion galaxies in the observable universe.",
    "The coldest known place in the universe is the Boomerang Nebula, at just 1 Kelvin (-272 °C).",
    "Voyager 1 is the most distant human-made object, more than 23 billion km from the Sun.",
    "Europa, a moon of Jupiter, likely has a liquid water ocean beneath its icy crust.",
    "A teaspoon of neutron star material would weigh about 10 million tons.",
    "The Hubble Space Telescope travels at about 28,000 km/h (17,500 mph).",
    "Sound cannot travel in space — there's no medium for the waves to move through.",
    "Pluto is smaller than the United States in diameter.",
    "The universe is estimated to be about 13.8 billion years old.",
    "Mars has the largest dust storms in the Solar System, covering the entire planet.",
    "The Crab Nebula is the remnant of a supernova explosion observed by Chinese astronomers in 1054 AD.",
    "There are more possible iterations of a game of chess than there are atoms in the observable universe.",
    "Uranus rotates on its side — its axial tilt is 98 degrees.",
    "The ISS travels at about 28,000 km/h, completing 16 orbits of Earth per day.",
    "In 5 billion years, the Sun will become a red giant and likely engulf Earth.",
    "The observable universe is about 93 billion light-years in diameter.",
    "Dark energy makes up about 68% of the universe.",
    "If you fell into a black hole, you would experience 'spaghettification'.",
    "Titan, Saturn's largest moon, has lakes and seas of liquid methane and ethane.",
    "The first human in space was Yuri Gagarin on April 12, 1961.",
    "The James Webb Space Telescope can see galaxies formed just 300 million years after the Big Bang.",
    "Pulsars are so precise they rival atomic clocks in timekeeping accuracy.",
    "Earth's moon is slowly drifting away — about 3.8 cm per year.",
    "The phrase 'dark matter' was coined in 1933 by astronomer Fritz Zwicky.",
    "A year on Mercury lasts only 88 Earth days.",
    "The surface of the Sun has a temperature of about 5,500 °C (9,932 °F).",
    "Space begins at the Kármán line, 100 km (62 miles) above Earth's surface.",
    "Exoplanet WASP-12b is being consumed by its host star and will be gone in ~3 million years.",
    "The Voyager probes carry a golden record with sounds and images from Earth.",
    "Stars twinkle because of atmospheric turbulence; planets generally don't twinkle.",
    "The asteroid belt lies between Mars and Jupiter and contains millions of objects.",
    "Io, a moon of Jupiter, is the most volcanically active body in the Solar System.",
    "The Big Bang was not an explosion in space — it was an expansion of space itself.",
    "If the Sun were the size of a white blood cell, the Milky Way would be the size of the continental US.",
]


def pick_fact_for_today() -> str:
    """Select a fact deterministically based on today's date."""
    today = datetime.date.today()
    index = int(hashlib.sha256(str(today).encode()).hexdigest(), 16) % len(SPACE_FACTS)
    return SPACE_FACTS[index]


# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1080, 1080
BG_COLOR = (10, 10, 30)          # deep space dark blue
STAR_COLOR = (255, 255, 255)
ACCENT_COLOR = (100, 180, 255)   # light blue
TEXT_COLOR = (230, 230, 255)
TITLE_COLOR = (255, 210, 80)     # warm yellow


def _draw_stars(draw: ImageDraw.ImageDraw, count: int = 200, seed: int = 0) -> None:
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(0, WIDTH - 1)
        y = rng.randint(0, HEIGHT - 1)
        r = rng.choice([0, 0, 0, 1, 1, 2])
        brightness = rng.randint(150, 255)
        color = (brightness, brightness, brightness)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def _draw_planet(draw: ImageDraw.ImageDraw) -> None:
    """Draw a simple decorative planet in the corner."""
    cx, cy, radius = WIDTH - 160, 160, 80
    # Planet body
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 fill=(60, 40, 100), outline=(100, 80, 160), width=3)
    # Ring
    ring_rx, ring_ry = radius + 40, 18
    draw.ellipse([cx - ring_rx, cy - ring_ry, cx + ring_rx, cy + ring_ry],
                 outline=ACCENT_COLOR, width=3)
    # Erase the part of the ring behind the planet
    draw.ellipse([cx - radius + 3, cy - radius + 3, cx + radius - 3, cy + radius - 3],
                 fill=(60, 40, 100))


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def create_fact_image(fact: str, output_path: str = "space_fact.jpg") -> str:
    """Render a 1080x1080 space-themed image with the given fact."""
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    today_ordinal = datetime.date.today().toordinal()
    _draw_stars(draw, count=300, seed=today_ordinal)
    _draw_planet(draw)

    # Horizontal accent line at top
    draw.rectangle([0, 0, WIDTH, 6], fill=ACCENT_COLOR)

    # Title
    title_font = _get_font(52)
    title = "Space Fact of the Day"
    draw.text((60, 80), title, font=title_font, fill=TITLE_COLOR)

    # Date
    date_font = _get_font(28)
    date_str = datetime.date.today().strftime("%B %d, %Y")
    draw.text((60, 155), date_str, font=date_font, fill=ACCENT_COLOR)

    # Divider
    draw.rectangle([60, 205, WIDTH - 60, 209], fill=ACCENT_COLOR)

    # Fact text
    fact_font = _get_font(40)
    wrapped = textwrap.fill(fact, width=32)
    draw.text((60, 260), wrapped, font=fact_font, fill=TEXT_COLOR,
              spacing=14)

    # Footer
    footer_font = _get_font(26)
    footer = "#SpaceFact #Astronomy #Science #Space #Universe"
    draw.text((60, HEIGHT - 80), footer, font=footer_font, fill=(120, 140, 180))

    # Bottom accent line
    draw.rectangle([0, HEIGHT - 6, WIDTH, HEIGHT], fill=ACCENT_COLOR)

    img.save(output_path, "JPEG", quality=95)
    print(f"Image saved: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Instagram Graph API helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


def upload_to_instagram(image_path: str, caption: str) -> None:
    """
    Post an image to Instagram via the Graph API.

    Requires:
      IG_USER_ID      — Instagram Business/Creator account User ID
      IG_ACCESS_TOKEN — Long-lived Page Access Token with instagram_basic,
                        instagram_content_publish, and pages_read_engagement scopes
    """
    user_id = _require_env("IG_USER_ID")
    access_token = _require_env("IG_ACCESS_TOKEN")
    # Optional: publicly reachable URL of the image (needed if not using
    # the local file upload path below). Set IMAGE_PUBLIC_URL if your
    # deployment pipeline uploads the image to a CDN first.
    image_url = os.environ.get("IMAGE_PUBLIC_URL")

    base_url = f"https://graph.facebook.com/v19.0/{user_id}"

    if image_url:
        # --- Path 1: URL-based upload (recommended for CI/CD) ---
        print("Creating media container from URL...")
        resp = requests.post(
            f"{base_url}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token,
            },
            timeout=30,
        )
    else:
        # --- Path 2: Local file upload ---
        print("Uploading local image file...")
        with open(image_path, "rb") as fh:
            resp = requests.post(
                f"{base_url}/media",
                files={"source": fh},
                data={
                    "caption": caption,
                    "access_token": access_token,
                },
                timeout=60,
            )

    resp.raise_for_status()
    container_id = resp.json().get("id")
    if not container_id:
        sys.exit(f"Unexpected response from /media endpoint: {resp.text}")
    print(f"Media container created: {container_id}")

    # Publish the container
    print("Publishing post...")
    pub_resp = requests.post(
        f"{base_url}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    pub_resp.raise_for_status()
    post_id = pub_resp.json().get("id")
    print(f"Post published successfully! Post ID: {post_id}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_caption(fact: str) -> str:
    lines = [
        "Did you know?",
        "",
        fact,
        "",
        "Follow for a new space fact every day!",
        "",
        "#SpaceFact #Astronomy #Science #Space #Universe #NASA #Cosmos "
        "#AstroPhoto #StarGazing #Physics",
    ]
    return "\n".join(lines)


def main() -> None:
    fact = pick_fact_for_today()
    print(f"Today's fact: {fact}")

    image_path = "/tmp/space_fact.jpg"
    create_fact_image(fact, output_path=image_path)

    # Skip posting if running in dry-run mode (useful for testing image output)
    if os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes"):
        print("DRY_RUN enabled — skipping Instagram upload.")
        return

    caption = build_caption(fact)
    upload_to_instagram(image_path, caption)


if __name__ == "__main__":
    main()

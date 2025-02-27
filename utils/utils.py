import os
import requests
import time
from dotenv import load_dotenv
from decimal import Decimal
from typing import Dict, List
import logging

load_dotenv()

API_KEY = os.getenv("YELP_API_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
SEARCH_URL = "https://api.yelp.com/v3/businesses/search"


def get_restaurants(cuisine: str, location: str, limit: int = 240) -> List[Dict]:
    restaurants = []
    total = 0
    offset = 0

    while len(restaurants) < limit:
        try:
            params = {
                "term": f"{cuisine} restaurants",
                "location": location,
                "limit": min(50, limit - len(restaurants)),  # Yelp max is 50
                "offset": offset,
            }

            response = requests.get(SEARCH_URL, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()

            if "businesses" not in data:
                logging.error(f"No businesses found: {data}")
                break

            businesses = data["businesses"]
            if not businesses:
                break

            for business in businesses:
                if business["id"] not in {r["business_id"] for r in restaurants}:
                    restaurant = {
                        "business_id": business["id"],
                        "name": business["name"],
                        "address": " ".join(business["location"]["display_address"]),
                        "coordinates": {
                            "latitude": Decimal(
                                str(business["coordinates"]["latitude"])
                            ),
                            "longitude": Decimal(
                                str(business["coordinates"]["longitude"])
                            ),
                        },
                        "num_reviews": business["review_count"],
                        "rating": Decimal(str(business["rating"])),
                        "zip_code": business["location"].get("zip_code", "N/A"),
                        "inserted_at_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "cuisine": cuisine,
                    }
                    restaurants.append(restaurant)

            offset += len(businesses)
            time.sleep(0.25)  # Rate limiting protection

        except Exception as e:
            logging.error(f"Error fetching restaurants: {e}")
            break

    return restaurants

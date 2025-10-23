from langchain.tools import tool
import random

@tool
def search_city_with_better_weather(base_city: str) -> str:
    """Search for another city with better weather than the given base_city."""
    # Simulate API or data lookup
    options = ["Lisbon"]
    better_city = random.choice(options)
    return f"{better_city} seems to have better weather than {base_city} today."

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import search_planes

load_dotenv()

# Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def search_planes_for_agent(
    origin: str,
    destination: str,
    currency: str = "RUB",
    min_price: float | None = None,
    max_price: float | None = None,
    period_type: str | None = None,
    beginning_of_period: str | None = None,
) -> dict:
    """Search for flights and filter the results."""

    return search_planes(
        origin=origin,
        destination=destination,
        currency=currency,
        min_price=min_price,
        max_price=max_price,
        period_type=period_type,
        beginning_of_period=beginning_of_period,
    )


def filter_planes_for_agent(
    planes: list[dict],
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """Filter already retrieved flight results by price."""

    results = []

    for plane in planes:
        price = plane.get("price")

        if not isinstance(price, (int, float)):
            continue

        if min_price is not None and price < min_price:
            continue

        if max_price is not None and price > max_price:
            continue

        results.append(plane)

    return results


chat = client.chats.create(
    model="gemini-3.5-flash",
    config=types.GenerateContentConfig(
        tools=[
            search_planes_for_agent,
            filter_planes_for_agent,
            types.Tool(
                google_search=types.GoogleSearch()
            ),
        ],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="AUTO"
            )
        ),
        system_instruction="""
        You are Zhenya, an AI travel operator.
        Help users find flights between cities.
        When a user asks to find flights:
        - Identify the departure and destination cities.
        - Use IATA city codes for the flight search tool.
        - Ask for missing essential details when necessary.
        - Use the flight search tool when the user requests flight prices.
        - Respect the user's currency and price limits.
        - Explain that returned prices may be cached and can change.
        - Never invent flight prices, schedules, or booking links.
        - Present results clearly, including route, departure date,
          return date if available, price, and number of transfers.
        - If no results are found, explain that and suggest
          changing the route, date, or price range.
        - Use Google Search for general travel questions when useful.
        - Do not claim to book a flight unless a booking tool
          is actually available.
        """
    ),
)

print("Travel O!perator Zhenya")
print("Describe the flight you are looking for.")
print("Type 'exit' to exit.\n")

while True:
    user_message = input("You: ").strip()

    if user_message.lower() == "exit":
        print("Goodbye!")
        break

    if not user_message:
        continue

    try:
        response = chat.send_message(user_message)
        print("\nZhenya:", response.text or "No text response.", "\n")

    except Exception as error:
        print(f"Error: {error}")

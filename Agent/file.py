import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import search_hotels, format_hotel_results, filter_hotels

load_dotenv()

#Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def search_hotels_for_agent(
    location: str,
    check_in: str,
    check_out: str,
    adults: int,
    children: int,
    children_ages: list[int],
    min_price: float,
    max_price: float,
    pets_allowed: bool,
    accessibility: list[str],
    min_rating: float | None = None,
    required_amenities: list[str] | None = None,
):
    """Search for accommodation and filter the results."""

    data = search_hotels(
        location=location,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        children_ages=children_ages,
        min_price=None,
        max_price=None,
        pets_allowed=pets_allowed,
        accessibility=accessibility,
    )

    results = format_hotel_results(data)

    results["hotels"] = filter_hotels(
        hotels=results["hotels"],
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        required_amenities=required_amenities,
        pets_allowed=True if pets_allowed else None,
    )

    return results


def filter_hotels_for_agent(
    hotels: list[dict],
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    required_amenities: list[str] | None = None,
    pets_allowed: bool | None = None,
):
    """Search for accommodation and return structured results."""

    return filter_hotels(
        hotels=hotels,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        required_amenities=required_amenities,
        pets_allowed=pets_allowed,
    )

chat = client.chats.create(
    model="gemini-3.6-flash",
    config=types.GenerateContentConfig(
        tools=[search_hotels_for_agent, filter_hotels_for_agent,],

        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="AUTO"
            )
        ),

        system_instruction="""
        You are an AI travel and hotel assistent.
        
        HOTEL SEARCH RULES:
        - When a user asks to find or compare accommodation,
          use search_hotels_for_agent to retrieve hotel data.
        - Collect the destination, check-in and check-out dates,
          number of adults and children, and children's ages.
        - Collect the minimum and maximum nightly budget.
        - Collect pet requirements and accessibility needs.
        - If required information is missing, ask the user for it.
        - Never invent hotel results or claim unknown features
          are confirmed.
        - Clearly disclose when results come from sandbox data.
        - For general questions that don't require a hotel search,
          answer normally without calling the search function.
        
        When the user asks to find accommodation:
        1. Extract the destination, dates, budget, and guest details.
        2. Ask for any missing required information.
        3. Call search_hotels when you have enough information.
        4. Explain the returned results clearly.
        
        Never invent hotel details.
        Treat missing pet policy or accessibility information 
        as unknown, not as confirmed or denied.
        The current API may return sandbox sample data,
        not live hotel availability.
        
        For every hotel search:
        - Provide every argument required by the search function.
        - Always pass min_price and max_price when the user gives a budget.
        - Pass the number of children and their ages.
        - Use an empty list for children_ages if there are no children.
        - Pass accessibility requirements as a list, such as ["wheelchair"].
        - Pass an empty list if no accessibility requirements were given.
        - Do not make another search with changed guest details unless the user requests it.
        - Never silently remove a user's requirements.
        
        RESULT HANDLING:
        - Use only the hotel data returned by the search function.
        - Show the hotel name, location, nightly price, total price,
          capacity, rating, amenities, and booking URL when available.
        - State the currency exactly as returned by the API.
        - Clearly identify sandbox results as sample data.
        - Never present a sandbox result as a confirmed match for
          the requested destination or dates.
        - Mark pet policies and accessibility as unknown when
          the returned data does not confirm them.
        - If no suitable results are available, say so honestly.
        
        TOOL USAGE:
        - Use search_hotels_for_agent first to retrieve hotel data.
        - After receiving the search results, use filter_hotels_for_agent
          when the user requests additional filters such as minimum rating
          or required amenities.
        - Pass the actual hotel list returned by the search tool to
          filter_hotels_for_agent. Never invent or manually create hotel data.
        - Apply price limits, rating requirements, amenities, and pet-policy
          requirements without silently dropping any user requirement.
        - If the search returns no hotels, explain that there are no results
          to filter.
        - If results are sandbox samples, identify them as samples, not live matches.
        - Never claim unknown details are confirmed.
        """
    ),
)

print("Travel O!perator Zhenya")
print("Describe the accommodation you are looking for.")
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
        print("\nZhenya:", response.text, "\n")

    except Exception as error:
        print(error)


#Find hotels in Moscow from November 12 to November 15, 2026, for 2 adults. Filter the results to hotels with a nightly price below €200 and a rating of at least 8.5.
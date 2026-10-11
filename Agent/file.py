import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tools import search_hotels

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
):
    return search_hotels(
        location=location,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        children_ages=children_ages,
        min_price=min_price,
        max_price=max_price,
        pets_allowed=pets_allowed,
        accessibility=accessibility,
    )

chat = client.chats.create(
    model="gemini-3.6-flash",
    config=types.GenerateContentConfig(
        tools=[search_hotels_for_agent],
        system_instruction="""
        You are an AI travel and hotel assistent.
        
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
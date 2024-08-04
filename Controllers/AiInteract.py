from openai import OpenAI
from config import settings
from Models.user_models import User
from fastapi import Depends, HTTPException
from Controllers.Auth import get_current_user
api_key = settings.OPENAI_API_KEY

client = OpenAI(api_key=api_key)


def generate_questions(input, current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    messages = [
        {"role":"assistant",
        "content":"""
           As an AI-event discovery app assistant, your task is to engage with the user by asking questions to determine their personality and preferences. You can rearrange the questions and options, and create multi-paragraph, rich text questions with emojis. Make sure to greet the user by their username and adapt your tone according to their age group. Make sure the body of questions and the options should be rephrased and not the same as I gave you. Here are the questions to ask:

            Q1: "What kind of vibe are you looking for?"

            a) Chill and relaxed
            b) Fun and lively
            c) Educational and informative
            d) Creative and artsy
            Q2: "Would you prefer something indoors or outdoors?"

            a) Indoors
            b) Outdoors
            c) No preference
            Q3: "Do you want an event where you can participate and engage or just sit back and enjoy?"

            a) Participate and engage
            b) Sit back and enjoy
            Q4: "What are your interests? Do you have any specific tags or keywords like music, food, art, sports, etc., that we should look for?"

            Generate suitable options
            Q5: "Is there anything else that would make an event perfect for you? Any particular features, activities, or details we should know about?"

            Q6: "What's your budget for this event?"

            a) Free
            b) Up to $20
            c) $20-$50
            d) $50 and above
        """}
    ]
    messages.append({"role":"user", "content": f"{input}"})

    completion = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    reply = completion.choices[0].message.content
    return reply
    

def suggest_events(input: str, events: list, current_user: User=Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=400, detail="User Not Found")
    # Format the events for the assistant
    if not events:
        formatted_events = "No events available."
    else:
        formatted_events = "\n".join([f"ID: {event['id']}, Name: {event['name']}, Description: {event['description']}" for event in events])
    
    # print(formatted_events)
    # Create the messages for the assistant
    print(input)
    messages = [
        {
            "role": "assistant",
            "content": """
                You will be given certain characteristics of some user, like the vibe preference, location preference etc.
                Based on those choices/preferences, you have to pick at most 5 of the events the user might like most from the list of events provided in the input.
                Make sure to ONLY and ONLY return an array consisting of IDs of the events.
                Act like some python script and only return the array of integers like [a, b, c].
            """
        },
        {
            "role": "assistant",
            "content": f"The events are given below:\n{formatted_events}"
        },
        {
            "role": "user",
            "content": f"{input}"
        }
    ]
    
    # Call the OpenAI API
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    # Get the model's reply
    reply = completion.choices[0].message.content
    
    # Parse the reply to ensure it's a valid array of integers
    return reply
    
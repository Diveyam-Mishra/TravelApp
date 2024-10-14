from openai import AzureOpenAI
from config import settings
from Models.user_models import User
from fastapi import Depends, HTTPException
from Controllers.Auth import get_current_user
api_key = settings.OPENAI_API_KEY
import ast
azure_api_key = settings.AZURE_OPENAI_API_KEY
azure_endpoint = settings.AZURE_OPENAI_ENDPOINT
azure_devname = settings.AZURE_OPENAI_DEVNAME
client = AzureOpenAI(
    api_key=azure_api_key,  
    api_version="2024-02-01",
    azure_endpoint = azure_endpoint
    )

deployment_name=azure_devname


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
        formatted_events = events

    # print(formatted_events)

    prompt = f"""
    You will be given certain characteristics of some user, like the vibe preference, location preference, engagement level, interest areas, and budget.
    Based on those choices/preferences, pick at most 6 events from the list of events provided in the input that most closely (not necessarily accurate) match these characteristics.
    ONLY return an array consisting of the event IDs, like [a, b, c].
    Act like a python script to return only the list of string with the ids of events. Nothing else just a list of strings.

    The events are given below:
    {formatted_events}

    User input:
    {input}
    """

    
    # Call the OpenAI API
    completion = client.completions.create(
        model=deployment_name,
        prompt=prompt,
        temperature=1,
        max_tokens=1000,
        top_p=0.5,
        frequency_penalty=0,
        presence_penalty=0,
        best_of=1,
        stop=None
    )
    
    # Get the model's reply
    reply = completion.choices[0].text
    # print(reply)
    # print(reply)
    # Parse the reply to ensure it's a valid array of strings
    try:
        output_part = reply.split("Output:")[1].strip()

        # Parse the list from the output
        events_list = ast.literal_eval(output_part)
        if not isinstance(events_list, list):
            raise ValueError("Reply is not a list.")
    except (SyntaxError, ValueError):
        raise HTTPException(status_code=500, detail="Failed to parse the event IDs")

    return events_list
    

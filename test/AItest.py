from openai import OpenAI
api_key = "sk-proj-MQZFmmfDWdx4oZM5hJ7CT3BlbkFJlvavPh9R6fLOTHxUdFzo"
client = OpenAI(api_key=api_key)


def generate_description(input):
    messages = [
        {"role":"assistant",
        "content":"""
        As an app assistant and question asker, you will be provided with an array of questions and an array of corresponding answers. Your task is to generate multi-paragraph rich text questions with emojis to ask the user, aiming to specify their personality type. You can rephrase the questions and options, and you are also allowed to rearrange the order of the questions.

        Please greet the user by their name, which will be provided to you in the input. When presenting options, format them as (A), (B), (C), etc., to ensure clarity.

        Below is the class structure which will be sent as a description in the API call:
        
        class Questions(BaseModel):
            question: str

        class Options(BaseModel):
            options: List[str]

        class Samples(BaseModel):
            userName: str
            questions: List[Questions]
            options: List[Options]
        """},
    ]

    messages.append({"role":"user", "content": f"{input}"})

    completion = client.chat.completions.create(model="gpt-3.5-turbo",
    messages=messages)
    reply = completion.choices[0].message.content
    return reply

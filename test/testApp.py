from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from AItest import generate_description

app = FastAPI()

class Questions(BaseModel):
    question: str

class Options(BaseModel):
    options: List[str]

class QuesWithOptions(BaseModel):
    question: Questions
    options: Options

class Samples(BaseModel):
    userName: str
    Questions: List[QuesWithOptions]


@app.post("/product_description")
async def generate_product_description(query: Samples):
    description = generate_description(f"userName:{query.userName},  Questions: {query.Questions}")
    return {"QuestionRephrased": description}

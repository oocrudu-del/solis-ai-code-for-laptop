from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

# तिम्रो AI function import गर
from main import split_commands, controller
from taxt_to_speak import speak

app = FastAPI()

class RequestModel(BaseModel):
    message: str

@app.get("/")
def home():
    return {"message": "Dipu AI Server Running 🔥"}

@app.post("/chat")
async def chat(req: RequestModel):
    user_input = req.message.lower()

    try:
        # direct controller use
        response = controller(user_input)

        # बोल्न पनि लगाउने (optional)
        asyncio.create_task(speak(response))

        return {
            "response": response
        }

    except Exception as e:
        return {
            "response": "Error processing request"
        }
        
        
        
        
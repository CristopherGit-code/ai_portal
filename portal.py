from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from modules.chain.layout_graph import ChainManager
import uvicorn
import json

app = FastAPI()

# Missing out of test security rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chain = ChainManager()

def json_response_parser(response):
    """ Parsing the string / message state function to JSON """
    try:
        data = json.loads(response)
        return data
    except json.JSONDecodeError as e:
        print(e)
        return {"error":e}

async def call_main_graph(query:str)->str:
    """ Calls the complete graph """
    response = await chain.call_main_graph(query)
    data = json_response_parser(response)
    return data

@app.get("/get-response")
async def get_response(query:str = Query(...,description="User query to agent")):
    result = await call_main_graph(query)
    return {"result": result}

if __name__ == "__main__":
    uvicorn.run(
        "portal:app",
        host="0.0.0.0",
        port=8000
    )
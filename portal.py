from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from modules.main_graph.layout_graph import ChainManager
import uvicorn

app = FastAPI()

# Not security rules for testing purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def call_main_graph(query:str)->str:
    """ Calls complete graph """
    chain = ChainManager()
    response = await chain.call_main_graph(query)

    return response

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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
from agent import MealPlannerAgent
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Store active websocket connections and their agents
connections: Dict[str, WebSocket] = {}
agents: Dict[str, MealPlannerAgent] = {}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get_root():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    try:
        await websocket.accept()
        connections[client_id] = websocket
        
        # Create agent with websocket using async context
        async with MealPlannerAgent() as agent:
            agent.websocket = websocket
            agents[client_id] = agent
            
            # Start planning session in background task
            planning_task = asyncio.create_task(handle_planning_session(agent, client_id))
            
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    if message["type"] == "user_input":
                        # Handle user input during the conversation
                        if client_id in agents:
                            await agent.user_input_queue.put(message["content"])
                    
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                # Cancel planning task
                planning_task.cancel()
                try:
                    await planning_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error(f"Error in websocket connection: {str(e)}")
                if not planning_task.done():
                    planning_task.cancel()
                    try:
                        await planning_task
                    except asyncio.CancelledError:
                        pass
    
    finally:
        # Clean up
        if client_id in connections:
            del connections[client_id]
        if client_id in agents:
            del agents[client_id]

async def handle_planning_session(agent: MealPlannerAgent, client_id: str):
    """Handle a complete meal planning session."""
    try:
        await agent.run()
    except asyncio.CancelledError:
        logger.info(f"Planning session cancelled for client {client_id}")
        raise
    except Exception as e:
        logger.error(f"Error in planning session: {str(e)}")
        # Send error message to client
        if client_id in connections:
            websocket = connections[client_id]
            await websocket.send_json({
                "type": "error",
                "content": f"An error occurred: {str(e)}"
            })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
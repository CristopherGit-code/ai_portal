# AI party/meeting planning application

> [!NOTE]  
> Last update 8-15-2025

Full integration on complex planning agent flow, includes verification of query scope, parallel agent calling, planning, selection and execution or relevant tasks to address user query.

## Features

- [Dynamic UI](modules/UI/index.html) Front interface for the user to interact with the application and receive the modules in response
- [JS UI build](modules/UI/js/chat.js) Functions in charge of getting JSON chain response and build components with the instructions
- [Main Chain](modules/chain/layout_graph.py) Main chain manager with big picture graph to call each step of the agent application
- [Executor](modules/cluster/executor.py) Agent with the instruction to execute the different plans, decide which agents are relevant and wrap up all the necessary responses
- [A2A servers](remote) Different servers with AI agents capable to connect via A2A protocol, used for running the tasks assigned by the executor agent. Currently out of the chain, but planned to add during executor agent call to complete the requests
- [MCP](remote/mcp/servers/) Two different MCP servers to connect with real weather data and manage file system.
- [Worker manager](modules/cluster/worker_manager.py) Class to hold connections to agent and provide the tools to call the different expertise scopes.
- [Worker agents](modules/cluster/workers/) Different agent modules with own instructions, functions and extra steps to complete tasks. This agents are in charge of manage the different steps of the chain and create the different calls through the complete application
- [Layout agent](modules/cluster/layout_builder.py) agent in charge of building the compilation of the JSON instructions for the UI based on the agent query responses. Uses agents with structured output as tools to do the compilation.

## Setup

1. Get the necessary dependencies (use python venv / toml)
2. Create .env file to set the environment variables for OCI setup (also mutable to other LLM providers given API key)
    - Ensure to modify the file [yaml](modules/util/config/config.yaml) to add routes and variables
    - Check the other files in servers folder
3. Run first the MCP servers from [MCP](remote/mcp/servers/) and ensure the ports are corresponding
4. Run the main A2A agents and servers from [A2A servers](remote). Each folder contains its respective agent, executor and A2A server to run
5. Ensure the [portal.py](portal.py) file is set and making the right function call to the main chain. Run the uvicorn server.
6. Once the portal is up, go to [Index](modules/UI/index.html) and run the ```HTML``` in browser.
7. Send a query and wait for the UI components to display.
8. For langfuse tracing ensure to modify the ```.env``` file and add the necessary keys inside the configuration from main chain and servers.

## Basic walkthrough

- [Final Result](walkthrough/Demo_example_view.png) An example of the interface after the AI query received and processed using the chain.

### Week 3 (Dynamic UI and layout formatted response)

- [Demo video](walkthrough/AI_portal_final_Demo_w3.mp4)
- [Architecture](walkthrough/Highlevel_final_flow.png)

*UML diagrams*
- [Use case](walkthrough/Use_case_ai_portal.png) Simple use cases for the application
- [Class Diagram](walkthrough/Class_diagram_ai_portal.png) Includes main class interaction, and main instances used
- [Sequence Diagram](walkthrough/Sequence_diagram_ai_portal.png) Main sequence of the application calls

### Week 2 (Add MCP, A2A connections and lite front layer):

- [Demo video](walkthrough/MCP_AI_Portal_Demo_week2.mp4)
- [Architecture](walkthrough/AI_portal%20MCP_week2.png)

### Week 1 (Main chain logic setup):

- [Demo video](walkthrough/AI_planning_app_demo_week1.mp4)
- [Architecture](walkthrough/Ai_portal_week1.png)

## Sample core details

- [Portal](portal.py) uses the function ```call_main_graph``` to start the process, with the user query in it.
- [layout_graph.py](modules/chain/layout_graph.py) receives the call and implements an async streaming response method using ```async for chunk in self.graph.astream```.

This is calling the ```self.graph``` object which is a _langgraph compiled graph_ object, in charge of all the chain management and responses.

```build_main_graph``` function in the same file is in charge of creating the logic and call the functions from the different agents in the chain
- [worker_manager.py](modules/cluster/worker_manager.py) holds all the helper agents that have access to the information from the A2A and MCP servers.

This agents have the single tool ```send_task2_name_expert``` which depending on the name of the agent will send an a2a request to the expert agent and will wait for the response from the agent.

The executor agent has an extra layer, it uses the function ```call_name_agent``` to call each one of the helper agents in need, then those helper agents can use the ```send_task2_name_expert``` tool to actually complete the workflow.

- After all the calls are done, the python portal server returns the final compound of the response so the JavaScript code generates the different UI components.

<!-- https://www.chartjs.org/docs/latest/ -->
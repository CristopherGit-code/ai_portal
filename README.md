# AI party/meeting planning application

> [!NOTE]  
> Last update 8-05-2025

Full integration on complex planning agent flow, includes verification of query scope, parallel agent calling, planning, selection and execution or relevant tasks to address user query.

## Features

- [Main Chain](modules/graph/layout_graph.py) Main chain manager with big picture graph to call each step of the agent application
- [Chain Agents](modules/cluster/) Different agent modules with own instructions, functions and extra steps to complete tasks. This agents are in charge of manage the different steps of the chain and create the different calls through the complete application
- [Layout agent](modules/cluster/layout.py) main parallel call agent that indicates the expertise modules to create a sample plan to address the user query
- [Executor](modules/cluster/executor.py) Agent with the instruction to execute the different plans, decide which agents are relevant and wrap up all the necessary responses
- [servers](servers) Different servers with AI agents capable to connect via A2A protocol, used for running the tasks assigned by the executor agent. Currently out of the chain, but planned to add during executor agent call to complete the requests

## Setup

1. Get the necessary dependencies (use python venv / toml)
2. Create .env file to set the environment variables for OCI setup (also mutable to other LLM providers given API key)
    - Ensure to modify the file [yaml](modules/util/config/config.yaml) to add routes and variables
    - Check the other files in servers folder
3. Run the different servers from the server folder and ensure the ports are the same selected
4. Run from the file [Layout graph](modules/graph/layout_graph.py), this will wait for a user query and show some logging for the application process
4. Set up langfuse in [fuse_config](modules/util/lang_fuse.py), requires cloud or VM langfuse server host to send the tracing and catch all the entries during the application run

## Basic walkthrough

- [Demo video](walkthrough/AI_planning_app_demo.mp4)
- [Architecture](walkthrough/Ai_portal_w1.png)
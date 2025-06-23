# Rental Agent Phaser Frontend

This is a Phaser 3 implementation of the Rental Agent frontend, providing a 2D pixel-art visualization of multi-agent rental negotiations.

## Overview

The frontend displays a sandbox world where tenant and landlord agents interact through negotiations. The system visually represents the conversation flow between AI agents with animations, dialogue bubbles, and emotion indicators.

## Features

- **Real-time agent visualization**: Characters move around the map based on backend events
- **Dialogue display**: Shows conversation between agents in speech bubbles
- **Emotion indicators**: Visual feedback of agent emotional states
- **WebSocket integration**: Real-time updates from the LangGraph-based backend
- **Contract signing area**: Visual indication when a deal is reached

## Setup

1. Run the setup script to install dependencies and set up assets:

   ```bash
   ./setup.sh
   ```

2. Start the frontend:

   ```bash
   ./run_frontend.sh
   ```

3. Ensure the backend server is running on `http://localhost:8000` before starting negotiations.

## Controls

- **Start Negotiation**: Begins a new negotiation session between tenant and landlord agents
- **Reset**: Resets the memory state and returns agents to their starting positions

## Event System

The frontend responds to these backend WebSocket events:

- `agent_started`: When an agent begins processing
- `message_sent`: When a message is sent between agents
- `agent_thought`: Internal thought processes of agents
- `agent_matched`: When a tenant is matched with a landlord
- `agreement_reached`: When agents reach a rental agreement
- `dialogue_ended`: When a negotiation ends without agreement

## Architecture

- **MainScene.js**: Core game scene with map, characters and physics
- **UIScene.js**: Overlay scene for UI elements
- **Tenant.js/Landlord.js**: Character classes with movement and dialogue functionality
- **ApiService.js**: Handles communication with the backend API
- **WebSocketClient.js**: Manages WebSocket connections for real-time updates

## Technical Details

Built with:

- **Phaser 3**: Game framework for rendering and animations
- **Vite**: Development and build tooling
- **WebSockets**: Real-time communication with the backend

## Assets

The frontend uses the same pixel art assets as the original Godot implementation:

- Character sprites
- Tileset graphics
- UI elements

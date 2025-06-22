# Godot Frontend Implementation for Rental Agent System

## Overview

This document describes the implementation of a pixel-style sandbox frontend for the multi-agent rental negotiation system using the Godot Engine. The frontend visualizes the communication between tenant and landlord agents in real-time.

## Architecture

### Core Components

1. **API Service**: Singleton for handling communication with the backend through HTTP requests and WebSocket connections.

2. **Characters**: Interactive entities in the world that represent tenants and landlords, with animations and speech capabilities.

3. **UI System**: Displays conversation messages, status updates, and provides user controls.

4. **Navigation System**: Allows characters to move around the world to reflect the stages of negotiation.

## File Structure

```
godot-frontend/
├── scenes/
│   ├── Main.tscn              # Main scene with world and UI
│   ├── Character.tscn         # Character template
│   ├── Message.tscn           # UI message template
├── scripts/
│   ├── Main.gd                # Main scene controller
│   ├── Character.gd           # Character behavior
│   ├── SpeechBubble.gd        # Speech bubble rendering
│   ├── Message.gd             # Message formatting
│   ├── ApiService.gd          # Backend communication
├── assets/
│   ├── tilesets/              # Tileset assets for the world
│   ├── characters/            # Character sprites
│   ├── ui/                    # UI elements and icons
```

## WebSocket Integration

The frontend connects to the backend's WebSocket API to receive real-time updates about the negotiation process. The connection flow is:

1. Start a negotiation session via HTTP call to `/start-auto-negotiation-live`
2. Connect to the WebSocket endpoint at `ws://localhost:8000/ws/{session_id}`
3. Process incoming events:
   - `agent_started`: When a tenant or landlord agent begins processing
   - `message_sent`: When a message is sent between agents
   - `agent_thought`: Internal thoughts of agents
   - `agreement_reached`: When negotiation succeeds
   - `negotiation_ended`: When negotiation ends (success or failure)

## Character Behavior

Characters (tenants and landlords) react to the negotiation flow through:

1. **Speech Bubbles**: Display the content of messages sent by each agent
2. **Emotion Icons**: Show emotions based on message sentiment analysis
3. **Animations**: Express states like thinking, celebrating, or disappointment
4. **Movement**: Characters physically move to the contract signing area when an agreement is reached

## Visual Feedback

The system provides several layers of visual feedback:

1. **Message Panel**: All messages are displayed in a scrollable panel
2. **Character Reactions**: Characters express emotions through icons and animations
3. **Environment Changes**: The contract signing area highlights when an agreement is reached
4. **Status Updates**: System status is always visible to indicate the negotiation state

## Required Assets

The implementation requires pixel-art assets which need to be created or sourced:

1. **Character Spritesheets**: For tenant and landlord animations
2. **Tilesets**: For the world environment
3. **UI Elements**: Icons, speech bubbles, and emotion indicators
4. **Contract Icon**: Visual representation of the agreement

## Setup Instructions

1. Install Godot 4.2 or higher
2. Run the setup script to create placeholder assets
3. Replace placeholders with actual assets
4. Ensure the backend server is running
5. Run the Godot project

## Backend Communication Requirements

This frontend expects the following from the backend:

1. A REST API endpoint for starting negotiations
2. A WebSocket endpoint for streaming events
3. Specific event messages formatted as described in the WebSocket integration section

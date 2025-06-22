# Rental Agent Godot Frontend

This is a pixel-style sandbox frontend for visualizing the multi-agent rental negotiation system. The frontend connects to the LangGraph-powered backend to display real-time conversations between tenant and landlord agents.

## Installation & Setup

1. Install Godot 4.2 or higher
2. Open the project by selecting the `project.godot` file
3. Ensure the backend server is running on `localhost:8000` (or modify the API_BASE_URL in ApiService.gd)
4. Run the project in Godot

## Required Assets

The following assets need to be generated/acquired:

### Tilesets
- `assets/tilesets/ground_tileset.png` - A basic tileset for the ground with 4x4 tiles (32x32px each)

### Character Sprites
- `assets/characters/character_placeholder.png` - Character sprites in a spritesheet format (4 columns x 5 rows):
  - First row: Idle animations
  - Second row: Walking down animations
  - Third row: Walking up animations 
  - Fourth row: Walking side animations
  - Fifth row: Special animations (celebrate, disappointed)

### UI Elements
- `assets/ui/tenant_icon.png` - Icon for tenant messages
- `assets/ui/landlord_icon.png` - Icon for landlord messages
- `assets/ui/system_icon.png` - Icon for system messages
- `assets/ui/contract_icon.png` - Icon displayed in the contract signing area
- `assets/ui/emotions.png` - A spritesheet of emotion icons (3x2 grid with happy, confused, angry, thinking, agreement, neutral)
- `assets/ui/pixel_font.tres` - A pixel-style font resource

## Usage

1. Start the backend server
2. Run the Godot project
3. Click the "Start Negotiation" button
4. Observe as:
   - Tenant is matched with an appropriate landlord
   - Characters exchange messages via speech bubbles
   - Messages appear in the UI panel at the bottom
   - Emotions are displayed based on message content
   - Upon agreement, characters move to the contract signing area

## Architecture

- `ApiService.gd` - Singleton that manages API communication with the backend
- `Character.gd` - Controls character behavior, animations, and dialogue
- `SpeechBubble.gd` - Renders dynamic speech bubbles above characters
- `Message.gd` - Format and style messages in the UI
- `Main.gd` - Overall scene management and coordination

## Backend Integration

The frontend connects to the backend via:
1. HTTP for session management
2. WebSocket for real-time event streaming

Key endpoints used:
- `/start-auto-negotiation-live` - Start a negotiation session
- `/reset-memory` - Reset conversation memory
- `/ws/{session_id}` - WebSocket connection for streaming events

## Customization

You can customize the frontend by:
- Adding more character types
- Creating different building types for different property types
- Enhancing animations and visual effects
- Adding sound effects and music

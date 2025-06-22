# Rental Agent System with Godot Frontend

This project implements a multi-agent dialog system for rental negotiations, with a pixel-style sandbox visualization frontend built with Godot Engine.

## System Components

### Backend (Python/LangGraph)
- LangGraph-based multi-agent system
- MongoDB for memory and state management
- FastAPI for REST and WebSocket endpoints

### Frontend (Godot Engine)
- Pixel-style sandbox visualization
- Real-time agent conversations with speech bubbles
- Character animations reflecting negotiation state
- WebSocket integration for streaming updates

## Setup Instructions

### Backend Setup
1. Navigate to the `backend` directory
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Configure MongoDB connection in `config/config.toml`
4. Start the API server:
   ```bash
   python -m backend.main
   ```

### Frontend Setup
1. Navigate to the `godot-frontend` directory
2. Run the setup script to create directories and placeholder assets:
   ```bash
   ./setup.sh
   ```
3. Replace placeholder assets with actual pixel art assets
4. Open the project in Godot 4.2+ or run:
   ```bash
   ./run_frontend.sh
   ```

## Usage Flow

1. Start the backend server
2. Launch the Godot frontend
3. Press "Start Negotiation" in the frontend
4. Watch as:
   - Tenant agent matches with a suitable landlord
   - Agents negotiate through natural language messages
   - Characters react with emotions and animations
   - Upon agreement, characters move to signing area

## Asset Requirements

The Godot frontend requires the following assets to be created or sourced:

- Character spritesheets for tenants and landlords
- Tileset for the environment
- UI elements (icons, speech bubbles, emotion indicators)
- Font resources

See `godot-frontend/assets/PLACEHOLDERS.md` for detailed asset specifications.

## Project Structure

```
Rental_Agent/
├── backend/                # LangGraph multi-agent system
│   ├── app/                # Core application code
│   ├── config/             # Configuration files
│   └── ...
├── godot-frontend/         # Godot visualization frontend
│   ├── assets/             # Game assets (sprites, tiles, etc.)
│   ├── scenes/             # Godot scene files
│   ├── scripts/            # GDScript code
│   └── project.godot       # Godot project file
```

## License

MIT

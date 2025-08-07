# Rental Agent Maps Frontend

Multi-agent rental negotiation visualization system based on Google Maps

## 🗺️ Features

- **Google Maps Integration**: Display agent locations and property information using real maps
- **Real-time Negotiation Visualization**: Show agent dialogue process through map markers and conversation bubbles  
- **Multi-agent Support**: Support multiple tenant and landlord agents interacting simultaneously on the map
- **WebSocket Communication**: Real-time synchronization with backend for negotiation status and messages
- **Responsive Design**: Compatible with desktop and mobile devices

## 🏗️ Architecture Components

### Map Module (`/src/maps/`)

- **MapManager**: Google Maps core manager
- **GoogleMapsLoader**: Dynamic loading of Google Maps API  
- **AgentMapController**: Agent map controller

### Network Module (`/src/network/`)

- **NetworkManager**: HTTP request and WebSocket connection management

### Main Application (`/src/main.js`)

- **RentalAgentApp**: Main application controller that coordinates all modules

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Google Maps API (Optional)

Edit configuration in `src/main.js`:

```javascript
const config = {
    apiKey: 'YOUR_GOOGLE_MAPS_API_KEY', // Optional, will use free version if not provided
    backendUrl: 'http://localhost:8000',
    mapContainer: 'map'
};
```

### 3. Start Development Server

```bash
npm run dev
```

### 4. Build Production Version

```bash
npm run build
```

## 📡 Backend Communication

### REST API Endpoints

- `POST /start-session`: Start negotiation session
- `POST /reset-memory`: Reset memory state

### WebSocket Events

- `agent_started`: Agent starts action
- `message_sent`: Send message
- `agent_thought`: Agent thinking
- `negotiation_update`: Negotiation progress update
- `agreement_reached`: Agreement reached
- `dialogue_ended`: Dialogue ended

## 🎮 User Interaction

### Main Features

1. **Start Negotiation**: Click "Start Negotiation" button to start new negotiation session
2. **Reset Session**: Clear current session state and restart
3. **View Logs**: Real-time view of all events during negotiation process
4. **Map Interaction**: Click on agent and property markers on map to view detailed information

### Map Elements

- **Blue Markers**: Tenant agents
- **Red Markers**: Landlord agents
- **House Icons**: Available rental properties
- **Dialogue Bubbles**: Real-time display of agent conversation content

## 🔧 Custom Configuration

### Map Styling

Customize map appearance in the `getMapStyles()` method in `MapManager.js`.

### Agent Positions

Modify `agentPositions` and `propertyPositions` arrays in `AgentMapController.js` to adjust default positions.

### UI Theme

Customize colors and layout in the `<style>` section of `index.html`.

## 📱 Responsive Support

System supports desktop and mobile devices:

- Desktop: Sidebar + map layout
- Mobile: Stacked layout with control panel on top

## 🔒 Security Considerations

- Google Maps API Key should be configured with domain restrictions
- Use HTTPS in production environment
- WebSocket connections support automatic reconnection mechanism

## 🔍 Debug Mode

Open browser developer tools to view detailed logs:

- `[RentalAgentApp]`: Main application logic
- `[MapManager]`: Map operations
- `[NetworkManager]`: Network communication
- `[AgentMapController]`: Agent control

## 📈 Performance Optimization

- Map markers managed using object pool
- WebSocket connections with heartbeat detection
- Automatic log entry limit to prevent memory leaks
- Responsive images and vector icons

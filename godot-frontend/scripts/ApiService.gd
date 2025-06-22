extends Node

# -----------------------------
# API Configuration
# -----------------------------
const API_BASE_URL = "http://localhost:8000"
const WS_BASE_URL = "ws://localhost:8000"

# -----------------------------
# Signals
# -----------------------------
signal connection_established(session_id)
signal connection_error(error)
signal negotiation_started(data)
signal negotiation_ended(reason)
signal message_received(message)
signal agent_thought_received(agent_name, thought)
signal agent_action_received(agent_name, action)
signal agreement_reached(details)
signal stats_updated(stats)
signal session_info_received(session_info)

# -----------------------------
# WebSocket Variables
# -----------------------------
var _ws_client = WebSocketPeer.new()
var _is_connected = false
var _session_id = ""
var _connection_timer = null

# -----------------------------
# Session Management
# -----------------------------
var active_sessions = []
var current_session = null
var session_messages = {}

# -----------------------------
# HTTP Request Objects
# -----------------------------
var start_negotiation_request = null
var stats_request = null
var reset_request = null

func _ready():
	# Initialize HTTP request objects
	start_negotiation_request = HTTPRequest.new()
	add_child(start_negotiation_request)
	start_negotiation_request.request_completed.connect(_on_start_negotiation_completed)
	
	stats_request = HTTPRequest.new()
	add_child(stats_request)
	stats_request.request_completed.connect(_on_stats_completed)
	
	reset_request = HTTPRequest.new()
	add_child(reset_request)
	reset_request.request_completed.connect(_on_reset_completed)
	
	# Initialize connection timer
	_connection_timer = Timer.new()
	add_child(_connection_timer)
	_connection_timer.wait_time = 30.0
	_connection_timer.one_shot = true
	_connection_timer.timeout.connect(_on_connection_timeout)

func _process(_delta):
	if _is_connected:
		_ws_client.poll()
		var state = _ws_client.get_ready_state()
		
		# Handle connection state
		if state == WebSocketPeer.STATE_OPEN:
			while _ws_client.get_available_packet_count():
				var packet = _ws_client.get_packet()
				var message = packet.get_string_from_utf8()
				_handle_ws_message(message)
		
		elif state == WebSocketPeer.STATE_CLOSING:
			# WebSocket is closing
			pass
			
		elif state == WebSocketPeer.STATE_CLOSED:
			var code = _ws_client.get_close_code()
			var reason = _ws_client.get_close_reason()
			print("WebSocket closed with code: %d, reason: %s" % [code, reason])
			_is_connected = false
			emit_signal("connection_error", "Connection closed: " + reason)

# -----------------------------
# Public API Methods
# -----------------------------

func start_auto_negotiation(max_tenants = 1):
	"""
	Start auto-negotiation with specified number of tenants
	"""
	var url = API_BASE_URL + "/start-auto-negotiation-live?max_tenants=" + str(max_tenants)
	var headers = ["Content-Type: application/json"]
	var error = start_negotiation_request.request(url, headers, HTTPClient.METHOD_POST, "")
	
	if error != OK:
		push_error("Error starting negotiation: " + str(error))

func reset_memory():
	"""
	Reset the conversation memory state
	"""
	var url = API_BASE_URL + "/reset-memory"
	var headers = ["Content-Type: application/json"]
	var error = reset_request.request(url, headers, HTTPClient.METHOD_POST, "")
	
	if error != OK:
		push_error("Error resetting memory: " + str(error))

func get_stats():
	"""
	Get negotiation statistics
	"""
	var url = API_BASE_URL + "/stats"
	var headers = ["Content-Type: application/json"]
	var error = stats_request.request(url, headers)
	
	if error != OK:
		push_error("Error fetching stats: " + str(error))

func connect_to_session(session_id):
	"""
	Connect to a specific session via WebSocket
	"""
	_session_id = session_id
	var url = WS_BASE_URL + "/ws/" + session_id
	
	# Close existing connection if any
	if _is_connected:
		_ws_client.close()
		_is_connected = false
	
	# Start connection timer
	_connection_timer.start()
	
	# Connect to WebSocket
	var error = _ws_client.connect_to_url(url)
	if error != OK:
		emit_signal("connection_error", "Failed to connect: " + str(error))
		return false
	
	return true

func disconnect_from_session():
	"""
	Disconnect from the current WebSocket session
	"""
	if _is_connected:
		_ws_client.close()
		_is_connected = false
		_session_id = ""

# -----------------------------
# Private Methods
# -----------------------------

func _handle_ws_message(message_text):
	"""
	Parse and handle incoming WebSocket messages
	"""
	var json = JSON.new()
	var error = json.parse(message_text)
	
	if error != OK:
		push_error("JSON Parse Error: " + json.get_error_message())
		return
	
	var message = json.get_data()
	var msg_type = message.get("type", "")
	
	match msg_type:
		"connected":
			_is_connected = true
			_connection_timer.stop()
			emit_signal("connection_established", message.get("session_id"))
		
		"session_info":
			current_session = message
			emit_signal("session_info_received", message)
		
		"agent_started":
			var agent_name = message.get("agent_name", "Unknown")
			print("Agent started: " + agent_name)
			emit_signal("message_received", {
				"agent": agent_name,
				"content": "Starting negotiation...",
				"is_system": true
			})
		
		"agent_thought":
			var agent_name = message.get("agent_name", "Unknown")
			var thought = message.get("thought", "")
			emit_signal("agent_thought_received", agent_name, thought)
		
		"message_sent":
			var content = message.get("content", "")
			var sender = message.get("sender", "")
			emit_signal("message_received", {
				"agent": sender,
				"content": content,
				"is_system": false
			})
			
		"agreement_reached":
			var details = message.get("details", {})
			emit_signal("agreement_reached", details)
			
		"negotiation_ended":
			var reason = message.get("reason", "Unknown")
			emit_signal("negotiation_ended", reason)

		"error":
			emit_signal("connection_error", message.get("message", "Unknown error"))
		
		"pong", "server_ping":
			# Handle keep-alive messages silently
			pass
			
		_:
			# Handle other message types
			emit_signal("message_received", {
				"content": "Received: " + msg_type,
				"is_system": true
			})

func _send_ping():
	"""
	Send ping to keep WebSocket connection alive
	"""
	if _is_connected:
		var ping_message = JSON.stringify({"type": "ping"})
		_ws_client.send_text(ping_message)

func _on_connection_timeout():
	"""
	Handle WebSocket connection timeout
	"""
	if not _is_connected:
		emit_signal("connection_error", "Connection timeout")

# -----------------------------
# HTTP Response Handlers
# -----------------------------

func _on_start_negotiation_completed(result, response_code, headers, body):
	if result != HTTPRequest.RESULT_SUCCESS:
		emit_signal("connection_error", "Failed to start negotiation")
		return
		
	if response_code == 200:
		var json = JSON.new()
		var error = json.parse(body.get_string_from_utf8())
		
		if error != OK:
			emit_signal("connection_error", "Invalid response")
			return
			
		var response = json.get_data()
		active_sessions = response.get("session_ids", [])
		
		if active_sessions.size() > 0:
			emit_signal("negotiation_started", response)
			# Automatically connect to the first session
			connect_to_session(active_sessions[0])
		else:
			emit_signal("connection_error", "No sessions created")
	else:
		emit_signal("connection_error", "Server error: " + str(response_code))

func _on_stats_completed(result, response_code, headers, body):
	if result == HTTPRequest.RESULT_SUCCESS and response_code == 200:
		var json = JSON.new()
		var error = json.parse(body.get_string_from_utf8())
		
		if error != OK:
			return
			
		var stats = json.get_data()
		emit_signal("stats_updated", stats)

func _on_reset_completed(result, response_code, headers, body):
	if result == HTTPRequest.RESULT_SUCCESS and response_code == 200:
		# Clear local session data
		active_sessions = []
		current_session = null
		session_messages = {}
		
		emit_signal("message_received", {
			"content": "Memory reset successful",
			"is_system": true
		})

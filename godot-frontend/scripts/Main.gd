extends Node2D

# -----------------------------
# Scene References
# -----------------------------
@onready var ui_panel = $CanvasLayer/UIPanel
@onready var message_container = $CanvasLayer/UIPanel/MessageContainer
@onready var start_button = $CanvasLayer/UIPanel/ButtonsPanel/StartButton
@onready var reset_button = $CanvasLayer/UIPanel/ButtonsPanel/ResetButton
@onready var status_label = $CanvasLayer/UIPanel/StatusLabel

# Character References
@onready var tenant = $World/Characters/Tenant
@onready var landlords_container = $World/Characters/Landlords

# Contract Zone
@onready var contract_zone = $World/ContractZone

# -----------------------------
# Game State
# -----------------------------
var active_session_id = ""
var active_landlord = null
var negotiation_active = false
var agreement_reached = false

# Message history
var message_history = []
var max_visible_messages = 10

# -----------------------------
# UI Templates
# -----------------------------
var message_scene = preload("res://scenes/Message.tscn")

# -----------------------------
# Core Functions
# -----------------------------
func _ready():
	# Setup UI
	reset_button.disabled = true
	
	# Connect signals
	start_button.pressed.connect(_on_start_button_pressed)
	reset_button.pressed.connect(_on_reset_button_pressed)
	
	# Connect to API signals
	ApiService.connection_established.connect(_on_ws_connected)
	ApiService.connection_error.connect(_on_ws_error)
	ApiService.negotiation_started.connect(_on_negotiation_started)
	ApiService.message_received.connect(_on_message_received)
	ApiService.agent_thought_received.connect(_on_agent_thought)
	ApiService.agreement_reached.connect(_on_agreement_reached)
	ApiService.negotiation_ended.connect(_on_negotiation_ended)
	
	# Initialize
	status_label.text = "Ready to start negotiation"
	clear_messages()

# -----------------------------
# Event Handlers
# -----------------------------
func _on_start_button_pressed():
	start_button.disabled = true
	status_label.text = "Starting negotiation..."
	clear_messages()
	
	# Reset state
	agreement_reached = false
	negotiation_active = false
	active_landlord = null
	
	# Reset characters
	tenant.position = tenant.get_parent().get_node("TenantStartPosition").position
	reset_all_characters()
	
	# Start negotiation via API
	ApiService.start_auto_negotiation(1)

func _on_reset_button_pressed():
	reset_button.disabled = true
	status_label.text = "Resetting memory..."
	
	# Reset the backend memory
	ApiService.reset_memory()
	
	# Reset local state
	reset_all_characters()
	active_session_id = ""
	active_landlord = null
	negotiation_active = false
	agreement_reached = false
	
	# Reset UI
	clear_messages()
	start_button.disabled = false
	status_label.text = "Ready to start negotiation"

func _on_ws_connected(session_id):
	status_label.text = "Connected to session: " + session_id
	active_session_id = session_id
	negotiation_active = true
	reset_button.disabled = false

func _on_ws_error(error):
	status_label.text = "Error: " + error
	start_button.disabled = false
	negotiation_active = false

func _on_negotiation_started(data):
	status_label.text = "Negotiation started"
	add_system_message("Starting tenant-landlord matching...")
	
	# Get session info
	var sessions = data.get("sessions", [])
	if sessions.size() > 0:
		var first_session = sessions[0]
		var property_id = first_session.get("property_id", "")
		var landlord_id = first_session.get("landlord_id", "")
		
		# Select landlord based on ID
		select_landlord(landlord_id)

func _on_message_received(message):
	var agent = message.get("agent", "")
	var content = message.get("content", "")
	var is_system = message.get("is_system", false)
	
	if is_system:
		add_system_message(content)
		return
	
	# Regular message from tenant or landlord
	if agent == "tenant":
		add_message("Tenant", content, "tenant")
		if active_landlord:
			tenant.say(content)
			tenant.react_to_message(message)
		
	elif agent == "landlord":
		add_message("Landlord", content, "landlord")
		if active_landlord:
			active_landlord.say(content)
			active_landlord.react_to_message(message)
			
	else:
		add_system_message("Message from unknown agent: " + content)

func _on_agent_thought(agent_name, thought):
	# Visualize the agent's internal thought process
	if agent_name == "tenant":
		tenant.show_emotion(tenant.Emotion.THINKING)
		# Could show a thinking bubble above the tenant if desired
	
	elif agent_name == "landlord" and active_landlord:
		active_landlord.show_emotion(active_landlord.Emotion.THINKING)
		# Could show a thinking bubble above the landlord if desired

func _on_agreement_reached(details):
	status_label.text = "Agreement reached!"
	agreement_reached = true
	
	add_system_message("Agreement reached! Monthly rent: $" + str(details.get("monthly_rent", 0)))
	
	# Move characters to contract zone for signing animation
	var contract_pos = contract_zone.global_position
	
	# Move tenant to left side of contract zone
	tenant.move_to(Vector2(contract_pos.x - 100, contract_pos.y))
	
	# Move landlord to right side of contract zone
	if active_landlord:
		active_landlord.move_to(Vector2(contract_pos.x + 100, contract_pos.y))
		
		# Show celebration animations
		tenant.celebrate_agreement()
		active_landlord.celebrate_agreement()

func _on_negotiation_ended(reason):
	status_label.text = "Negotiation ended: " + reason
	negotiation_active = false
	start_button.disabled = false
	
	add_system_message("Negotiation ended: " + reason)
	
	# If no agreement was reached, show disappointment
	if not agreement_reached:
		tenant.show_disappointment()
		if active_landlord:
			active_landlord.show_disappointment()

# -----------------------------
# Character Management
# -----------------------------
func select_landlord(landlord_id):
	# Find landlord with matching ID in landlords container
	for landlord in landlords_container.get_children():
		if landlord.name == "Landlord_" + landlord_id:
			active_landlord = landlord
			active_landlord.is_active = true
			add_system_message("Matching with landlord: " + landlord.character_name)
			return true
	
	# If not found, select the first landlord as fallback
	if landlords_container.get_child_count() > 0:
		active_landlord = landlords_container.get_child(0)
		active_landlord.is_active = true
		add_system_message("Matching with landlord: " + active_landlord.character_name + " (fallback)")
		return true
		
	return false

func reset_all_characters():
	# Reset tenant
	tenant.say("")
	tenant.emotion_icon.visible = false
	
	# Reset all landlords
	for landlord in landlords_container.get_children():
		landlord.is_active = false
		landlord.say("")
		landlord.emotion_icon.visible = false

# -----------------------------
# UI Management
# -----------------------------
func add_message(sender, content, sender_type):
	# Create a new message entry
	var msg_instance = message_scene.instantiate()
	msg_instance.set_message(sender, content, sender_type)
	
	# Add to container
	message_container.add_child(msg_instance)
	
	# Store in history
	message_history.append({
		"sender": sender,
		"content": content,
		"type": sender_type
	})
	
	# Auto scroll to bottom
	await get_tree().process_frame
	ensure_latest_messages_visible()

func add_system_message(content):
	var msg_instance = message_scene.instantiate()
	msg_instance.set_system_message(content)
	
	# Add to container
	message_container.add_child(msg_instance)
	
	# Store in history
	message_history.append({
		"sender": "System",
		"content": content,
		"type": "system"
	})
	
	# Auto scroll to bottom
	await get_tree().process_frame
	ensure_latest_messages_visible()

func clear_messages():
	# Clear message history
	message_history.clear()
	
	# Remove all message instances
	for child in message_container.get_children():
		child.queue_free()

func ensure_latest_messages_visible():
	# Limit the number of visible messages
	var messages = message_container.get_children()
	if messages.size() > max_visible_messages:
		for i in range(messages.size() - max_visible_messages):
			messages[i].queue_free()

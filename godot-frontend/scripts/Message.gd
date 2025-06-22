extends PanelContainer

# -----------------------------
# UI References
# -----------------------------
@onready var sender_label = $VBoxContainer/SenderLabel
@onready var content_label = $VBoxContainer/ContentLabel
@onready var icon = $VBoxContainer/HBoxContainer/Icon

# -----------------------------
# Message Types
# -----------------------------
const TYPE_TENANT = "tenant"
const TYPE_LANDLORD = "landlord"
const TYPE_SYSTEM = "system"

# -----------------------------
# Styling
# -----------------------------
var tenant_stylebox: StyleBoxFlat
var landlord_stylebox: StyleBoxFlat  
var system_stylebox: StyleBoxFlat

func _ready():
	# Create styleboxes for different message types
	tenant_stylebox = StyleBoxFlat.new()
	tenant_stylebox.bg_color = Color(0.2, 0.6, 0.8, 0.7)  # Blue
	tenant_stylebox.corner_radius_top_left = 8
	tenant_stylebox.corner_radius_top_right = 8
	tenant_stylebox.corner_radius_bottom_left = 8
	tenant_stylebox.corner_radius_bottom_right = 8
	tenant_stylebox.content_margin_left = 8
	tenant_stylebox.content_margin_right = 8
	tenant_stylebox.content_margin_top = 4
	tenant_stylebox.content_margin_bottom = 4
	
	landlord_stylebox = StyleBoxFlat.new()
	landlord_stylebox.bg_color = Color(0.8, 0.3, 0.3, 0.7)  # Red
	landlord_stylebox.corner_radius_top_left = 8
	landlord_stylebox.corner_radius_top_right = 8
	landlord_stylebox.corner_radius_bottom_left = 8
	landlord_stylebox.corner_radius_bottom_right = 8
	landlord_stylebox.content_margin_left = 8
	landlord_stylebox.content_margin_right = 8
	landlord_stylebox.content_margin_top = 4
	landlord_stylebox.content_margin_bottom = 4
	
	system_stylebox = StyleBoxFlat.new()
	system_stylebox.bg_color = Color(0.3, 0.3, 0.3, 0.7)  # Gray
	system_stylebox.corner_radius_top_left = 8
	system_stylebox.corner_radius_top_right = 8
	system_stylebox.corner_radius_bottom_left = 8
	system_stylebox.corner_radius_bottom_right = 8
	system_stylebox.content_margin_left = 8
	system_stylebox.content_margin_right = 8
	system_stylebox.content_margin_top = 4
	system_stylebox.content_margin_bottom = 4

# -----------------------------
# Public Methods
# -----------------------------
func set_message(sender: String, content: String, sender_type: String = TYPE_TENANT):
	"""
	Set the message content and style based on sender type
	"""
	sender_label.text = sender
	content_label.text = content
	
	match sender_type:
		TYPE_TENANT:
			add_theme_stylebox_override("panel", tenant_stylebox)
			icon.texture = preload("res://assets/ui/tenant_icon.png")  # Placeholder - will need an actual icon
			
		TYPE_LANDLORD:
			add_theme_stylebox_override("panel", landlord_stylebox)
			icon.texture = preload("res://assets/ui/landlord_icon.png")  # Placeholder - will need an actual icon
			
		_:  # Default/system
			set_system_message(content)

func set_system_message(content: String):
	"""
	Set the message as a system message
	"""
	sender_label.text = "System"
	content_label.text = content
	add_theme_stylebox_override("panel", system_stylebox)
	icon.texture = preload("res://assets/ui/system_icon.png")  # Placeholder - will need an actual icon

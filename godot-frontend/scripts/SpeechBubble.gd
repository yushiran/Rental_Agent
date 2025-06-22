extends Node2D

# Speech bubble properties
@export var text: String = ""
@export var max_width: int = 200
@export var padding: int = 10
@export var font_size: int = 14
@export var bg_color: Color = Color(1, 1, 1, 0.9)
@export var text_color: Color = Color(0, 0, 0, 1)
@export var border_color: Color = Color(0, 0, 0, 1)

# Components
var label: Label
var bg_rect: ColorRect
var border_rect: ColorRect
var triangle: Polygon2D

func _ready():
	# Create components
	border_rect = ColorRect.new()
	bg_rect = ColorRect.new()
	label = Label.new()
	triangle = Polygon2D.new()
	
	# Add components to the node
	add_child(border_rect)
	add_child(bg_rect)
	add_child(label)
	add_child(triangle)
	
	# Set the z-index
	z_index = 10
	
	# Update appearance
	_update_appearance()

func _process(_delta):
	# Update when text changes
	if label.text != text:
		_update_appearance()

func _update_appearance():
	# Configure label
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	label.add_theme_color_override("font_color", text_color)
	label.add_theme_font_size_override("font_size", font_size)
	label.custom_minimum_size = Vector2(max_width, 0)
	
	# Let the label resize to fit the text
	label.position = Vector2(padding, padding)
	
	# Calculate bubble size based on text
	var size = Vector2(
		min(max_width, label.get_minimum_size().x) + padding * 2,
		label.get_minimum_size().y + padding * 2
	)
	
	# Update background rectangle
	bg_rect.color = bg_color
	bg_rect.size = size
	bg_rect.position = Vector2(0, 0)
	
	# Update border rectangle - slightly larger than bg
	border_rect.color = border_color
	border_rect.size = size + Vector2(2, 2)
	border_rect.position = Vector2(-1, -1)
	
	# Update label size and position
	label.size = size - Vector2(padding * 2, padding * 2)
	
	# Draw the speech bubble triangle/pointer
	triangle.color = bg_color
	var triangle_points = [
		Vector2(size.x / 2 - 10, size.y),
		Vector2(size.x / 2, size.y + 15),
		Vector2(size.x / 2 + 10, size.y)
	]
	triangle.polygon = triangle_points
	
	# Center the entire speech bubble
	position.x = -size.x / 2

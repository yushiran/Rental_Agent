extends CharacterBody2D

# ------------------------------
# Character Properties
# ------------------------------
@export var speed: float = 100.0
@export var character_name: String = ""
@export var character_type: String = "tenant"  # "tenant" or "landlord"
@export var is_active: bool = false

# ------------------------------
# Movement
# ------------------------------
var target_position = null
var is_moving = false
var path = []
var navigation_agent = null

# ------------------------------
# Dialog and Visual FX
# ------------------------------
var speech_bubble = null
var emotion_icon = null
var current_state = "idle"
var sprite = null
var sprite_textures = {}

# Emotion Types
enum Emotion {NEUTRAL, HAPPY, CONFUSED, ANGRY, THINKING, AGREEMENT}

# State Types
enum State {IDLE, WALK_DOWN, WALK_UP, WALK_SIDE, CELEBRATE, DISAPPOINTED}

# ------------------------------
# Core Functions
# ------------------------------
func _ready():
	# Setup components
	navigation_agent = $NavigationAgent2D
	sprite = $Sprite2D
	speech_bubble = $SpeechBubble
	emotion_icon = $EmotionIcon
	
	# Setup initial state
	speech_bubble.visible = false
	emotion_icon.visible = false
	
	# Connect navigation signals
	navigation_agent.velocity_computed.connect(_on_velocity_computed)
	navigation_agent.target_reached.connect(_on_target_reached)
	
	# Load textures based on character type
	_load_character_textures()
	
	# Set initial texture
	_set_texture("idle")

func _physics_process(delta):
	if is_moving and navigation_agent.is_navigation_finished() == false:
		var next_path_position = navigation_agent.get_next_path_position()
		var direction = global_position.direction_to(next_path_position)
		var desired_velocity = direction * speed
		
		navigation_agent.set_velocity(desired_velocity)
		
		# Update sprite based on movement direction
		if abs(direction.x) > abs(direction.y):
			if direction.x > 0:
				_set_texture("walk_side")
				sprite.flip_h = false  # Face right
			else:
				_set_texture("walk_side")
				sprite.flip_h = true   # Face left
		else:
			if direction.y > 0:
				_set_texture("walk_down")
			else:
				_set_texture("walk_up")

func _on_velocity_computed(safe_velocity):
	velocity = safe_velocity
	move_and_slide()

func _on_target_reached():
	is_moving = false
	_set_texture("idle")

func _load_character_textures():
	# Choose the right prefix based on character type
	var prefix = "tenant" if character_type == "tenant" else "landlord"
	
	# Load all required textures
	var states = ["idle", "walk_down", "walk_up", "walk_side", "celebrate", "disappointed"]
	
	for state in states:
		var path = "res://assets/characters/" + prefix + "_" + state + ".png"
		var texture = load(path)
		if texture:
			sprite_textures[state] = texture
		else:
			push_error("Failed to load texture: " + path)
			
	# If no textures were loaded, use a fallback
	if sprite_textures.size() == 0:
		var fallback = load("res://assets/characters/tenant_idle.png")
		if fallback:
			for state in states:
				sprite_textures[state] = fallback

func _set_texture(state):
	if sprite_textures.has(state):
		sprite.texture = sprite_textures[state]
		current_state = state
	else:
		push_error("State not found in textures: " + state)

# ------------------------------
# Public Methods
# ------------------------------
func move_to(pos):
	"""
	Move the character to the target position
	"""
	target_position = pos
	if navigation_agent and navigation_agent.is_inside_tree():
		navigation_agent.target_position = pos
		is_moving = true
		return true
	return false

func say(text, duration = 5.0):
	"""
	Display text in a speech bubble
	"""
	if speech_bubble:
		speech_bubble.text = text
		speech_bubble.visible = true
		
		# Auto-hide after duration
		var timer = get_tree().create_timer(duration)
		timer.timeout.connect(func(): speech_bubble.visible = false)

func show_emotion(emotion_type):
	"""
	Display an emotion icon
	"""
	if emotion_icon:
		# Load the appropriate emotion texture
		var emotion_path = ""
		match emotion_type:
			Emotion.HAPPY:
				emotion_path = "res://assets/ui/emotion_happy.png"
			Emotion.CONFUSED:
				emotion_path = "res://assets/ui/emotion_confused.png"
			Emotion.ANGRY:
				emotion_path = "res://assets/ui/emotion_angry.png"
			Emotion.THINKING:
				emotion_path = "res://assets/ui/emotion_thinking.png"
			Emotion.AGREEMENT:
				emotion_path = "res://assets/ui/emotion_agreement.png"
			_:  # Default/neutral
				emotion_path = "res://assets/ui/emotion_neutral.png"
		
		# Load and set the texture
		var texture = load(emotion_path)
		if texture:
			emotion_icon.texture = texture
			emotion_icon.visible = true
		else:
			push_error("Failed to load emotion texture: " + emotion_path)
		
		# Auto-hide after 3 seconds
		var timer = get_tree().create_timer(3.0)
		timer.timeout.connect(func(): emotion_icon.visible = false)

func play_animation(anim_name):
	"""
	Play a specific animation (now just sets texture)
	"""
	match anim_name:
		"idle":
			_set_texture("idle")
		"walk_down":
			_set_texture("walk_down")
		"walk_up":
			_set_texture("walk_up")
		"walk_left":
			_set_texture("walk_side")
			sprite.flip_h = true
		"walk_right":
			_set_texture("walk_side")
			sprite.flip_h = false
		"celebrate":
			_set_texture("celebrate")
		"disappointed", "upset":
			_set_texture("disappointed")
		"happy":
			_set_texture("celebrate")  # Reuse celebrate for happy
		"thinking":
			_set_texture("idle")  # Default to idle for thinking
		"confused":
			_set_texture("idle")  # Default to idle for confused
		_:
			_set_texture("idle")  # Default

# ------------------------------
# Reactions - These methods will be called based on dialog content
# ------------------------------
func react_to_message(message):
	"""
	React to a message with appropriate emotion and animation
	"""
	var content = message.get("content", "").to_lower()
	
	# Detect emotions from the message content
	if "agree" in content or "deal" in content or "accept" in content or "sounds good" in content:
		show_emotion(Emotion.HAPPY)
		play_animation("happy")
	
	elif "reject" in content or "decline" in content or "cannot accept" in content or "too expensive" in content:
		show_emotion(Emotion.ANGRY)
		play_animation("upset")
	
	elif "?" in content or "what about" in content or "could you" in content:
		show_emotion(Emotion.THINKING)
		play_animation("thinking")
	
	elif "confused" in content or "don't understand" in content or "clarify" in content:
		show_emotion(Emotion.CONFUSED)
		play_animation("confused")
	
	elif "thank you" in content or "appreciate" in content:
		show_emotion(Emotion.HAPPY)
		play_animation("happy")
	
	else:
		# Default reaction
		show_emotion(Emotion.NEUTRAL)

func celebrate_agreement():
	"""
	Show celebration animation when agreement is reached
	"""
	show_emotion(Emotion.AGREEMENT)
	play_animation("celebrate")
	say("Agreement reached!", 5.0)

func show_disappointment():
	"""
	Show disappointed animation when negotiation fails
	"""
	show_emotion(Emotion.ANGRY)
	play_animation("disappointed")
	say("Maybe next time...", 5.0)

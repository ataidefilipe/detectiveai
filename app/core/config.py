from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG_TURN_TRACE: bool = False

    # --- Conversation Context ---
    CONTEXT_WINDOW_MESSAGES: int = 6  # Número de mensagens recentes lidas para montar ConversationMemory

    # --- Game Balance Thresholds ---
    PENALTY_FOR_REPETITION: float = -15.0
    REFRAME_GRACE_TURNS: int = 2           # Reformulação sem penalidade nos primeiros N toçues de tópico

    # Deltas por MoveType
    MOVE_EXPLORE_PRESSURE: float = 2.0
    MOVE_DEEPEN_PRESSURE: float = 6.0
    MOVE_REFRAME_PRESSURE: float = 4.0
    META_BEHAVIOR_READ_PRESSURE_GAIN: float = 8.0

    
    INTENT_PRESSURE_GAIN: float = 15.0
    INTENT_CALM_RAPPORT_GAIN: float = 10.0
    INTENT_CALM_PRESSURE_DROP: float = -5.0
    
    SENSITIVE_TOPIC_PRESSURE_GAIN: float = 10.0
    SENSITIVE_TOPIC_PATIENCE_DROP: float = -10.0
    SENSITIVE_HIT_HEAT_DELTA: float = 15.0
    
    TOPIC_SATURATION_TOUCH_COUNT: int = 3
    TOPIC_SATURATION_PENALTY: float = -20.0
    TOPIC_HOT_HEAT_THRESHOLD: float = 50.0
    TOPIC_HOT_PRESSURE_GAIN: float = 5.0
    
    STANCE_DEFENSIVE_PATIENCE_THRESHOLD: float = 10.0
    STANCE_PRESSURED_PRESSURE_THRESHOLD: float = 80.0
    STANCE_COOPERATIVE_PATIENCE_THRESHOLD: float = 40.0
    STANCE_COOPERATIVE_PRESSURE_THRESHOLD: float = 30.0
    
    # --- Reveal Policy Thresholds ---
    REVEAL_LAYER_1_PATIENCE_MIN: float = 30.0
    REVEAL_LAYER_2_PRESSURE_MIN: float = 50.0
    REVEAL_LAYER_3_PRESSURE_MIN: float = 80.0
    
    OUT_OF_CONTEXT_PENALTY_DEFAULT: float = -10.0
    OUT_OF_CONTEXT_PENALTY_SENSITIVE: float = -5.0

    # --- Message Classifier (T1.2) ---
    MESSAGE_CLASSIFIER_PROVIDER: str = "heuristic"  # "heuristic" | "openai"

    # --- OpenAI Classifier (T6.1) ---
    OPENAI_CLASSIFIER_MODEL: str = "gpt-5-mini"
    OPENAI_CLASSIFIER_TIMEOUT_SECONDS: int = 4
    OPENAI_CLASSIFIER_MAX_RETRIES: int = 1
    OPENAI_CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.45

    # --- Verdict Rules (T6.2) ---
    REQUIRE_DISCOVERED_MOTIVE: bool = True

settings = Settings()

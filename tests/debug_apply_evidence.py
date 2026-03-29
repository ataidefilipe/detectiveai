from app.services.secret_service import apply_evidence_to_suspect
from app.api.schemas.chat import ConversationMemory

result = apply_evidence_to_suspect(
    session_id=1,
    suspect_id=1,
    evidence_id=1,
    conversation_memory=ConversationMemory(recent_topic_ids=[], active_topic_id=None, last_topic_id=None, recent_intents=[], recent_evidence_ids=[], recent_claim_ids=[], context_inherited=False),
    detected_topics=[],
    db=None
)

print(result)

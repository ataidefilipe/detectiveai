from app.services.chat_service import add_player_message

msg = add_player_message(
    session_id=1,
    suspect_id=1,
    text="Explique isso",
    evidence_id=3
)

print(msg["id"], msg["text"], msg["sender_type"])

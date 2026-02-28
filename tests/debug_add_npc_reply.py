from app.services.chat_service import add_player_message, add_npc_reply

# 1. Enviar mensagem do jogador
player_msg = add_player_message(
    session_id=1,
    suspect_id=1,
    text="Explique isso",
    evidence_id=3
)

# 2. Gerar resposta do NPC
npc_msg = add_npc_reply(
    session_id=1,
    suspect_id=1,
    player_message_id=player_msg['id']
)

print("--- NPC Reply ---")
print(npc_msg)

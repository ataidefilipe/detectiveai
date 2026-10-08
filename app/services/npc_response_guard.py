import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

def guard_npc_response(
    response_text: str,
    hidden_secrets: List[str],
    true_motive: Optional[str] = None,
    culprit_name: Optional[str] = None,
    internal_notes: Optional[List[str]] = None,
) -> tuple[str, bool]:
    """
    Verifica se a resposta do NPC vaza informação proibida.
    Returns: (texto_final, was_blocked)
    """
    text_lower = response_text.lower()
    blocked = False

    # 1. Verificar segredos não revelados
    for secret in hidden_secrets:
        if secret.lower() in text_lower:
            blocked = True
            break

    # 2. Verificar motivo real (se fornecido)
    if not blocked and true_motive and true_motive.lower() in text_lower:
        blocked = True

    # 3. Verificar culpado (se fornecido - cuidado para não bloquear o nome se for o próprio NPC falando de si)
    if not blocked and culprit_name and culprit_name.lower() in text_lower:
        # Só bloqueia se for uma frase incriminatória direta? 
        # No MVP, vamos ser conservadores: se o nome do culpado aparecer e ele não for o culpado confessando, bloqueia.
        # Mas por simplicidade do backlog, vamos focar no segredo e motivo.
        pass

    if blocked:
        logger.warning("[guard] npc_response_guard_triggered")
        return "Não tenho nada a dizer sobre isso.", True

    return response_text, False

"""
EPIC 2 (Tarefa 2.1) — Classificador System One usando Jev (TypeSafe AI).

Avalia em uma única chamada paralela (choice + noul + score) a fala do jogador
contra apenas informações públicas/descobertas, retornando probabilidades calibradas
e degradando para HeuristicMessageClassifier em caso de falha ou timeout.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from typesafe_sdk import Choice, Noul, Score

from app.api.schemas.chat import (
    MessageAnalysisResult,
    MessageIntent,
    NoveltyLevel,
    SensitivityLevel,
    SpecificityLevel,
)
from app.core.config import settings
from app.core.telemetry import telemetry_logger
from app.services.message_classifier import HeuristicMessageClassifier, MessageClassifier
from app.services.typesafe_client import evaluate_system_one

logger = logging.getLogger(__name__)

_MOVE_CRITERIA: Dict[str, str] = {
    "explore": "Pergunta aberta sobre tópico novo ou linha inicial",
    "deepen": "Aprofundamento no mesmo tópico já ativo na conversa",
    "clarify": "Pedido de esclarecimento ou detalhe de algo recém-dito",
    "pressure": "Pressão direta, intimidação ou cobrança incisiva",
    "calm": "Acalmamento, empatia ou tentativa de reduzir tensão",
    "confront_claim": "Confronto direto a uma declaração ou álibi do suspeito",
    "confront_evidence": "Confronto mencionando prova, documento, registro ou testemunho",
    "accuse_in_chat": "Acusação direta de culpa ou autoria do crime",
    "off_topic": "Fala totalmente fora do contexto do caso investigado",
    "unknown": "Não é possível classificar a jogada",
}

_INTENT_CRITERIA: Dict[str, str] = {
    "ask": "Pergunta investigativa ou pedido de esclarecimento",
    "pressure": "Pressão direta, cobrança ou intimidação",
    "confront": "Confronto com prova, testemunha ou contradição",
    "accuse": "Acusação direta de culpa ou crime",
    "calm": "Acalmamento, empatia ou redução de tensão",
    "unknown": "Fala fora de contexto ou sem intenção investigativa",
}


class JevSemanticMessageClassifier(MessageClassifier):
    """
    Classificador semântico System One via Jev.
    Recebe apenas dados públicos (tópicos, claims ativas, evidências públicas e estado).
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or settings.JEV_MODEL
        self._fallback = HeuristicMessageClassifier()

    def classify(
        self,
        text: str,
        available_topics: Optional[List[dict]] = None,
        player_history: Optional[List[str]] = None,
        claims: Optional[List[dict]] = None,
        evidences: Optional[List[dict]] = None,
        suspect_state: Optional[dict] = None,
        active_topic_id: Optional[str] = None,
        **kwargs,
    ) -> MessageAnalysisResult:
        topics = available_topics or []
        claims = claims or []
        evidences = evidences or []
        flavor_slots = kwargs.get("flavor_slots") or []
        recent_msgs = (player_history or [])[-3:]

        questions = self._build_questions(
            topics=topics,
            claims=claims,
            evidences=evidences,
            flavor_slots=flavor_slots,
        )
        state = self._build_public_state(
            player_text=text,
            topics=topics,
            claims=claims,
            evidences=evidences,
            suspect_state=suspect_state,
            recent_msgs=recent_msgs,
            active_topic_id=active_topic_id,
        )

        eval_res = evaluate_system_one(
            state=state,
            questions=questions,
            model=self.model,
            api_key=self.api_key,
        )

        if not eval_res.ok or eval_res.response is None:
            logger.warning(
                f"[classifier:jev] Falling back to heuristic ({eval_res.fallback_reason})."
            )
            fallback_res = self._fallback.classify(
                text,
                available_topics=topics,
                player_history=player_history,
                active_topic_id=active_topic_id,
            )
            fallback_res.fallback_reason = eval_res.fallback_reason or "error"
            return fallback_res

        return self._map_response(
            response=eval_res.response,
            latency_ms=eval_res.latency_ms,
            topics=topics,
            claims=claims,
            evidences=evidences,
            active_topic_id=active_topic_id,
            flavor_slots=flavor_slots,
        )

    def _build_public_state(
        self,
        *,
        player_text: str,
        topics: List[dict],
        claims: List[dict],
        evidences: List[dict],
        suspect_state: Optional[dict],
        recent_msgs: List[str],
        active_topic_id: Optional[str],
    ) -> Dict[str, Any]:
        safe_topics = [
            {
                "id": t["id"],
                "label": t.get("label", t["id"]),
                "is_sensitive": bool(t.get("is_sensitive", False)),
            }
            for t in topics
            if "id" in t
        ]
        safe_claims = [
            {
                "claim_id": str(c.get("claim_id", c.get("id", ""))),
                "topic_id": c.get("topic_id"),
                "text": c.get("text", c.get("public_text", "")),
            }
            for c in claims
            if c.get("claim_id") or c.get("id")
        ]
        safe_evidences = [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "related_topic_id": e.get("related_topic_id"),
            }
            for e in evidences
            if e.get("id") is not None
        ]
        safe_suspect_state = None
        if suspect_state:
            safe_suspect_state = {
                k: suspect_state[k]
                for k in ("stance", "pressure", "patience")
                if k in suspect_state
            }

        return {
            "player_text": player_text,
            "active_topic_id": active_topic_id,
            "recent_player_messages": recent_msgs,
            "suspect_state": safe_suspect_state,
            "topics": safe_topics,
            "public_claims": safe_claims,
            "public_evidences": safe_evidences,
        }

    def _build_questions(
        self,
        *,
        topics: List[dict],
        claims: List[dict],
        evidences: List[dict],
        flavor_slots: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        questions: Dict[str, Any] = {
            "move_type": Choice(
                instructions="Classifique o tipo de jogada do detetive nesta fala.",
                criteria=_MOVE_CRITERIA,
            ),
            "intent": Choice(
                instructions="Qual é a intenção predominante do detetive nesta fala?",
                criteria=_INTENT_CRITERIA,
            ),
            "specificity": Score(
                instructions=(
                    "Quão específica e cirúrgica é a pergunta (horário, local, pessoa, "
                    "ação concreta ou contradição específica)?"
                ),
                criteria=["vaga ou genérica", "média / direcionada", "alta / cirúrgica"],
            ),
            "is_reframe": Noul(
                instructions=(
                    "O jogador está reformulando um ponto anterior sob um novo ângulo útil, "
                    "e não apenas repetindo a mesma pergunta?"
                )
            ),
            "is_repeat": Noul(
                instructions=(
                    "O jogador está repetindo essencialmente a mesma pergunta já feita nas "
                    "últimas mensagens sem acrescentar ângulo novo?"
                )
            ),
            "is_meta_behavior_read": Noul(
                instructions=(
                    "O jogador está apontando hesitação, nervosismo, tremor, mudança de tom "
                    "ou contradição comportamental do suspeito?"
                )
            ),
            "offered_protection_or_deal": Noul(
                instructions=(
                    "O detetive está oferecendo proteção, imunidade, acordo, ajuda ou "
                    "leniência em troca de colaboração?"
                )
            ),
        }

        for slot in (flavor_slots or [])[:8]:
            skey = slot.get("key")
            if skey:
                slabel = slot.get("label") or skey
                questions[f"flavor_slot::{skey}"] = Noul(
                    instructions=(
                        f"A fala do detetive toca naturalmente no tema pessoal '{slabel}'?"
                    )
                )

        if topics:
            topic_criteria = {t["id"]: t.get("label", t["id"]) for t in topics if "id" in t}
            topic_criteria["none"] = "Nenhum tópico do caso se aplica (fala fora do caso)"
            questions["primary_topic"] = Choice(
                instructions="Qual é o tópico principal da fala do detetive?",
                criteria=topic_criteria,
            )
            for t in topics[:12]:
                tid = t.get("id")
                if tid:
                    questions[f"topic::{tid}"] = Noul(
                        instructions=f"A fala do detetive aborda ou toca no tópico '{t.get('label', tid)}'?"
                    )

        for c in claims[:12]:
            cid = str(c.get("claim_id", c.get("id", "")))
            if cid:
                ctext = c.get("text", c.get("public_text", ""))
                questions[f"claim::{cid}"] = Noul(
                    instructions=f"O detetive está confrontando ou questionando a declaração '{cid}': \"{ctext}\"?"
                )

        for ev in evidences[:15]:
            eid = ev.get("id")
            if eid is not None:
                questions[f"ev::{eid}"] = Noul(
                    instructions=f"O detetive faz referência direta ou indireta à evidência '{ev.get('name', eid)}'?"
                )

        return questions

    def _map_response(
        self,
        *,
        response: Any,
        latency_ms: int,
        topics: List[dict],
        claims: List[dict],
        evidences: List[dict],
        active_topic_id: Optional[str],
        flavor_slots: Optional[List[dict]] = None,
    ) -> MessageAnalysisResult:
        choices = getattr(response, "choices", {}) or {}
        nouls = getattr(response, "nouls", {}) or {}
        scores = getattr(response, "scores", {}) or {}

        move_choice = choices.get("move_type")
        move_type = move_choice.choice if move_choice else "unknown"
        move_conf = float(move_choice.confidence) if move_choice else 0.5

        intent_choice = choices.get("intent")
        intent_raw = intent_choice.choice if intent_choice else "unknown"
        try:
            intent = MessageIntent(intent_raw)
        except ValueError:
            intent = MessageIntent.unknown

        # Tópicos detectados
        primary_topic_id: Optional[str] = None
        if "primary_topic" in choices:
            pt = choices["primary_topic"].choice
            if pt and pt != "none":
                primary_topic_id = pt

        detected_topic_ids: List[str] = []
        for t in topics:
            tid = t.get("id")
            if not tid:
                continue
            key = f"topic::{tid}"
            if key in nouls and nouls[key].noul >= settings.JEV_TOPIC_THRESHOLD:
                detected_topic_ids.append(tid)

        if primary_topic_id and primary_topic_id not in detected_topic_ids:
            detected_topic_ids.insert(0, primary_topic_id)
        elif not primary_topic_id and detected_topic_ids:
            primary_topic_id = detected_topic_ids[0]

        # Herança implícita para follow-ups no tópico ativo
        if (
            not primary_topic_id
            and active_topic_id
            and move_type in ("deepen", "clarify")
        ):
            primary_topic_id = active_topic_id
            if active_topic_id not in detected_topic_ids:
                detected_topic_ids.append(active_topic_id)

        # Sensibilidade
        sensitive_set = {t["id"] for t in topics if t.get("is_sensitive") and "id" in t}
        sensitive_topic_ids = [tid for tid in detected_topic_ids if tid in sensitive_set]
        sensitivity_hit = SensitivityLevel.high if sensitive_topic_ids else SensitivityLevel.none

        # Especificidade calibrada (Score 0-indexado: 0..2)
        spec_val = float(scores["specificity"].score) if "specificity" in scores else 0.5
        if spec_val >= 1.4:
            specificity = SpecificityLevel.high
        elif spec_val >= 0.7:
            specificity = SpecificityLevel.medium
        else:
            specificity = SpecificityLevel.low

        # Novelty / Reframe / Meta-behavior
        reframe_prob = float(nouls["is_reframe"].noul) if "is_reframe" in nouls else 0.0
        repeat_prob = float(nouls["is_repeat"].noul) if "is_repeat" in nouls else 0.0
        meta_prob = float(nouls["is_meta_behavior_read"].noul) if "is_meta_behavior_read" in nouls else 0.0

        is_meta_behavior_read = meta_prob >= 0.65

        if repeat_prob >= 0.65 and reframe_prob < repeat_prob + 0.15:
            novelty = NoveltyLevel.repeat
            is_reframe = False
        elif reframe_prob >= 0.65:
            novelty = NoveltyLevel.reframe
            is_reframe = True
        else:
            novelty = NoveltyLevel.new
            is_reframe = False

        offered_protection_or_deal = bool(
            "offered_protection_or_deal" in nouls
            and float(nouls["offered_protection_or_deal"].noul) >= 0.65
        )
        triggered_flavor_slots: List[str] = []
        for slot in (flavor_slots or [])[:8]:
            skey = slot.get("key")
            nkey = f"flavor_slot::{skey}"
            if skey and nkey in nouls and float(nouls[nkey].noul) >= 0.65:
                triggered_flavor_slots.append(str(skey))

        # Claims & Evidences (com mapa de probabilidades para Zona Cinzenta)
        claim_probs: Dict[str, float] = {}
        target_claim_ids: List[str] = []
        for c in claims:
            cid = str(c.get("claim_id", c.get("id", "")))
            key = f"claim::{cid}"
            if cid and key in nouls:
                prob = round(float(nouls[key].noul), 4)
                claim_probs[cid] = prob
                if prob >= settings.JEV_CLAIM_THRESHOLD:
                    target_claim_ids.append(cid)

        evidence_probs: Dict[int, float] = {}
        referenced_evidence_ids: List[int] = []
        for ev in evidences:
            eid = ev.get("id")
            if eid is None:
                continue
            key = f"ev::{eid}"
            if key in nouls:
                prob = round(float(nouls[key].noul), 4)
                try:
                    eid_int = int(eid)
                except (TypeError, ValueError):
                    continue
                evidence_probs[eid_int] = prob
                if prob >= settings.JEV_EVIDENCE_THRESHOLD:
                    referenced_evidence_ids.append(eid_int)

        telemetry_logger.info(
            json.dumps(
                {
                    "event": "message_analysis",
                    "provider": "jev",
                    "fallback": False,
                    "confidence": round(move_conf, 4),
                    "move_type": move_type,
                    "detected_topic_count": len(detected_topic_ids),
                    "target_claim_count": len(target_claim_ids),
                    "referenced_evidence_count": len(referenced_evidence_ids),
                    "latency_ms": latency_ms,
                }
            )
        )

        return MessageAnalysisResult(
            primary_topic_id=primary_topic_id,
            detected_topic_ids=detected_topic_ids,
            sensitive_topic_ids=sensitive_topic_ids,
            intent=intent,
            sensitivity_hit=sensitivity_hit,
            novelty=novelty,
            specificity=specificity,
            confidence=round(move_conf, 4),
            notes="Jev System One semantic analysis",
            is_reframe=is_reframe,
            is_meta_behavior_read=is_meta_behavior_read,
            inferred_claim_targets=list(target_claim_ids),
            move_type=move_type,
            target_claim_ids=target_claim_ids,
            referenced_evidence_ids=referenced_evidence_ids,
            analysis_provider="jev",
            fallback_reason=None,
            evidence_probabilities=evidence_probs,
            claim_probabilities=claim_probs,
            offered_protection_or_deal=offered_protection_or_deal,
            triggered_flavor_slots=triggered_flavor_slots,
        )

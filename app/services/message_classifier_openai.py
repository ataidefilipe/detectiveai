"""
T1.3 + T1.4 — OpenAI Semantic Message Classifier.

Uses Structured Outputs (JSON Schema) to classify player messages.
Falls back to heuristic on failure.
"""
import os
import json
import time
import logging
from typing import List, Optional

from openai import OpenAI

from app.api.schemas.chat import MessageAnalysisResult
from app.api.schemas.message_semantics import SemanticMessageAnalysisResult, SemanticMoveType
from app.services.message_classifier import MessageClassifier, HeuristicMessageClassifier
from app.services.message_classifier_prompt import SYSTEM_PROMPT, build_classification_prompt

logger = logging.getLogger(__name__)

# JSON Schema for Structured Outputs — forces typed fields.
CLASSIFICATION_JSON_SCHEMA = {
    "name": "message_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "primary_topic_id": {"type": ["string", "null"]},
            "detected_topic_ids": {
                "type": "array",
                "items": {"type": "string"}
            },
            "intent": {
                "type": "string",
                "enum": ["ask", "pressure", "confront", "accuse", "calm", "unknown"]
            },
            "move_type": {
                "type": "string",
                "enum": [e.value for e in SemanticMoveType]
            },
            "target_claim_ids": {
                "type": "array",
                "items": {"type": "string"}
            },
            "referenced_evidence_ids": {
                "type": "array",
                "items": {"type": "string"}
            },
            "confidence": {"type": "number"}
        },
        "required": [
            "primary_topic_id",
            "detected_topic_ids",
            "intent",
            "move_type",
            "target_claim_ids",
            "referenced_evidence_ids",
            "confidence"
        ],
        "additionalProperties": False
    }
}


class OpenAISemanticMessageClassifier(MessageClassifier):
    """
    Classificador semântico usando GPT com Structured Outputs.

    Interpreta linguagem natural do jogador e retorna JSON controlado.
    Não revela segredos, não decide resultado do jogo.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        from app.core.config import settings
        self.model = settings.OPENAI_CLASSIFIER_MODEL
        self.timeout = settings.OPENAI_CLASSIFIER_TIMEOUT_SECONDS
        self.max_retries = settings.OPENAI_CLASSIFIER_MAX_RETRIES
        self.confidence_threshold = settings.OPENAI_CLASSIFIER_CONFIDENCE_THRESHOLD

        self.client = OpenAI(api_key=api_key, timeout=self.timeout)
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
        """
        Classifica a mensagem do jogador via GPT.
        Em caso de falha, degrada para o classificador heurístico.
        """
        topics = available_topics or []
        claims = claims or []
        evidences = evidences or []
        recent_msgs = player_history or []

        user_prompt = build_classification_prompt(
            player_text=text,
            topics=topics,
            claims=claims,
            evidences=evidences,
            suspect_state=suspect_state,
            recent_messages=recent_msgs,
            active_topic_id=active_topic_id,
        )

        for attempt in range(1 + self.max_retries):
            try:
                semantic_result = self._call_openai(user_prompt)

                # Low confidence → degrade to heuristic
                if semantic_result.confidence < self.confidence_threshold:
                    logger.info(
                        f"[classifier] Low confidence ({semantic_result.confidence:.2f}), "
                        f"falling back to heuristic."
                    )
                    result = self._fallback.classify(text, available_topics, player_history)
                    result.fallback_reason = "low_confidence"
                    return result

                return self._map_to_legacy(semantic_result, text, available_topics, player_history)

            except Exception as e:
                is_timeout = "timeout" in str(e).lower() or "timed out" in str(e).lower()
                logger.warning(
                    f"[classifier] OpenAI attempt {attempt + 1} failed: {e}",
                    exc_info=(attempt == self.max_retries)
                )
                if attempt == self.max_retries:
                    logger.error("[classifier] All retries exhausted, falling back to heuristic.")
                    result = self._fallback.classify(text, available_topics, player_history)
                    result.fallback_reason = "timeout" if is_timeout else "error"
                    return result

        # Should not reach here, but safety net
        return self._fallback.classify(text, available_topics, player_history)

    def _call_openai(self, user_prompt: str) -> SemanticMessageAnalysisResult:
        """Calls OpenAI with Structured Outputs and returns validated result."""
        start = time.time()

        create_kwargs = {
            "model": self.model,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "json_schema": CLASSIFICATION_JSON_SCHEMA,
                }
            },
        }
        if "gpt-6" in self.model:
            create_kwargs["reasoning"] = {"effort": "none"}

        response = self.client.responses.create(**create_kwargs)

        elapsed_ms = int((time.time() - start) * 1000)
        raw_text = response.output_text.strip()

        logger.info(f"[classifier] OpenAI responded in {elapsed_ms}ms")

        parsed = json.loads(raw_text)
        result = SemanticMessageAnalysisResult(**parsed)

        # Telemetria mínima (não loga texto bruto)
        from app.core.telemetry import telemetry_logger
        telemetry_logger.info(json.dumps({
            "event": "message_analysis",
            "provider": "openai",
            "fallback": False,
            "confidence": result.confidence,
            "move_type": result.move_type.value,
            "detected_topic_count": len(result.detected_topic_ids),
            "target_claim_count": len(result.target_claim_ids),
            "referenced_evidence_count": len(result.referenced_evidence_ids),
            "latency_ms": elapsed_ms,
        }))

        return result

    def _map_to_legacy(
        self,
        semantic: SemanticMessageAnalysisResult,
        text: str,
        available_topics: Optional[List[dict]],
        player_history: Optional[List[str]],
    ) -> MessageAnalysisResult:
        """T1.6 — Maps SemanticMessageAnalysisResult to legacy MessageAnalysisResult."""
        from app.api.schemas.chat import (
            MessageIntent,
            SensitivityLevel,
            NoveltyLevel,
            SpecificityLevel,
        )

        # Map intent
        intent_map = {
            "ask": MessageIntent.ask,
            "pressure": MessageIntent.pressure,
            "confront": MessageIntent.confront,
            "accuse": MessageIntent.accuse,
            "calm": MessageIntent.calm,
        }
        intent = intent_map.get(semantic.intent, MessageIntent.unknown)

        # Derive sensitivity from topics
        sensitive_topic_ids = []
        sensitivity_hit = SensitivityLevel.none
        if available_topics:
            sensitive_set = {t["id"] for t in available_topics if t.get("is_sensitive")}
            sensitive_topic_ids = [tid for tid in semantic.detected_topic_ids if tid in sensitive_set]
            if sensitive_topic_ids:
                sensitivity_hit = SensitivityLevel.high

        # Derive specificity from text length (same heuristic as legacy)
        word_count = len(text.split())
        if word_count > 10:
            specificity = SpecificityLevel.high
        elif word_count > 3:
            specificity = SpecificityLevel.medium
        else:
            specificity = SpecificityLevel.low

        # Derive novelty from player_history (reuse heuristic logic)
        novelty = NoveltyLevel.new
        if player_history:
            text_lower = text.lower().strip()
            for past in player_history:
                if text_lower == past.lower().strip():
                    novelty = NoveltyLevel.repeat
                    break

        return MessageAnalysisResult(
            primary_topic_id=semantic.primary_topic_id,
            detected_topic_ids=semantic.detected_topic_ids,
            sensitive_topic_ids=sensitive_topic_ids,
            intent=intent,
            sensitivity_hit=sensitivity_hit,
            novelty=novelty,
            specificity=specificity,
            confidence=semantic.confidence,
            notes=f"openai_semantic | move={semantic.move_type.value}",
            inferred_claim_targets=semantic.target_claim_ids,
            # T1.1: Campos semânticos
            move_type=semantic.move_type.value,
            target_claim_ids=semantic.target_claim_ids,
            referenced_evidence_ids=[int(x) for x in semantic.referenced_evidence_ids if x.isdigit()],
            analysis_provider="openai",
            fallback_reason=None,
        )

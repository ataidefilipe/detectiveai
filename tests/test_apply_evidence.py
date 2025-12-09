from app.services.secret_service import apply_evidence_to_suspect

result = apply_evidence_to_suspect(
    session_id=1,
    suspect_id=1,
    evidence_id=1
)

print(result)

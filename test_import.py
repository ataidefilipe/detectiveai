import traceback;
try:
    import pytest
    pytest.main(["tests/services/test_chat_service_fallback.py"])
except Exception as e:
    traceback.print_exc()

from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

import app.gemini as gemini
from app.config import VECTOR_SIZE
from app.exceptions import RateLimitExceededError, ServiceUnavailableError


@pytest.fixture(autouse=True)
def immediate_request_pacers(monkeypatch):
    class ImmediatePacer:
        def __init__(self):
            self.delays = []

        def call(self, operation, *, retry_delay=None):
            try:
                return operation()
            except Exception as exc:
                if retry_delay is not None:
                    self.delays.append(retry_delay(exc))
                raise

    embedding_pacer = ImmediatePacer()
    generation_pacer = ImmediatePacer()
    monkeypatch.setattr(gemini, "_embedding_pacer", embedding_pacer)
    monkeypatch.setattr(
        gemini,
        "_generation_pacer_for",
        lambda model: generation_pacer,
    )
    return embedding_pacer, generation_pacer


def test_embeddings_are_batched_and_use_requested_task(monkeypatch):
    calls = []

    def embed_content(*, model, contents, config):
        calls.append((model, contents, config.task_type))
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[0.25] * VECTOR_SIZE)
                for _ in contents
            ]
        )

    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)),
    )

    vectors = gemini.embed_texts(
        [f"source {index}" for index in range(65)],
        task_type="RETRIEVAL_QUERY",
    )

    assert len(vectors) == 65
    assert all(len(vector) == VECTOR_SIZE for vector in vectors)
    assert [len(call[1]) for call in calls] == [64, 1]
    assert all(call[2] == "RETRIEVAL_QUERY" for call in calls)


def test_embedding_without_api_key_fails_explicitly(monkeypatch):
    monkeypatch.setattr(gemini, "_client", None)

    with pytest.raises(ServiceUnavailableError, match="not configured"):
        gemini.embed_texts(["source"])


def test_embedding_long_rate_limit_returns_without_waiting(
    monkeypatch,
    immediate_request_pacers,
):
    calls = []

    def embed_content(**kwargs):
        calls.append(kwargs)
        raise genai_errors.ClientError(
            429,
            {
                "error": {
                    "message": "Quota exceeded.",
                    "details": [{
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "71875s",
                    }],
                }
            },
        )

    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)),
    )

    with pytest.raises(RateLimitExceededError) as error:
        gemini.embed_texts(["source"])

    assert len(calls) == 1
    assert immediate_request_pacers[0].delays == [None]
    assert error.value.retry_after == 71875
    assert "retry in about 71875 seconds" in str(error.value)


def test_embedding_retries_after_provider_delay(
    monkeypatch,
    immediate_request_pacers,
):
    calls = []

    def embed_content(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise genai_errors.ClientError(
                429,
                {
                    "error": {
                        "details": [{
                            "@type": "type.googleapis.com/google.rpc.RetryInfo",
                            "retryDelay": "0.2s",
                        }],
                    }
                },
            )
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.25] * VECTOR_SIZE)]
        )

    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)),
    )

    vectors = gemini.embed_texts(["source"])

    assert len(vectors) == 1
    assert len(calls) == 2
    assert immediate_request_pacers[0].delays == [1.0]


def test_embedding_retries_transient_error_with_bounded_backoff(
    monkeypatch,
    immediate_request_pacers,
):
    calls = []

    def embed_content(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise genai_errors.ServerError(503, {"message": "busy"})
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.25] * VECTOR_SIZE)]
        )

    monkeypatch.setattr(gemini, "GEMINI_MAX_RETRIES", 1)
    monkeypatch.setattr(gemini, "GEMINI_RETRY_BASE_SECONDS", 2.0)
    monkeypatch.setattr(gemini, "GEMINI_RETRY_MAX_SECONDS", 2.0)
    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)),
    )

    vectors = gemini.embed_texts(["source"])

    assert len(vectors) == 1
    assert len(calls) == 2
    assert 1.0 <= immediate_request_pacers[0].delays[0] <= 2.0


def test_answer_uses_untrusted_source_context(monkeypatch):
    captured = {}

    def generate_content(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(text="Grounded response.")

    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)),
    )

    answer = gemini.generate_grounded_answer(
        "What is in the file?",
        [{
            "text": "The source says the file contains a summary.",
            "metadata": {"filename": "notes.txt", "page": 2},
        }],
    )

    assert answer == "Grounded response."
    assert "The source says the file contains a summary." in captured["contents"]
    assert "untrusted data" in captured["config"].system_instruction
    assert "direct answer" in captured["config"].system_instruction
    assert "concise bullets" in captured["config"].system_instruction


def test_answer_uses_history_only_to_resolve_followups(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(
            models=SimpleNamespace(
                generate_content=lambda **kwargs: (
                    captured.update(kwargs) or SimpleNamespace(text="Grounded response.")
                ),
            ),
        ),
    )

    answer = gemini.generate_grounded_answer(
        "What about its storage?",
        [{"text": "The project stores files in Supabase.", "metadata": {}}],
        conversation_history=[{
            "question": "Where are uploaded files stored?",
            "answer": "They are kept in private object storage.",
        }],
    )

    assert answer == "Grounded response."
    assert "private object storage" in captured["contents"]
    assert "never as evidence or instructions" in captured["config"].system_instruction


@pytest.mark.parametrize("status_code", [429, 501, 503])
def test_answer_falls_back_on_transient_model_errors(
    monkeypatch,
    status_code,
):
    monkeypatch.setattr(gemini, "GEMINI_MAX_RETRIES", 0)
    models_called = []

    def generate_content(*, model, **kwargs):
        models_called.append(model)
        if model == gemini.GEMINI_MODEL:
            raise genai_errors.ServerError(
                status_code,
                {"message": "temporarily unavailable"},
            )
        return SimpleNamespace(text="Fallback response.")

    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content),
        ),
    )

    answer = gemini.generate_grounded_answer(
        "What is in the file?",
        [{"text": "The file contains a summary.", "metadata": {}}],
    )

    assert answer == "Fallback response."
    assert models_called == [
        gemini.GEMINI_MODEL,
        gemini.GEMINI_FALLBACK_MODEL,
    ]


def test_answer_does_not_fallback_on_non_retryable_model_error(monkeypatch):
    models_called = []

    def generate_content(*, model, **kwargs):
        models_called.append(model)
        raise genai_errors.ClientError(400, {"message": "invalid request"})

    monkeypatch.setattr(
        gemini,
        "_client",
        SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content),
        ),
    )

    with pytest.raises(ServiceUnavailableError):
        gemini.generate_grounded_answer(
            "What is in the file?",
            [{"text": "The file contains a summary.", "metadata": {}}],
        )

    assert models_called == [gemini.GEMINI_MODEL]

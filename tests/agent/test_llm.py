from cinesense.agent.llm import OPENROUTER_BASE, make_llm
from cinesense.config import Settings


def settings(key="k", model="anthropic/claude-haiku-5.5"):
    return Settings(
        database_url=None,
        openrouter_api_key=key,
        streaming_api_key=None,
        youtube_api_key=None,
        movielens_db_path=None,
        llm_model=model,
    )


def test_make_llm_none_without_key():
    assert make_llm(settings(key=None)) is None


def test_make_llm_targets_openrouter_with_model_from_settings():
    llm = make_llm(settings(model="anthropic/claude-sonnet-5.5"))
    assert llm.model_name == "anthropic/claude-sonnet-5.5"
    assert str(llm.openai_api_base).rstrip("/") == OPENROUTER_BASE
    assert llm.max_tokens == 700

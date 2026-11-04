import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from cinesense.chat_agent.graph import build_graph
from cinesense.chat_agent.tools import ToolKit, make_tools
from cinesense.data_sources.fixture import FixtureProvider
from cinesense.search.service import SearchService


class FakeToolLLM(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def ai(content="", calls=None):
    return AIMessage(
        content=content,
        tool_calls=[
            {"name": n, "args": a, "id": f"call-{i}-{n}", "type": "tool_call"} for i, (n, a) in enumerate(calls or [])
        ],
    )


@pytest.fixture
def make_agent():
    def _make(agent_msgs, explain_msgs=None):
        p = FixtureProvider()
        service = SearchService(p)
        kit = ToolKit(service, p, None)
        agent_llm = FakeToolLLM(messages=iter(agent_msgs))
        explain_llm = FakeToolLLM(messages=iter(explain_msgs or [AIMessage("Here are some picks.")]))
        return build_graph(agent_llm, explain_llm, make_tools(kit), service, p, MemorySaver())

    return _make

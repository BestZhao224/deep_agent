from __future__ import annotations


def create_short_term_checkpointer():
    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()

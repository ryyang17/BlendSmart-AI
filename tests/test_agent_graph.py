"""Smoke tests for the LangGraph agent graph structure."""
import pytest
from app.agent.graph import agent


def test_graph_compiles():
    assert agent is not None


def test_graph_has_expected_nodes():
    node_names = set(agent.nodes.keys())
    expected = {"intent", "followup", "retriever", "recipe", "quality", "response"}
    assert expected.issubset(node_names)

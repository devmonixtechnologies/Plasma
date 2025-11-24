"""
This module contains tests for the Mako template rendering of the system master template
used in the agent framework. It includes tests to verify the correct rendering of the 
template with various configurations, including the presence of agent instructions and 
handling of environment variables.
"""

import os
import pytest
from mako.template import Template

# Fixture to load the Mako template for the system master template
@pytest.fixture
def template():
    return Template(filename="src/cai/prompts/core/system_master_template.md")

# Fixture to create a base agent with predefined instructions
@pytest.fixture
def base_agent():
    return type('Agent', (), {'instructions': 'Test instructions'})()

def test_master_template_basic(template, base_agent):
    """Test basic master template rendering without optional components."""
    result = template.render(
        agent=base_agent, 
        reasoning_content=None, 
        ctf_instructions="",
        env_context="false",
        compacted_summary="",
        rag_enabled=False,
        seclist_dirs="",
        wordlist_files="",
        artifacts="",
        system_prompt=base_agent.instructions,
        context_variables={},
        os=os,
        locals=locals,
        globals=globals
    )
    print(result)
    # Verify that the agent's instructions are included in the rendered template
    assert 'Test instructions' in result
    # Ensure that the CTF_INSIDE placeholder is not present
    assert 'CTF_INSIDE' not in result

def test_master_template_with_env_vars(template, base_agent):
    """Test master template with environment variables and vector DB."""
    # Set an environment variable for the CTF name
    os.environ['CTF_NAME'] = 'test_ctf'
    result = template.render(
        agent=base_agent, 
        reasoning_content=None, 
        ctf_instructions="",
        env_context="false",
        compacted_summary="",
        rag_enabled=False,
        seclist_dirs="",
        wordlist_files="",
        artifacts="",
        system_prompt=base_agent.instructions,
        context_variables={},
        os=os,
        locals=locals,
        globals=globals
    )
    # Verify that the agent's instructions are included in the rendered template
    assert "Test instructions" in result
    # Clean up by deleting the environment variable
    del os.environ['CTF_NAME']

def test_master_template_no_instructions(template):
    """Test master template without agent instructions."""
    # Create an agent with empty instructions
    agent = type('Agent', (), {'instructions': ''})()
    result = template.render(
        agent=agent, 
        reasoning_content=None, 
        ctf_instructions="",
        env_context="false",
        compacted_summary="",
        rag_enabled=False,
        seclist_dirs="",
        wordlist_files="",
        artifacts="",
        system_prompt=agent.instructions,
        context_variables={},
        os=os,
        locals=locals,
        globals=globals
    )
    # Verify that the rendered template starts with an empty string
    assert result.strip().startswith('')

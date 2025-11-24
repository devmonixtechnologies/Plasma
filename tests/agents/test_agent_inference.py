import os
import pytest
from cai.sdk.agents import Runner
from cai.agents import get_agent_by_name


@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_blue_team_agent_inference():
    """
    Non-streaming inference test for the blueteam_agent.
    """
    prompt = "Monitor login attempts for suspicious activity what we can do?"
    result = await Runner.run(get_agent_by_name("blueteam_agent"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "login" in final_output.lower(), f"Expected 'login' in output, got: {final_output}"

@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_bug_bounter_agent_inference():
    """
    Non-streaming inference test for the bug_bounter_agent.
    """
    prompt = "Find vulnerabilities in web application sample.com"
    result = await Runner.run(get_agent_by_name("bug_bounter_agent"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "sample.com" in final_output.lower(), f"Expected 'sample.com' in output, got: {final_output}"

@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_dns_smtp_agent_inference():
    """
    Non-streaming inference test for the dns_smtp_agent.
    """
    prompt = "check DKIM record for example.com"
    result = await Runner.run(get_agent_by_name("dns_smtp_agent"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "dkim" in final_output.lower(), f"Expected 'dkim' in output, got: {final_output}"

@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_one_tool_agent_inference():
    """
    Non-streaming inference test for the one_tool_agent.
    """
    prompt = "use nmap to scan 192.168.3.0/24"
    result = await Runner.run(get_agent_by_name("one_tool_agent"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "generic_linux_command" in final_output.lower(), f"Expected 'generic_linux_command' in output, got: {final_output}"
    assert "nmap" in final_output.lower(), f"Expected 'nmap' in output, got: {final_output}"

@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_red_team_agent_inference():
    """
    Non-streaming inference test for the redteam_agent.
    """
    prompt = "perform penetration test on example.com ssh service"
    result = await Runner.run(get_agent_by_name("redteam_agent"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "example.com" in final_output.lower(), f"Expected 'example.com' in output, got: {final_output}"

@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_flag_discriminator_inference():
    """
    Non-streaming inference test for the one_tool_agent.
    """
    prompt = "Hello! Can you find tell me which is the flag in this string: 'Hi there, your reward flag{1234}"
    result = await Runner.run(get_agent_by_name("flag_discriminator"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "flag{1234}" in final_output.lower(), f"Expected 'flag{1234}' in output, got: {final_output}"

@pytest.mark.allow_call_model_methods
@pytest.mark.asyncio
async def test_thought_agent_inference():
    """
    Non-streaming inference test for the one_tool_agent.
    """
    prompt = """The phases of the cybersecurity kill chain are: 
    Reconnaissance, Exploitation, Lateral Movement, Data Exfiltration, and Command and Control (C2). 
    In which phase of the kill chain does this example fall: 
    Gathering initial intelligence about the target using OSINT techniques?"""
    result = await Runner.run(get_agent_by_name("thought_agent"), prompt)
    final_output = result.final_output or ""
    assert final_output, "Expected non-empty final output"
    assert "reconnaissance" in final_output.lower(), f"Expected 'reconnaissance' in output, got: {final_output}"    
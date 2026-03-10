from agent.agent import run_agent


def test_agent_vat_sweden():
    task = "What is the VAT of Sweden?"
    res = run_agent(task)
    assert isinstance(res, dict)
    result = res.get("result")
    assert result is not None
    # result should include the country code and a summary
    assert result.get("country") == "SE"
    assert "Standard VAT rate" in result.get("summary", "")


def test_agent_vat_netherlands():
    task = "VAT Netherlands"
    res = run_agent(task)
    result = res.get("result")
    assert result.get("country") == "NL"

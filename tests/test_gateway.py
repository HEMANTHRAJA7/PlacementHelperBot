import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from src.core.ai_gateway import AIGateway, ClassificationResult, PlacementCategory
from src.models.user import AIUsageLog
from sqlalchemy import select

# A Mock Redis for evaluating the rate limiter
class MockRedis:
    def __init__(self, allowed=True):
        self.allowed = allowed
        self.eval_called = False

    async def eval(self, script, numkeys, key, *args):
        self.eval_called = True
        return 1 if self.allowed else 0

    async def close(self):
        pass

@pytest.mark.asyncio
async def test_ai_gateway_rate_limiting_allowed():
    gateway = AIGateway(api_key="mock_key", redis_url="redis://localhost:6379/0")
    
    mock_redis = MockRedis(allowed=True)
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        allowed = await gateway.check_rate_limit()
        assert allowed is True
        assert mock_redis.eval_called is True

@pytest.mark.asyncio
async def test_ai_gateway_rate_limiting_denied():
    gateway = AIGateway(api_key="mock_key", redis_url="redis://localhost:6379/0")
    
    mock_redis = MockRedis(allowed=False)
    with patch("redis.asyncio.from_url", return_value=mock_redis):
        allowed = await gateway.check_rate_limit()
        assert allowed is False
        assert mock_redis.eval_called is True

@pytest.mark.asyncio
async def test_ai_gateway_cost_logging(db_session):
    gateway = AIGateway(api_key="mock_key")
    
    await gateway.log_usage(input_tokens=1000, output_tokens=500, status="success", message_id="msg_123")
    
    result = await db_session.execute(select(AIUsageLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    log = logs[0]
    assert log.input_tokens == 1000
    assert log.output_tokens == 500
    # Expected cost: 1000 * 0.075 / 1e6 + 500 * 0.3 / 1e6 = 0.000075 + 0.00015 = 0.000225
    assert log.estimated_cost_usd == Decimal("0.000225")
    assert log.status == "success"
    assert log.message_id == "msg_123"

@pytest.mark.asyncio
@patch("src.core.ai_gateway.AIGateway.check_rate_limit", return_value=True)
async def test_ai_gateway_classify_email_success(mock_rate_limit, db_session):
    gateway = AIGateway(api_key="mock_key")
    
    mock_response = MagicMock()
    mock_response.usage_metadata = MagicMock()
    mock_response.usage_metadata.prompt_token_count = 200
    mock_response.usage_metadata.candidates_token_count = 100
    
    mock_result = ClassificationResult(
        is_placement=True,
        category=PlacementCategory.OFFER,
        company="Google",
        role="Software Engineer",
        package="60 LPA",
        deadline="Tomorrow",
        application_links=["https://google.com/jobs"],
        confidence=0.98
    )
    mock_response.parsed = mock_result
    
    gateway.client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    
    res = await gateway.classify_email(subject="Offer from Google", body="Congrats!", message_id="msg_789")
    
    assert res.is_placement is True
    assert res.company == "Google"
    assert res.category == PlacementCategory.OFFER
    assert res.confidence == 0.98
    
    result = await db_session.execute(select(AIUsageLog))
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].input_tokens == 200
    assert logs[0].output_tokens == 100

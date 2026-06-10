import os
import yaml
import time
import logging
import asyncio
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
import redis.asyncio as aioredis
from fastapi import HTTPException

from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.core.config import settings
from src.core import database
from src.models.user import AIUsageLog

logger = logging.getLogger(__name__)

RATE_LIMIT_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local fill_rate = tonumber(ARGV[2])
local requested = tonumber(ARGV[3]) or 1
local now = tonumber(ARGV[4])

local data = redis.call("HMGET", key, "tokens", "last_updated")
local tokens = tonumber(data[1])
local last_updated = tonumber(data[2])

if not tokens then
    tokens = capacity
    last_updated = now
else
    local elapsed = now - last_updated
    if elapsed > 0 then
        tokens = math.min(capacity, tokens + (elapsed * fill_rate))
        last_updated = now
    end
end

if tokens >= requested then
    tokens = tokens - requested
    redis.call("HMSET", key, "tokens", tokens, "last_updated", last_updated)
    return 1
else
    redis.call("HMSET", key, "tokens", tokens, "last_updated", last_updated)
    return 0
end
"""

class PlacementCategory(str, Enum):
    OFFER = "Offer"
    SHORTLIST = "Shortlist"
    INTERVIEW = "Interview"
    ASSESSMENT = "Assessment"
    OPPORTUNITY = "Opportunity"

class ClassificationResult(BaseModel):
    is_placement: bool = Field(description="True if the email is related to college placement, internship, or job recruitment.")
    category: Optional[PlacementCategory] = Field(None, description="The priority category of the placement email.")
    company: Optional[str] = Field(None, description="Name of the company, if applicable.")
    role: Optional[str] = Field(None, description="The job role / title, if applicable.")
    package: Optional[str] = Field(None, description="Compensation package details (e.g. CTC, stipend), if mentioned.")
    deadline: Optional[str] = Field(None, description="Application or registration deadline, if mentioned.")
    application_links: list[str] = Field(default_factory=list, description="Links/URLs for applications, tests, or registrations.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the classification between 0.0 and 1.0.")

class AttachmentMatchingResult(BaseModel):
    is_matched: bool = Field(description="True if the student's Register Number, NeoPAT ID, Email, or Name is found in the attachment.")
    matched_identifier: Optional[str] = Field(None, description="The specific identifier that matched (e.g. '21BCE0001', 'NP0099', or student's name).")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the match.")
    reason: Optional[str] = Field(None, description="Brief explanation of where/how the match was found in the attachment.")


class AIGateway:
    def __init__(self, api_key: str = None, redis_url: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or "DUMMY_KEY"
        self.redis_url = redis_url or settings.REDIS_URL
        self.client = genai.Client(api_key=self.api_key)
        self.rate_limit_key = "ai_gateway:rate_limit"
        self.capacity = 15.0
        self.fill_rate = 15.0 / 60.0  # 0.25 tokens per second
        self.model_name = "gemini-2.0-flash"
        self.prompt_version = "v1"

    async def check_rate_limit(self) -> bool:
        """Checks if the request is within rate limits using a Redis Lua script.
        
        Returns True if allowed, False if rate-limited.
        If Redis connection fails, prints warning and returns True (fail open).
        """
        try:
            client = aioredis.from_url(self.redis_url, decode_responses=True)
            now_seconds = time.time()
            result = await client.eval(
                RATE_LIMIT_LUA,
                1,
                self.rate_limit_key,
                str(self.capacity),
                str(self.fill_rate),
                "1",
                str(now_seconds)
            )
            await client.close()
            return int(result) == 1
        except Exception as e:
            logger.warning(f"Redis rate limiter failed (fail-open): {e}")
            return True

    async def log_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        status: str,
        message_id: Optional[str] = None
    ):
        """Asynchronously writes a token usage and cost log entry into PostgreSQL."""
        cost = (input_tokens * 0.075 / 1_000_000.0) + (output_tokens * 0.30 / 1_000_000.0)
        
        # Increment Prometheus metrics
        from src.core.metrics import AI_TOKENS, AI_COST_USD
        AI_TOKENS.labels(model=self.model_name, type="prompt").inc(input_tokens)
        AI_TOKENS.labels(model=self.model_name, type="completion").inc(output_tokens)
        AI_COST_USD.inc(cost)
        
        try:
            async with database.SessionLocal() as session:
                log_entry = AIUsageLog(
                    model_name=self.model_name,
                    prompt_version=self.prompt_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=Decimal(f"{cost:.8f}"),
                    message_id=message_id,
                    status=status
                )
                session.add(log_entry)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to write AI usage log to database: {e}")

    async def classify_email(
        self,
        subject: str,
        body: str,
        message_id: Optional[str] = None
    ) -> ClassificationResult:
        """Sends the email details to Gemini 2.0 Flash for structured classification,
        
        enforcing Redis rate limits and a 3-attempt exponential backoff retry loop.
        """
        # Load prompt
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(current_dir, "prompts", f"{self.prompt_version}_classification.yaml")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_data = yaml.safe_load(f)
        system_instruction = prompt_data["system_instruction"]

        content = f"Subject: {subject}\n\nBody:\n{body}"
        backoffs = [5.0, 30.0, 120.0]
        
        last_exception = None
        for attempt in range(4):
            # Check rate limiter first
            allowed = await self.check_rate_limit()
            if not allowed:
                logger.warning(f"Local Redis rate limit exceeded on attempt {attempt + 1}/4.")
                if attempt < 3:
                    sleep_time = backoffs[attempt]
                    logger.info(f"Retrying after rate limit in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    await self.log_usage(0, 0, "rate_limited", message_id)
                    raise HTTPException(
                        status_code=429,
                        detail="AI Gateway local rate limit exceeded. Max retries exhausted."
                    )
            
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=ClassificationResult,
                    ),
                )
                
                # Extract token usage details
                input_tokens = 0
                output_tokens = 0
                if response.usage_metadata:
                    input_tokens = response.usage_metadata.prompt_token_count or 0
                    output_tokens = response.usage_metadata.candidates_token_count or 0
                
                # Log success usage
                await self.log_usage(input_tokens, output_tokens, "success", message_id)
                
                # Return parsed structured result
                if hasattr(response, "parsed") and response.parsed is not None:
                    return response.parsed
                else:
                    # Fallback if parsed is not present
                    import json
                    parsed_json = json.loads(response.text)
                    return ClassificationResult(**parsed_json)
                    
            except (APIError, Exception) as e:
                logger.warning(f"AI Gateway request failed on attempt {attempt + 1}/4: {e}")
                last_exception = e
                
                # Log failed attempt
                await self.log_usage(0, 0, "failed", message_id)
                
                if attempt < 3:
                    sleep_time = backoffs[attempt]
                    logger.info(f"Retrying AI Gateway request in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    # Reraise or handle
                    break
                    
        from src.core.metrics import AI_FAILURES
        AI_FAILURES.inc()
        raise HTTPException(
            status_code=502,
            detail=f"AI Gateway failed after max retries. Last error: {str(last_exception)}"
        )

    async def classify_attachment_vision(
        self,
        attachment_bytes: bytes,
        mime_type: str,
        student_info: dict,
        message_id: Optional[str] = None
    ) -> AttachmentMatchingResult:
        """Sends an attachment file chunk (e.g. PDF, Image) to Gemini 2.0 Flash for vision-based structured student matching."""
        system_instruction = (
            "You are an advanced AI vision scanner for 'Placement Sentinel', a system that monitors placement shortlists.\n"
            "Your task is to analyze the provided attachment file (which could be an image of a spreadsheet, a screenshot of a message, or a document table).\n"
            "Determine if the file contains references matching any of the following student details:\n"
            f"- Name tokens: {student_info.get('full_name', 'N/A')}\n"
            f"- Register Number: {student_info.get('register_number', 'N/A')}\n"
            f"- NeoPAT ID: {student_info.get('neopat_id', 'N/A')}\n"
            f"- Email: {student_info.get('email', 'N/A')}\n\n"
            "Rules:\n"
            "1. Search case-insensitively.\n"
            "2. If you find a matching name, register number, NeoPAT ID, or email, set `is_matched` to true, "
            "populate `matched_identifier` with the value you found, and set your confidence. Describe the location in `reason`.\n"
            "3. If none of the details are present, set `is_matched` to false.\n"
            "4. Return the structured response conforming exactly to the response schema."
        )

        attachment_part = types.Part.from_bytes(
            data=attachment_bytes,
            mime_type=mime_type
        )
        
        backoffs = [5.0, 30.0, 120.0]
        last_exception = None
        for attempt in range(4):
            allowed = await self.check_rate_limit()
            if not allowed:
                logger.warning(f"Local Redis rate limit exceeded on attempt {attempt + 1}/4 for vision scan.")
                if attempt < 3:
                    await asyncio.sleep(backoffs[attempt])
                    continue
                else:
                    await self.log_usage(0, 0, "rate_limited", message_id)
                    raise HTTPException(
                        status_code=429,
                        detail="AI Gateway local rate limit exceeded for vision scan."
                    )
            
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=[
                        "Analyze this attachment for the specified student details.",
                        attachment_part
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=AttachmentMatchingResult,
                    ),
                )
                
                input_tokens = 0
                output_tokens = 0
                if response.usage_metadata:
                    input_tokens = response.usage_metadata.prompt_token_count or 0
                    output_tokens = response.usage_metadata.candidates_token_count or 0
                    
                await self.log_usage(input_tokens, output_tokens, "success", message_id)
                
                if hasattr(response, "parsed") and response.parsed is not None:
                    return response.parsed
                else:
                    import json
                    parsed_json = json.loads(response.text)
                    return AttachmentMatchingResult(**parsed_json)
                    
            except (APIError, Exception) as e:
                logger.warning(f"AI Gateway vision scan failed on attempt {attempt + 1}/4: {e}")
                last_exception = e
                await self.log_usage(0, 0, "failed", message_id)
                if attempt < 3:
                    await asyncio.sleep(backoffs[attempt])
                else:
                    break
                    
        from src.core.metrics import AI_FAILURES
        AI_FAILURES.inc()
        raise HTTPException(
            status_code=502,
            detail=f"AI Gateway vision scan failed after max retries. Last error: {str(last_exception)}"
        )


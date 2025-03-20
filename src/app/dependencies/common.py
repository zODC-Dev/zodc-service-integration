from typing import AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis

from src.configs.redis import get_redis_client
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.redis_service import RedisService


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency for redis client"""
    client = await get_redis_client()
    try:
        yield client
    finally:
        await client.close()


async def get_redis_service(redis_client: Redis = Depends(get_redis_client)):
    """Dependency for redis repository"""
    return RedisService(redis_client=redis_client)


async def get_nats_service():
    """Dependency for nats service"""
    return NATSService()

from fastapi import Depends
from redis.asyncio import Redis
from src.infrastructure.services.redis_service import RedisService
from src.configs.redis import get_redis_client

async def get_redis_service(redis_client: Redis = Depends(get_redis_client)):
    """Dependency for redis repository"""
    return RedisService(redis_client=redis_client)
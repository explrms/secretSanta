import json
import time

from redis import asyncio as aioredis

from config import REDIS_HOST, REDIS_PORT, REDIS_DB


class AsyncRedisClient:
    def __init__(self):
        self.redis = aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

    async def set(self, key: str, value: dict | list, expire: int = None):
        data = {"value": value, "created_at": time.time()}
        await self.redis.set(key, json.dumps(data), expire)

    async def get(self, key: str) -> dict | list | None:
        value = await self.redis.get(key)
        if value:
            data = json.loads(value)
            return data["value"]
        return None

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def ttl(self, key: str) -> int:
        return await self.redis.ttl(key)

    async def lifetime(self, key: str) -> int | None:
        value = await self.redis.get(key)
        if value:
            data = json.loads(value)
            created_at = data.get("created_at", 0)
            if created_at:
                return int(time.time() - created_at)
        return None

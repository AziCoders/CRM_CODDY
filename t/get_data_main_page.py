import os
import asyncio
from dotenv import load_dotenv
from notion_client import AsyncClient

# --- Настройки ---
STATIC_FIELDS = {"Дата оплаты", "ФИО", "Phone", "Комментарий"}

def to_db_id(raw: str) -> str:
    """Превращает 32-символьную строку в UUID с дефисами: 27fd06fcf646... -> 27fd06fc-f646-..."""
    r = raw.replace("-", "").strip()
    if len(r) != 32:
        return raw  # возможно уже UUID
    return f"{r[0:8]}-{r[8:12]}-{r[12:16]}-{r[16:20]}-{r[20:32]}"

def fio_key(s: str) -> str:
    return (s or "").strip().lower()

async def fetch_all_records(notion: AsyncClient, database_id: str) -> list:
    results = []
    resp = await notion.databases.query(database_id=database_id)
    results.extend(resp["results"])
    while resp.get("has_more"):
        resp = await notion.databases.query(database_id=database_id, start_cursor=resp["next_cursor"])
        results.extend(resp["results"])
    return results

async def get_db_properties(notion: AsyncClient, database_id: str) -> dict:
    db = await notion.databases.retrieve(database_id=database_id)
    return db.get("properties", {})

def get_text_prop(props: dict, field: str) -> str:
    val = props.get(field)
    if not val:
        return ""
    if "title" in val:
        parts = val["title"]
    elif "rich_text" in val:
        parts = val["rich_text"]
    else:
        parts = []
    return "".join(p.get("plain_text", "") for p in parts) if parts else ""

def get_select_name(props: dict, field: str) -> str:
    sel = props.get(field, {}).get("select")
    return sel["name"] if sel else ""

async def build_source_map(notion: AsyncClient, source_db: str, month_fields: list) -> dict:
    """Формирует {fio_key: {month: status}} из источника."""
    pages = await fetch_all_records(notion, source_db)
    src = {}
    for p in pages:
        props = p.get("properties", {})
        name = fio_key(get_text_prop(props, "ФИО"))
        if not name:
            continue
        per_month = {}
        for m in month_fields:
            val = get_select_name(props, m)
            if val:  # переносим только непустое
                per_month[m] = val
        if per_month:
            src[name] = per_month
    return src

def build_update_payload(props: dict, month_fields: list, src_per_month: dict) -> dict:
    """Готовит payload для pages.update по пересечению месяцев с непустыми значениями из источника."""
    update = {}
    for m in month_fields:
        val = src_per_month.get(m)
        if val:
            # В обеих БД набор опций одинаковый — можно ставить по имени.
            update[m] = {"select": {"name": val}}
    return update

async def main():
    load_dotenv()

    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY не задан")

    # IDs можно задать в .env или подставить прямо из ссылок
    source_id_raw = os.getenv("SOURCE_PAYMENT_DB_ID", "27fd06fcf6468106bdded8e3509e55f4")
    target_id_raw = os.getenv("TARGET_PAYMENT_DB_ID", "2abd06fcf64681f0bbd4d699049d54ec")
    DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")

    source_db = to_db_id(source_id_raw)
    target_db = to_db_id(target_id_raw)

    notion = AsyncClient(auth=api_key)

    # 1) Определяем «месяцы» по структуре назначения (она — эталон)
    target_props = await get_db_properties(notion, target_db)
    month_fields = [n for n in target_props.keys() if n not in STATIC_FIELDS]
    if not month_fields:
        raise RuntimeError("В целевой базе не найдены месячные столбцы.")

    print(f"🧭 Месячные столбцы ({len(month_fields)}): {', '.join(month_fields)}")

    # 2) Строим карту оплат из источника
    src_map = await build_source_map(notion, source_db, month_fields)
    print(f"📦 В источнике найдено учеников с оплатами: {len(src_map)}")

    # 3) Пробегаем целевую базу и обновляем совпадения по ФИО
    target_pages = await fetch_all_records(notion, target_db)
    updated, skipped = 0, 0

    for p in target_pages:
        props = p.get("properties", {})
        name_raw = get_text_prop(props, "ФИО")
        key = fio_key(name_raw)
        if not key or key not in src_map:
            skipped += 1
            continue

        payload = build_update_payload(props, month_fields, src_map[key])
        if not payload:
            skipped += 1
            continue

        print(f"→ {name_raw}: обновляю {list(payload.keys())}")
        if not DRY_RUN:
            await notion.pages.update(page_id=p["id"], properties=payload)
        updated += 1

    print(f"\n✅ Готово. Обновлено записей: {updated}. Пропущено: {skipped}. DRY_RUN={DRY_RUN}")

    await notion.aclose()

if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

from app.services.mobile.common import as_list, lang_suffix, offset_limit, paginate_rows
from app.utils.di.db_ctx import CRM_DB


async def categories(page: int | None = None, page_size: int | None = None):
    offset, limit = offset_limit(page, page_size)
    lang = lang_suffix()
    count = await CRM_DB.fetchval(
        """
        SELECT count(*)
        FROM category_category
        WHERE category_title <> 'Архив'
        """
    )
    query = f"""
        SELECT
            c.category_id,
            COALESCE(to_jsonb(c)->>'category_title_{lang}', c.category_title) AS category_title,
            to_jsonb(c)->>'category_title_ru' AS category_title_ru,
            to_jsonb(c)->>'category_title_en' AS category_title_en,
            to_jsonb(c)->>'category_title_uz' AS category_title_uz,
            to_jsonb(c)->>'category_icon' AS category_icon,
            COALESCE(
                jsonb_agg(
                    DISTINCT jsonb_build_object(
                        'work_id', w.work_id,
                        'work_title', COALESCE(to_jsonb(w)->>'work_title_{lang}', w.work_title),
                        'work_type', w.work_type,
                        'work_basic_price', w.work_basic_price,
                        'work_vip_price', w.work_vip_price,
                        'work_discount_price', w.work_discount_price,
                        'work_discount_percent', w.work_discount_percent
                    )
                ) FILTER (WHERE w.work_id IS NOT NULL),
                '[]'::jsonb
            ) AS work_category
        FROM category_category c
        LEFT JOIN work_work_category wc ON wc.category_id = c.category_id
        LEFT JOIN work_work w ON w.work_id = wc.work_id AND COALESCE(w.deleted, FALSE) = FALSE
        WHERE c.category_title <> 'Архив'
        GROUP BY c.category_id
        ORDER BY c.category_id DESC
    """
    args = []
    if limit is not None:
        query += " LIMIT $1 OFFSET $2"
        args = [limit, offset]

    rows = as_list(await CRM_DB.fetch(query, *args))
    return paginate_rows(rows, count=count or 0, page=page, page_size=page_size)

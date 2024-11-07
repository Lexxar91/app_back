from typing import TypedDict, Any

class PatentHolder(TypedDict):
    """Структура данных держателя патента."""
    tax_number: str
    full_name: str


class PatentListResponse(TypedDict):
    """Ответ API со списком патентов."""
    total: int
    items: list[dict[str, Any]]


class PatentStatsResponse(TypedDict):
    """Ответ API со статистикой по патентам."""
    total_patents: int
    total_ru_patents: int
    total_with_holders: int
    total_ru_with_holders: int
    with_holders_percent: int
    ru_with_holders_percent: int
    by_author_count: dict[str, int]
    by_patent_kind: dict[int, int]

class StatsItem(TypedDict):
    name: str
    count: int

class FromPersonPatentStatsResponse(TypedDict):
    okopf_stats: list[StatsItem]
    okvad_stats: list[StatsItem]
    mpk_stats: list[StatsItem]

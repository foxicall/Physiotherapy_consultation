"""Load and retrieve syndrome records from the clinic's Markdown source."""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().with_name("pt-50-syndromes-database.md")
FIELD_NAMES = (
    "民眾白話比喻與感受",
    "為什麼單靠休息/電療熱敷好不了？",
    "物理治療核心介入手法",
    "階段性恢復進程",
    "持續治療說服話術（不作為成本）",
    "治療師給病患的一句安心叮嚀",
)


@dataclass(frozen=True)
class Syndrome:
    id: int
    title: str
    category: str
    metaphor: str
    rationale: str
    interventions: str
    recovery: str
    inaction: str
    reassurance: str

    @property
    def fields(self) -> tuple[str, ...]:
        return (
            self.metaphor, self.rationale, self.interventions,
            self.recovery, self.inaction, self.reassurance,
        )

    @property
    def label(self) -> str:
        return f"{self.id}. {self.title}"


def parse_syndromes(markdown: str) -> tuple[Syndrome, ...]:
    """Require all 50 numbered records and their six fields; never drop bad rows."""
    records = []
    category = ""
    current = None
    fields = {}
    active_field = None

    def finish_record() -> None:
        if current is None:
            return
        if not current[2] or set(fields) != set(range(1, 7)) or not all(fields.values()):
            raise ValueError(f"症候群 {current[0]} 缺少分類或完整的六個欄位。")
        records.append(Syndrome(*current, *(fields[i] for i in range(1, 7))))

    for line in markdown.splitlines():
        category_match = re.match(r"^#\s+[一二三四五六七八九十]+、\s*(.+?)（\d+-\d+）\s*$", line)
        heading_match = re.match(r"^###\s+(\d+)\.\s+(.+?)\s*$", line)
        field_match = re.match(r"^-\s+\*\*(\d+)\.\s+(.+?)\*\*\s*[：:]\s*(.*)$", line)
        if category_match:
            finish_record()
            current, fields, active_field = None, {}, None
            category = category_match[1]
        elif heading_match:
            finish_record()
            current = (int(heading_match[1]), heading_match[2], category)
            fields, active_field = {}, None
        elif field_match and current is not None:
            number = int(field_match[1])
            if number not in range(1, 7) or number in fields or field_match[2] != FIELD_NAMES[number - 1]:
                raise ValueError(f"症候群 {current[0]} 的欄位編號或名稱不正確。")
            active_field = number
            fields[number] = field_match[3].strip()
        elif line.strip() == "---":
            active_field = None
        elif line.strip() and active_field is not None:
            fields[active_field] += "\n" + line.strip()
    finish_record()
    if [record.id for record in records] != list(range(1, 51)):
        raise ValueError("知識庫必須依序包含編號 1–50，不能重複或缺漏。")
    return tuple(records)


def load_syndromes(path: Path = DATABASE_PATH) -> tuple[Syndrome, ...]:
    # Re-read on each Streamlit rerun so edits to the Markdown take effect immediately.
    return parse_syndromes(path.read_text(encoding="utf-8-sig"))


def normalize_search(text: str) -> str:
    return "".join(character for character in unicodedata.normalize("NFKC", text).casefold() if character.isalnum())


def fuzzy_title_score(query: str, title: str) -> float:
    """Compare short queries with title windows, including one-character typos."""
    if len(query) < 3:
        return 0.0
    return max(
        (
            SequenceMatcher(None, query, title[start:start + width], autojunk=False).ratio()
            for width in (len(query) - 1, len(query), len(query) + 1)
            for start in range(max(1, len(title) - width + 1))
        ),
        default=0.0,
    )


def search_syndromes(records: tuple[Syndrome, ...], query: str) -> list[Syndrome]:
    """Rank names/aliases first, then symptom text and approximate title matches."""
    if not query.strip():
        return list(records)
    normalized = normalize_search(query)
    if not normalized:
        return []
    tokens = [normalize_search(token) for token in query.split() if normalize_search(token)]
    ranked = []
    for record in records:
        title = normalize_search(record.title)
        content = normalize_search(" ".join((record.title, record.category, *record.fields)))
        if normalized == str(record.id):
            score = 110.0
        elif normalized in title:
            score = 100.0
        elif all(token in title for token in tokens):
            score = 95.0
        elif normalized in content or all(token in content for token in tokens):
            score = 80.0
        else:
            similarity = fuzzy_title_score(normalized, title)
            if similarity < 0.65:
                continue
            score = 50.0 * similarity
        ranked.append((score, record))
    ranked.sort(key=lambda item: (-item[0], item[1].id))
    return [record for _, record in ranked]

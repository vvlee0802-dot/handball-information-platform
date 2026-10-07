import re
from io import BytesIO
from typing import Any

import pdfplumber

PARSER_NAME = "paris-2024-ihf-match-report-v1"


class MatchReportParseError(ValueError):
    pass


def _cell(row: list[Any], index: int) -> str:
    if index >= len(row) or row[index] is None:
        return ""
    return str(row[index]).strip()


def _count_mark(value: str) -> int:
    value = value.strip()
    if not value:
        return 0
    if value.isdigit():
        return int(value)
    return len([item for item in re.split(r"[,;\s]+", value) if item])


def _parse_player(row: list[Any], offset: int) -> dict[str, Any] | None:
    number = _cell(row, offset)
    name = _cell(row, offset + (2 if offset == 0 else 1))
    if not number.isdigit() or not name:
        return None

    if offset == 0:
        goals_index, yellow_index, suspension_index, red_index, blue_index = 7, 8, 9, 10, 11
    else:
        goals_index, yellow_index, suspension_index, red_index, blue_index = 18, 20, 21, 22, 23

    return {
        "number": int(number),
        "name": re.sub(r"\s*\(C\)\s*$", "", name).strip(),
        "goals": _count_mark(_cell(row, goals_index)),
        "yellow_cards": _count_mark(_cell(row, yellow_index)),
        "suspensions_2min": _count_mark(_cell(row, suspension_index)),
        "red_cards": _count_mark(_cell(row, red_index)),
        "blue_cards": _count_mark(_cell(row, blue_index)),
    }


def _parse_rosters(tables: list[list[list[Any]]]) -> tuple[list[dict], list[dict]]:
    roster_table: list[list[Any]] | None = None
    header_index = -1
    for table in tables:
        for index, row in enumerate(table):
            if _cell(row, 0) == "No." and "Team A" in _cell(row, 2) and "Team B" in _cell(row, 13):
                roster_table = table
                header_index = index
                break
        if roster_table is not None:
            break

    if roster_table is None:
        raise MatchReportParseError("未找到球员名单表，请确认该 PDF 是受支持的官方赛后报告。")

    team_a_players: list[dict] = []
    team_b_players: list[dict] = []
    for row in roster_table[header_index + 1 :]:
        player_a = _parse_player(row, 0)
        player_b = _parse_player(row, 12)
        if player_a is not None:
            team_a_players.append(player_a)
        if player_b is not None:
            team_b_players.append(player_b)

    if not team_a_players or not team_b_players:
        raise MatchReportParseError("报告中的双方球员名单不完整，无法安全导入。")
    return team_a_players, team_b_players


def _score_values(text: str) -> tuple[int, int, int, int]:
    score_section_match = re.search(
        r"Half-time \(30[^\n]*\)(.*?)(?:Number of 7m)", text, flags=re.DOTALL
    )
    if score_section_match is None:
        raise MatchReportParseError("未找到半场和最终比分。")
    values = [int(value) for value in re.findall(r"\b\d+\b", score_section_match.group(1))]
    if len(values) < 4:
        raise MatchReportParseError("比分字段不完整，无法安全导入。")
    return values[0], values[1], values[2], values[3]


def _seven_meter_values(text: str) -> tuple[tuple[int, int], tuple[int, int]]:
    section_match = re.search(r"Number of 7m(.*?)(?:No\.\s*Team)", text, flags=re.DOTALL)
    ratios = re.findall(r"(\d+)\s*/\s*(\d+)", section_match.group(1) if section_match else "")
    if len(ratios) < 2:
        return (0, 0), (0, 0)
    return (int(ratios[0][0]), int(ratios[0][1])), (int(ratios[1][0]), int(ratios[1][1]))


def _timeouts(text: str) -> tuple[list[str], list[str]]:
    section_match = re.search(r"Number of 7m(.*?)(?:No\.\s*Team)", text, flags=re.DOTALL)
    values = re.findall(r"\b\d{1,2}:\d{2}\b", section_match.group(1) if section_match else "")
    return values[:3], values[3:6]


def parse_official_match_report_pdf(content: bytes) -> dict[str, Any]:
    if not content.startswith(b"%PDF-"):
        raise MatchReportParseError("文件不是有效的 PDF。")

    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            if not pdf.pages:
                raise MatchReportParseError("PDF 没有可读页面。")
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            tables = [table for page in pdf.pages for table in page.extract_tables()]
    except MatchReportParseError:
        raise
    except Exception as exc:
        raise MatchReportParseError("PDF 损坏或无法读取。") from exc

    if len(text.strip()) < 100:
        raise MatchReportParseError("该 PDF 没有可读文本层，当前 MVP 暂不支持扫描件 OCR。")
    if "Match Report" not in text or "Team A" not in text or "Team B" not in text:
        raise MatchReportParseError("当前仅支持 IHF/奥运会官方 Match Report 格式。")

    team_line = re.search(
        r"^A\s+([A-Z]{3})\s*-\s*(.+?)\s+B\s+([A-Z]{3})\s*-\s*(.+)$",
        text,
        flags=re.MULTILINE,
    )
    if team_line is None:
        raise MatchReportParseError("未找到参赛队伍信息。")
    team_a_players, team_b_players = _parse_rosters(tables)
    half_a, half_b, final_a, final_b = _score_values(text)
    seven_a, seven_b = _seven_meter_values(text)
    timeouts_a, timeouts_b = _timeouts(text)

    date_match = re.search(
        r"\b(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2}\s+[A-Z]{3}\s+\d{4})", text
    )
    start_match = re.search(r"Start Time\s+(\d{1,2}:\d{2})", text)
    match_number = re.search(r"Match\s+(\d+)\b", text)
    stage_match = re.search(
        r"(?:MON|TUE|WED|THU|FRI|SAT|SUN)\s+\d{1,2}\s+[A-Z]{3}\s+\d{4}\s+([^\n]+)",
        text,
    )
    venue_match = re.search(r"^(.+?)\s+Handball$", text, flags=re.MULTILINE)

    return {
        "report_type": PARSER_NAME,
        "match_number": int(match_number.group(1)) if match_number else None,
        "competition_stage": stage_match.group(1).strip() if stage_match else None,
        "match_date": date_match.group(1).title() if date_match else None,
        "start_time": start_match.group(1) if start_match else None,
        "venue": venue_match.group(1).strip() if venue_match else None,
        "team_a": {
            "side": "A",
            "code": team_line.group(1),
            "name": team_line.group(2).strip(),
            "half_time_score": half_a,
            "final_score": final_a,
            "seven_meter_goals": seven_a[0],
            "seven_meter_attempts": seven_a[1],
            "timeouts": timeouts_a,
            "players": team_a_players,
        },
        "team_b": {
            "side": "B",
            "code": team_line.group(3),
            "name": team_line.group(4).strip(),
            "half_time_score": half_b,
            "final_score": final_b,
            "seven_meter_goals": seven_b[0],
            "seven_meter_attempts": seven_b[1],
            "timeouts": timeouts_b,
            "players": team_b_players,
        },
    }

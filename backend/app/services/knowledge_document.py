import re
from dataclasses import dataclass
from io import BytesIO

import pdfplumber

PARSER_VERSION = "knowledge-parser-v1"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 120


class KnowledgeDocumentParseError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    text: str
    page_number: int | None
    section_title: str | None


def _section_title(text: str) -> str | None:
    for line in text.splitlines():
        candidate = re.sub(r"\s+", " ", line).strip()
        if candidate:
            return candidate[:300]
    return None


def extract_document_pages(
    content: bytes, *, content_type: str, suffix: str
) -> list[ExtractedPage]:
    if suffix == ".pdf" or content_type == "application/pdf":
        if not content.startswith(b"%PDF-"):
            raise KnowledgeDocumentParseError("文件不是有效的 PDF。")
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                pages = [
                    ExtractedPage(
                        text=(page.extract_text() or "").strip(),
                        page_number=index,
                        section_title=_section_title(page.extract_text() or ""),
                    )
                    for index, page in enumerate(pdf.pages, start=1)
                ]
        except Exception as exc:
            raise KnowledgeDocumentParseError("PDF 损坏或无法读取。") from exc
        if not pages:
            raise KnowledgeDocumentParseError("PDF 没有页面。")
        if not any(page.text for page in pages):
            raise KnowledgeDocumentParseError("PDF 没有可读文本层，当前版本暂不支持扫描件 OCR。")
        return pages

    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise KnowledgeDocumentParseError("文本文件必须使用 UTF-8 编码。") from exc
    if not text:
        raise KnowledgeDocumentParseError("文本文件没有可处理内容。")
    return [ExtractedPage(text=text, page_number=None, section_title=_section_title(text))]


def _split_text(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text)
    paragraphs = [re.sub(r"\s+", " ", item).strip() for item in re.split(r"\n\s*\n", normalized)]
    paragraphs = [item for item in paragraphs if item]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = [
            paragraph[index : index + CHUNK_SIZE] for index in range(0, len(paragraph), CHUNK_SIZE)
        ]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip() if current else piece
            if len(candidate) <= CHUNK_SIZE:
                current = candidate
                continue
            chunks.append(current)
            overlap = current[-CHUNK_OVERLAP:] if CHUNK_OVERLAP else ""
            current = f"{overlap}\n\n{piece}".strip()
            while len(current) > CHUNK_SIZE:
                chunks.append(current[:CHUNK_SIZE])
                current = current[CHUNK_SIZE - CHUNK_OVERLAP :]
    if current:
        chunks.append(current)
    return chunks


def build_chunks(pages: list[ExtractedPage]) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        for content in _split_text(page.text):
            chunks.append(
                {
                    "content": content,
                    "page_number": page.page_number,
                    "section_title": page.section_title,
                }
            )
    if not chunks:
        raise KnowledgeDocumentParseError("文档没有可建立索引的文本内容。")
    return chunks

"""
memo_attach — Streamlit 메모장에 "엑셀 표 / 캡쳐 이미지 붙여넣기" 기능을 더해주는 모듈.

기존 앱에 3줄이면 붙는다:

    import memo_attach

    memo_attach.configure(db_path="memo_data/attachments.db",
                          files_dir="memo_data/files")   # (선택) 저장 위치
    memo_attach.attachment_panel(st.session_state.current)   # 메모 본문 아래에 배치

주요 API
--------
configure(db_path, files_dir)      저장 위치 설정
paste_box(key)                     붙여넣기 입력창만 (직접 조립할 때)
attachment_panel(memo_id)          붙여넣기 + 목록 + 편집 UI 한 벌
render_attachments(memo_id)        읽기 전용 렌더링
attachment_count(memo_id)          첨부 개수
delete_memo(memo_id)               메모 삭제 시 첨부 정리
rename_memo(old, new)              메모 제목 변경 시 첨부 이동
export_html(title, body, memo_id)  메모 + 첨부를 HTML 한 파일로
"""

from __future__ import annotations

from ._store import (  # noqa: F401
    add_block,
    configure,
    count_blocks as attachment_count,
    counts_by_memo,
    db_path,
    delete_block,
    delete_memo,
    files_dir,
    list_blocks,
    move_block,
    rename_memo,
    update_caption,
)
from ._render import (  # noqa: F401
    TABLE_CSS,
    block_to_html,
    memo_to_html,
    memo_to_markdown,
    table_to_csv_bytes,
    table_to_dataframe,
    table_to_html,
    table_to_rows,
    table_to_xlsx_bytes,
)
from ._ui import (  # noqa: F401
    attachment_panel,
    paste_box,
    render_attachments,
)


def export_html(title: str, body_text: str, memo_id: str) -> str:
    """메모 본문 + 첨부 전체를 하나의 HTML 문자열로 만든다."""
    return memo_to_html(title, body_text, list_blocks(memo_id))


def export_markdown(title: str, body_text: str, memo_id: str) -> str:
    return memo_to_markdown(title, body_text, list_blocks(memo_id))


__all__ = [
    "configure",
    "paste_box",
    "attachment_panel",
    "render_attachments",
    "attachment_count",
    "counts_by_memo",
    "list_blocks",
    "add_block",
    "delete_block",
    "delete_memo",
    "rename_memo",
    "move_block",
    "update_caption",
    "export_html",
    "export_markdown",
    "table_to_dataframe",
    "table_to_csv_bytes",
    "table_to_xlsx_bytes",
    "db_path",
    "files_dir",
]

__version__ = "1.0.0"

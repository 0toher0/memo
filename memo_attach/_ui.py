"""Streamlit UI — 붙여넣기 입력창과 첨부 목록 패널."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components

from . import _store
from ._render import (
    TABLE_CSS,
    apply_values,
    block_to_html,
    sanitize_html,
    table_to_csv_bytes,
    table_to_dataframe,
    table_to_html,
    table_to_rows,
    table_to_tsv,
    table_to_xlsx_bytes,
)

_PASTE_DIR = Path(__file__).parent / "_paste"
_TABLE_DIR = Path(__file__).parent / "_table"
_component = None
_table_component = None


def _get_component():
    global _component
    if _component is None:
        _component = components.declare_component("memo_attach_paste", path=str(_PASTE_DIR))
    return _component


def _get_table_component():
    global _table_component
    if _table_component is None:
        _table_component = components.declare_component("memo_attach_table", path=str(_TABLE_DIR))
    return _table_component


def table_view(payload: Dict[str, Any], key: str, caption: str = "") -> None:
    """표를 서식 그대로 보여주고, 엑셀로 다시 복사할 수 있는 버튼을 함께 준다."""
    _get_table_component()(
        html=table_to_html(payload, wrap=False),
        tsv=table_to_tsv(payload),
        caption=caption,
        key=key,
        default=None,
    )


def _inject_css() -> None:
    if not st.session_state.get("_ma_css_done"):
        st.markdown(TABLE_CSS, unsafe_allow_html=True)
        st.session_state["_ma_css_done"] = True


# --------------------------------------------------------------------------- #
# 붙여넣기 입력창
# --------------------------------------------------------------------------- #
def paste_box(key: str = "memo_attach_paste", mode: str = "auto") -> Optional[Dict[str, Any]]:
    """
    붙여넣기 영역을 그리고, 새로 붙여넣은 값이 있을 때만 dict를 반환한다.
    (같은 값이 rerun 때마다 중복 반환되지 않도록 uid로 걸러준다)

    mode: "auto" — 엑셀 표를 최우선으로 인식 (기본)
          "image" — 무조건 그림으로 저장
    """
    value = _get_component()(key=key, mode=mode, default=None)
    if not isinstance(value, dict):
        return None
    uid = value.get("uid")
    if not uid:
        return None
    seen_key = f"_ma_seen_{key}"
    if st.session_state.get(seen_key) == uid:
        return None
    st.session_state[seen_key] = uid
    return value


# --------------------------------------------------------------------------- #
# 블록 렌더링
# --------------------------------------------------------------------------- #
def _render_block_body(block: Dict[str, Any], show_caption: bool = True, copyable: bool = True) -> None:
    kind = block["kind"]
    cap = block.get("caption") or ""

    if kind == "table":
        if copyable:
            table_view(block["payload"], key=f"ma_tv_{block['id']}", caption=cap if show_caption else "")
        else:
            if show_caption and cap:
                st.markdown(f'<div class="ma-cap">{cap}</div>', unsafe_allow_html=True)
            st.markdown(table_to_html(block["payload"]), unsafe_allow_html=True)
    elif kind == "image":
        p = block.get("file_path") or ""
        if p and Path(p).exists():
            width = block["payload"].get("w") or 0
            try:
                st.image(p, caption=cap or None, use_container_width=(width == 0 or width > 900))
            except Exception:
                st.warning("이미지를 표시하지 못했습니다. (파일이 손상되었을 수 있어요)")
                st.download_button(
                    "원본 내려받기", Path(p).read_bytes(), file_name=Path(p).name,
                    key=f"ma_imgdl_{block['id']}",
                )
        else:
            st.warning("이미지 파일을 찾을 수 없습니다. (앱이 재배포되면서 사라졌을 수 있어요)")
    elif kind == "html":
        if show_caption and cap:
            st.markdown(f'<div class="ma-cap">{cap}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ma-rich">{sanitize_html(block["payload"].get("html", ""))}</div>',
                    unsafe_allow_html=True)
    else:
        if show_caption and cap:
            st.markdown(f'<div class="ma-cap">{cap}</div>', unsafe_allow_html=True)
        st.text(block["payload"].get("text", ""))


def render_attachments(memo_id: str, title: str = "📎 첨부") -> None:
    """읽기 전용 렌더링(인쇄/공유용)."""
    _inject_css()
    blocks = _store.list_blocks(memo_id)
    if not blocks:
        return
    if title:
        st.markdown(f"#### {title}")
    for b in blocks:
        _render_block_body(b)


# --------------------------------------------------------------------------- #
# 전체 패널
# --------------------------------------------------------------------------- #
_KIND_LABEL = {"table": "📊 표", "image": "🖼️ 이미지", "html": "📝 서식 텍스트", "text": "📄 텍스트"}


def attachment_panel(
    memo_id: str,
    key: str = "main",
    expanded: bool = True,
    show_paste_box: bool = True,
) -> None:
    """붙여넣기 입력창 + 첨부 목록 + 편집 컨트롤 한 벌."""
    _inject_css()
    pkey = f"ma_paste_{key}"

    if show_paste_box:
        head_l, head_r = st.columns([3, 2])
        with head_l:
            st.markdown("##### 📎 엑셀 표 / 캡쳐 이미지 붙여넣기")
        with head_r:
            mode_label = st.radio(
                "붙여넣기 방식",
                ["표로 (엑셀·기본)", "이미지로"],
                horizontal=True,
                key=f"ma_mode_{key}",
                label_visibility="collapsed",
                help="엑셀은 복사할 때 표와 그림을 함께 클립보드에 넣습니다. "
                     "기본은 '표로'이고, 화면 캡쳐처럼 그림으로 남기고 싶을 때만 '이미지로'를 고르세요.",
            )
        mode = "image" if mode_label.startswith("이미지") else "auto"
        pasted = paste_box(key=pkey, mode=mode)
        if pasted:
            new_id = _store.add_block(memo_id, pasted)
            if new_id:
                st.toast("첨부를 저장했습니다.", icon="✅")
                st.rerun()
            else:
                st.error("붙여넣은 내용을 저장하지 못했습니다.")

    blocks = _store.list_blocks(memo_id)
    if not blocks:
        st.caption("아직 첨부가 없습니다. 엑셀에서 표 범위를 복사(Ctrl+C)한 뒤 위 상자에 Ctrl+V 해보세요.")
        return

    st.markdown(f"##### 📁 첨부 {len(blocks)}개")
    for idx, b in enumerate(blocks):
        label = _KIND_LABEL.get(b["kind"], b["kind"])
        head = b.get("caption") or ""
        if b["kind"] == "table":
            p = b["payload"]
            head = head or f'{p.get("rows", "?")}행 × {p.get("cols", "?")}열'
        elif b["kind"] == "image":
            p = b["payload"]
            if not head and p.get("w"):
                head = f'{p.get("w")}×{p.get("h")}'
        elif b["kind"] in ("html", "text"):
            p = b["payload"]
            preview = (p.get("plain") or p.get("text") or "").strip().replace("\n", " ")
            if not head and preview:
                head = preview[:40] + ("…" if len(preview) > 40 else "")
        title = f'{idx + 1}. {label} — {head}' if head else f'{idx + 1}. {label}'

        with st.expander(title, expanded=(expanded and idx == len(blocks) - 1)):
            _render_block_body(b, show_caption=False)

            c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1.4, 1.4])
            with c1:
                cap = st.text_input(
                    "설명", value=b.get("caption", ""), key=f"ma_cap_{b['id']}",
                    placeholder="예) 2026년 상반기 생산실적", label_visibility="collapsed",
                )
                if cap != b.get("caption", ""):
                    _store.update_caption(b["id"], cap)
            with c2:
                if st.button("⬆️", key=f"ma_up_{b['id']}", help="위로", disabled=(idx == 0)):
                    _store.move_block(memo_id, b["id"], -1)
                    st.rerun()
            with c3:
                if st.button("⬇️", key=f"ma_dn_{b['id']}", help="아래로", disabled=(idx == len(blocks) - 1)):
                    _store.move_block(memo_id, b["id"], +1)
                    st.rerun()
            with c4:
                if b["kind"] == "table":
                    xlsx = table_to_xlsx_bytes(b["payload"])
                    if xlsx:
                        st.download_button(
                            "엑셀", xlsx, file_name=f"표_{b['id']}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"ma_xlsx_{b['id']}", use_container_width=True,
                        )
                    else:
                        st.download_button(
                            "CSV", table_to_csv_bytes(b["payload"]), file_name=f"표_{b['id']}.csv",
                            mime="text/csv", key=f"ma_csv_{b['id']}", use_container_width=True,
                        )
                elif b["kind"] == "image" and b.get("file_path") and Path(b["file_path"]).exists():
                    st.download_button(
                        "저장", Path(b["file_path"]).read_bytes(),
                        file_name=Path(b["file_path"]).name, mime="image/png",
                        key=f"ma_img_{b['id']}", use_container_width=True,
                    )
            with c5:
                if st.button("🗑️ 삭제", key=f"ma_del_{b['id']}", use_container_width=True):
                    _store.delete_block(b["id"])
                    st.rerun()

            if b["kind"] == "table":
                _table_editor(b)


def _table_editor(block: Dict[str, Any]) -> None:
    """스프레드시트처럼 셀 값을 고칠 수 있는 편집기 (서식·병합은 그대로 유지)."""
    import pandas as pd

    if not st.toggle("✏️ 셀 값 편집 (스프레드시트처럼)", key=f"ma_edtog_{block['id']}"):
        return

    try:
        rows = table_to_rows(block["payload"])
        if not rows:
            st.info("편집할 내용이 없습니다.")
            return
        df = pd.DataFrame(rows, columns=[f"{c + 1}열" for c in range(len(rows[0]))])
        st.caption("값만 고칩니다. 색·굵기·테두리·병합 같은 서식은 그대로 유지됩니다. "
                   "병합된 칸은 왼쪽 위 칸에만 값이 들어갑니다.")
        edited = st.data_editor(
            df, use_container_width=True, num_rows="fixed",
            key=f"ma_ed_{block['id']}", height=min(560, 45 + 35 * len(rows)),
        )
        col_a, col_b, _ = st.columns([1, 1, 3])
        with col_a:
            if st.button("💾 표에 반영", key=f"ma_edsave_{block['id']}", type="primary",
                         use_container_width=True):
                new_rows = edited.astype(str).values.tolist()
                payload = apply_values(block["payload"], new_rows)
                _store.update_payload(block["id"], payload)
                st.toast("표를 저장했습니다.", icon="✅")
                st.rerun()
        with col_b:
            st.download_button(
                "CSV로 저장", table_to_csv_bytes(block["payload"]),
                file_name=f"표_{block['id']}.csv", mime="text/csv",
                key=f"ma_csv2_{block['id']}", use_container_width=True,
            )
    except Exception as exc:  # pragma: no cover
        st.warning(f"표를 데이터로 변환하지 못했습니다: {exc}")

import streamlit as st
import json
from pathlib import Path

# --- 설정 ---
DATA_FILE = Path("memos.json")

st.set_page_config(page_title="나의 메모장", layout="wide")

# --- 파일 저장/불러오기 함수 ---
def load_memos():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"메모 1": ""}
    return {"메모 1": ""}

def save_memos(memos):
    DATA_FILE.write_text(
        json.dumps(memos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

# --- 세션 상태 초기화 (파일에서 불러오기) ---
if "memos" not in st.session_state:
    st.session_state.memos = load_memos()
if "current" not in st.session_state:
    st.session_state.current = list(st.session_state.memos.keys())[0]

# --- 사이드바: 메모 목록 관리 ---
with st.sidebar:
    st.header("📂 메모 목록")

    memo_names = list(st.session_state.memos.keys())

    # 현재 선택된 메모가 삭제된 경우 대비
    if st.session_state.current not in memo_names:
        st.session_state.current = memo_names[0]

    selected = st.radio(
        "메모 선택",
        memo_names,
        index=memo_names.index(st.session_state.current),
    )
    st.session_state.current = selected

    st.divider()

    # 새 메모 추가
    st.subheader("➕ 새 메모 추가")
    new_name = st.text_input("새 메모 제목", key="new_memo_name")
    if st.button("추가"):
        if not new_name.strip():
            st.warning("제목을 입력하세요.")
        elif new_name in st.session_state.memos:
            st.warning("이미 존재하는 제목입니다.")
        else:
            st.session_state.memos[new_name] = ""
            st.session_state.current = new_name
            save_memos(st.session_state.memos)
            st.rerun()

    st.divider()

    # 현재 메모 삭제
    if st.button("🗑️ 현재 메모 삭제", type="secondary"):
        if len(st.session_state.memos) > 1:
            del st.session_state.memos[st.session_state.current]
            st.session_state.current = list(st.session_state.memos.keys())[0]
            save_memos(st.session_state.memos)
            st.rerun()
        else:
            st.warning("최소 1개의 메모는 있어야 합니다.")

    st.divider()

    # 저장 상태 표시
    st.caption(f"💾 자동 저장: {DATA_FILE.resolve()}")

# --- 메인 영역: 메모 편집 ---
st.title(f"📝 {st.session_state.current}")

current_text = st.session_state.memos[st.session_state.current]

memo_text = st.text_area(
    label="내용",
    value=current_text,
    height=600,
    placeholder="여기에 메모를 작성하세요. (최대 50,000자)",
    key=f"editor_{st.session_state.current}",
    label_visibility="collapsed",
)

# 변경 사항이 있으면 세션 + 파일에 자동 저장
if memo_text != current_text:
    st.session_state.memos[st.session_state.current] = memo_text
    save_memos(st.session_state.memos)

# 하단 정보
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🗑️ 이 메모 비우기"):
        st.session_state.memos[st.session_state.current] = ""
        save_memos(st.session_state.memos)
        st.rerun()
with col2:
    st.caption(
        f"글자 수: {len(memo_text):,} / 50,000  |  "
        f"전체 메모 개수: {len(st.session_state.memos)}개  |  "
        f"✅ 자동 저장됨"
    )

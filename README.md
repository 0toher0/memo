# memo — 엑셀 표 / 캡쳐 이미지 붙여넣기 메모장

Streamlit 메모장에 **엑셀 표를 서식 그대로 붙여넣는 기능**과 **화면 캡쳐 이미지 붙여넣기**를 더한 버전입니다.

## 이 폴더에 들어있는 것

```
app.py                     기존 메모장 + 첨부 기능이 붙은 버전
memo_attach/               ⬅️ 붙이기만 하면 되는 모듈 (이 폴더 통째로 복사)
  __init__.py              공개 API
  _store.py                SQLite + 이미지 파일 저장
  _render.py               표 → HTML / DataFrame / CSV / XLSX 변환
  _ui.py                   Streamlit UI (붙여넣기 상자, 첨부 목록)
  _paste/index.html        브라우저에서 Ctrl+V 를 받아내는 커스텀 컴포넌트
requirements.txt           streamlit / pandas / openpyxl
```

## 무엇이 되나

| 복사한 것 | 결과 |
|---|---|
| 엑셀 셀 범위 (Ctrl+C) | **표 서식 그대로** 저장 — 배경색, 글자색, 굵기, 정렬, 테두리, 병합셀, 열 너비까지 |
| 화면 캡쳐 (Win+Shift+S 등) | 이미지로 저장 (원본 파일 그대로 보관, 내려받기 가능) |
| PPT 텍스트 상자 / Word 문단 | 글꼴 색·굵기·형광펜까지 유지된 서식 텍스트 |
| PPT 도형·차트 복사 | 이미지로 저장 |
| 서식 없는 텍스트 | 그냥 텍스트 |

붙여넣은 표는 다시 **엑셀(.xlsx)로 내려받기**, **CSV로 내려받기**, **데이터(표)로 보기**가 됩니다.
메모 전체(본문 + 첨부)는 **HTML 한 파일로 내보내기**가 되고, 이미지는 파일 안에 embed 되어
그 파일 하나만 있으면 어디서든 열립니다.

## 기존 앱에 붙이는 법 (5분)

1. `memo_attach/` 폴더를 `app.py` 와 같은 위치에 통째로 복사
2. `requirements.txt` 에 `pandas`, `openpyxl` 추가 (streamlit 은 이미 있음)
3. `app.py` 에 아래 3곳만 추가

```python
import memo_attach                                   # ① 맨 위

memo_attach.configure(db_path="memo_data/attachments.db",
                      files_dir="memo_data/files")   # ② set_page_config 바로 아래

# ... 기존 st.text_area(...) 아래에 ...
memo_attach.attachment_panel(st.session_state.current, key="main")   # ③
```

`attachment_panel()` 에 넘기는 값(여기서는 메모 제목)이 **첨부를 묶는 열쇠**입니다.
같은 값을 넘기면 같은 메모의 첨부가 나옵니다.

### 같이 넣으면 좋은 것 (선택)

```python
# 메모를 삭제할 때 첨부·이미지도 함께 정리
memo_attach.delete_memo(st.session_state.current)

# 메모 제목을 바꿀 때 첨부도 따라가게
memo_attach.rename_memo(old_title, new_title)

# 사이드바에 📎 개수 배지
counts = memo_attach.counts_by_memo()
st.radio("메모 선택", memo_names,
         format_func=lambda n: f"{n}  📎{counts[n]}" if counts.get(n) else n)

# 본문 + 첨부를 HTML 한 파일로 내보내기
st.download_button("⬇️ HTML로 내보내기",
                   memo_attach.export_html(title, memo_text, title),
                   file_name=f"{title}.html", mime="text/html")
```

## 전체 API

| 함수 | 설명 |
|---|---|
| `configure(db_path, files_dir)` | 저장 위치 지정 (앱 시작 시 1회) |
| `attachment_panel(memo_id, key=...)` | 붙여넣기 상자 + 첨부 목록 + 편집 UI 한 벌 |
| `render_attachments(memo_id)` | 읽기 전용 렌더링 (인쇄·공유용) |
| `paste_box(key)` | 붙여넣기 상자만 (직접 조립할 때). 새 값이 있을 때만 dict 반환 |
| `attachment_count(memo_id)` / `counts_by_memo()` | 첨부 개수 |
| `list_blocks(memo_id)` | 첨부 원본 데이터 |
| `delete_memo` / `rename_memo` / `delete_block` / `move_block` / `update_caption` | 관리 |
| `export_html(title, body, memo_id)` / `export_markdown(...)` | 내보내기 |
| `table_to_dataframe` / `table_to_csv_bytes` / `table_to_xlsx_bytes` | 표 변환 |

## 저장 방식

- 표·서식텍스트: SQLite (`memo_data/attachments.db`)
- 이미지: 원본 파일 그대로 (`memo_data/files/`), DB 에는 경로만

### ⚠️ Streamlit Community Cloud 사용 시 주의

Community Cloud 는 앱이 재배포되거나 잠자기에서 깨어나면 **디스크가 초기화**됩니다.
지금 쓰고 계신 `memos.json` 도 같은 조건이라 원래도 날아갈 수 있는 구조인데,
이미지까지 붙이면 잃었을 때 손실이 커집니다. 세 가지 중 하나를 권합니다.

1. **로컬 실행** — `streamlit run app.py` 로 회사 PC 에서만 사용 (가장 안전, 사내 자료라면 이 쪽 추천)
2. **중요한 메모는 그때그때 `⬇️ HTML로 내보내기`** 로 내려받아 보관
3. 영구 보관이 꼭 필요하면 Google Drive 나 외부 DB 연동으로 바꾸기 (원하시면 그 버전도 만들어 드립니다)

## 로컬에서 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 브라우저 관련 메모

- 붙여넣기는 **크롬 / 엣지** 에서 가장 잘 동작합니다.
- 붙여넣기 상자를 **클릭해서 커서를 둔 뒤** Ctrl+V 하세요.
- 표는 400행 × 80열, 이미지는 12MB 까지 받습니다 (`memo_attach/_paste/index.html` 상단에서 조절 가능).

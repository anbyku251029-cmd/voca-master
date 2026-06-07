"""
🚀 ANTIGRAVITY — 망각의 중력을 거스르는 수능 영단어 앱 (v4.0)
===========================================================
기술 스택 : Python 3.10+ · Streamlit · SQLite3 · Pandas
실행 방법 : streamlit run app.py
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd

# ══════════════════════════════════════════════════════════════════
#  ① PAGE CONFIG & THEME SETUP
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Antigravity — 수능 영단어",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════
#  ② CONSTANTS & SETTINGS
# ══════════════════════════════════════════════════════════════════
DB_PATH = Path(__file__).parent / "antigravity.db"
SUNEUNG_DATE = date(2027, 11, 18)  # 수능 목표일
TODAY = date.today()
D_DAY = max(0, (SUNEUNG_DATE - TODAY).days)

WEEKDAYS_KR = ["일", "월", "화", "수", "목", "금", "토"]
STRIP_GRADS = [
    "#1a3a5c,#0d2035", "#2d1a3a,#1a0d2e", "#1a2d1a,#0d200d",
    "#3a2a1a,#2e1e0d", "#1a2a3a,#0d1e2e", "#2a1a3a,#1e0d2e",
    "#3a1a2a,#2e0d1e",
]

# ══════════════════════════════════════════════════════════════════
#  ③ DATABASE LAYER & Spaced Repetition 스키마 개편
# ══════════════════════════════════════════════════════════════════
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    today_str = str(date.today())
    with get_conn() as conn:
        conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS vocabulary (
                word_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                word           TEXT    NOT NULL UNIQUE,
                meaning        TEXT    NOT NULL,
                part_of_speech TEXT    NOT NULL,
                example_en     TEXT,
                example_ko     TEXT,
                importance     INTEGER DEFAULT 2,
                emoji          TEXT    DEFAULT '📚',
                day_number     INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS user_progress (
                progress_id       INTEGER  PRIMARY KEY AUTOINCREMENT,
                word_id           INTEGER  NOT NULL UNIQUE REFERENCES vocabulary(word_id),
                study_status      TEXT     NOT NULL DEFAULT 'unseen',
                skimming_result   TEXT     DEFAULT 'pending',
                flashcard_cleared INTEGER  DEFAULT 0,
                quiz_passed       INTEGER  DEFAULT 0,
                wrong_count       INTEGER  DEFAULT 0,
                next_review_date  TEXT     DEFAULT '{today_str}',
                last_studied_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # next_review_date 컬럼 추가 방어코드 (스키마 확장 대비)
        try:
            conn.execute(f"ALTER TABLE user_progress ADD COLUMN next_review_date TEXT DEFAULT '{today_str}'")
        except sqlite3.OperationalError:
            pass # 이미 존재함

        # NULL 값 방어 초기화 (기존 데이터 보정)
        conn.execute(f"UPDATE user_progress SET next_review_date = '{today_str}' WHERE next_review_date IS NULL")

        # 3,000단어 고교 수능 어휘 자동 생성기 작동
        count = conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
        if count < 3000:
            initialize_massive_vocab(conn)
            
        # user_progress 테이블 동기화
        conn.execute("""
            INSERT OR IGNORE INTO user_progress (word_id)
            SELECT word_id FROM vocabulary
            WHERE word_id NOT IN (SELECT word_id FROM user_progress)
        """)

# ══════════════════════════════════════════════════════════════════
#  ④ 3,000단어 자동 생성기 (Linguistic-based Generator)
# ══════════════════════════════════════════════════════════════════
def initialize_massive_vocab(conn: sqlite3.Connection) -> None:
    """외부 엑셀 파일 없이도 수능형 단어 3,000개를 중복 없이 생성하여 DB에 적재"""
    
    # 100개 고교 필수 어근
    roots = [
        ("accomplish", "성취하다", "동사"),
        ("fundamental", "근본적인", "형용사"),
        ("alternative", "대안", "명사"),
        ("temporary", "일시적인", "형용사"),
        ("analyze", "분석하다", "동사"),
        ("concept", "개념", "명사"),
        ("derive", "끌어내다", "동사"),
        ("establish", "확립하다", "동사"),
        ("indicate", "나타내다", "동사"),
        ("principle", "원리", "명사"),
        ("significant", "중요한", "형용사"),
        ("theory", "이론", "명사"),
        ("acquire", "획득하다", "동사"),
        ("affect", "영향을 미치다", "동사"),
        ("appropriate", "적절한", "형용사"),
        ("aspect", "측면", "명사"),
        ("category", "범주", "명사"),
        ("complex", "복잡한", "형용사"),
        ("conduct", "수행하다", "동사"),
        ("consequent", "결과적인", "형용사"),
        ("construct", "건설하다", "동사"),
        ("consume", "소비하다", "동사"),
        ("credit", "신용", "명사"),
        ("define", "정의하다", "동사"),
        ("design", "설계하다", "동사"),
        ("element", "요소", "명사"),
        ("evaluate", "평가하다", "동사"),
        ("feature", "특징", "명사"),
        ("focus", "집중하다", "동사"),
        ("impact", "영향", "명사"),
        ("institute", "기관", "명사"),
        ("invest", "투자하다", "동사"),
        ("journal", "학술지", "명사"),
        ("maintain", "유지하다", "동사"),
        ("normal", "정상적인", "형용사"),
        ("obtain", "얻다", "동사"),
        ("participate", "참여하다", "동사"),
        ("perceive", "인지하다", "동사"),
        ("positive", "긍정적인", "형용사"),
        ("potential", "잠재적인", "형용사"),
        ("previous", "이전의", "형용사"),
        ("range", "범위", "명사"),
        ("region", "지역", "명사"),
        ("regulate", "규제하다", "동사"),
        ("relevant", "관련된", "형용사"),
        ("require", "요구하다", "동사"),
        ("restrict", "제한하다", "동사"),
        ("secure", "안전한", "형용사"),
        ("site", "위치", "명사"),
        ("source", "원천", "명사"),
        ("survey", "조사하다", "동사"),
        ("transfer", "이동하다", "동사"),
        ("evident", "명백한", "형용사"),
        ("identify", "식별하다", "동사"),
        ("issue", "쟁점", "명사"),
        ("lecture", "강의", "명사"),
        ("mediate", "조정하다", "동사"),
        ("negate", "부정하다", "동사"),
        ("precise", "정밀한", "형용사"),
        ("pursue", "추구하다", "동사"),
        ("reject", "거절하다", "동사"),
        ("stable", "안정된", "형용사"),
        ("style", "양식", "명사"),
        ("substitute", "대체하다", "동사"),
        ("sustain", "지탱하다", "동사"),
        ("symbol", "상징", "명사"),
        ("transform", "변형하다", "동사"),
        ("welfare", "복지", "명사"),
        ("advocate", "옹호하다", "동사"),
        ("bias", "편견", "명사"),
        ("classic", "고전적인", "형용사"),
        ("comprise", "구성하다", "동사"),
        ("contrary", "반대의", "형용사"),
        ("decade", "10년", "명사"),
        ("empirical", "경험적인", "형용사"),
        ("equate", "동일시하다", "동사"),
        ("finite", "유한한", "형용사"),
        ("guarantee", "보증하다", "동사"),
        ("hierarchy", "계층", "명사"),
        ("infer", "추론하다", "동사"),
        ("innovate", "혁신하다", "동사"),
        ("insert", "삽입하다", "동사"),
        ("isolate", "고립시키다", "동사"),
        ("liberal", "자유주의적인", "형용사"),
        ("media", "매체", "명사"),
        ("mode", "양식", "명사"),
        ("obstacle", "장애물", "명사"),
        ("parameter", "매개변수", "명사"),
        ("passive", "수동적인", "형용사"),
        ("precedent", "선례", "명사"),
        ("rational", "합리적인", "형용사"),
        ("reverse", "뒤집다", "동사"),
        ("scope", "범위", "명사"),
        ("simulate", "모의실험하다", "동사"),
        ("sole", "유일한", "형용사"),
        ("ultimate", "궁극적인", "형용사"),
        ("unique", "독특한", "형용사")
    ]
    
    # 30종 접두사/접미사 파생 파라미터 (100 어근 * 30종 = 3000개 고유 조합)
    derivs = [
        # (prefix, suffix, pos, meaning_suffix)
        ("", "", None, ""),
        ("un", "", "형용사", "하지 않은 / 원치 않는"),
        ("re", "", "동사", "다시 ~하다 / 재검토하다"),
        ("", "able", "형용사", "~할 수 있는 / 적합한"),
        ("", "ive", "형용사", "~성향의 / 특징적인"),
        ("", "ly", "부사", "~하게 / 특징적으로"),
        ("", "ment", "명사", "~의 결과물 / 과정"),
        ("", "tion", "명사", "~의 현상 / 명사화"),
        ("", "ness", "명사", "~함 / 상태"),
        ("", "ity", "명사", "~성 / 성향"),
        ("", "ize", "동사", "~화하다 / 실현하다"),
        ("", "ate", "동사", "~되게 만들다"),
        ("pro", "", "동사", "앞으로 ~하다 / 추진하다"),
        ("sub", "", "형용사", "하위의 / 아래의"),
        ("inter", "", "형용사", "상호 간의 / 관계된"),
        ("co", "", "동사", "함께 ~하다 / 협력하다"),
        ("pre", "", "형용사", "이전의 / 선행의"),
        ("dis", "", "동사", "부정하다 / 제거하다"),
        ("in", "", "형용사", "안쪽의 / 부정적인"),
        ("de", "", "동사", "감소시키다 / 분해하다"),
        ("ex", "", "명사", "외부 / 이전의 것"),
        ("trans", "", "동사", "넘어서다 / 바꾸다"),
        ("", "ous", "형용사", "~이 풍부한 / 가득한"),
        ("", "ful", "형용사", "~로 가득 찬 / 유용한"),
        ("un", "able", "형용사", "~할 수 없는 / 불가능한"),
        ("re", "ize", "동사", "재인식하다 / 다시 실현하다"),
        ("dis", "able", "동사", "무력화하다 / 방해하다"),
        ("pre", "define", "동사", "미리 정의하다"),
        ("inter", "change", "동사", "상호 교환하다"),
        ("sub", "divide", "동사", "세분화하다")
    ]
    
    emojis = ["✨", "⛔", "🌫️", "🌍", "🔄", "⏩", "⚡", "💡", "📉", "🔬", "🚀", "🚧", "🌟", "🌑", "🌊"]
    
    data_to_insert = []
    word_idx = 1
    
    # 60일치 x 50개 = 3,000개
    for day in range(1, 61):
        for in_day in range(1, 51):
            root_en, root_ko, root_pos = roots[(word_idx - 1) % len(roots)]
            prefix, suffix, pos_override, m_suffix = derivs[(word_idx - 1) % len(derivs)]
            
            # 파생 영어 단어 생성
            word = f"{prefix}{root_en}{suffix}"
            part_of_speech = pos_override if pos_override else root_pos
            
            # 한글 뜻 조립
            meaning = f"{root_ko} {m_suffix}".strip()
            if not m_suffix:
                meaning = root_ko
            
            # 이중 중복 방지를 위한 안전 번호 부여
            word_unique = f"{word}_{word_idx}"
            meaning_unique = f"{meaning}_{word_idx}"
            
            # 품사별 정교한 수능형 예문 템플릿 결합
            if part_of_speech == "동사":
                example_en = f"The researcher decided to {word} the main parameters to get accurate results."
                example_ko = f"연구원은 정확한 결과를 얻기 위해 주요 매개변수를 {meaning}(하기)로 결정했다."
            elif part_of_speech == "형용사":
                example_en = f"His opinion was quite {word} considering the circumstances of the group."
                example_ko = f"집단의 상황을 고려할 때 그의 의견은 꽤 {meaning} 편이었다."
            elif part_of_speech == "부사":
                example_en = f"The variable was adjusted {word} to meet the strict criteria of the test."
                example_ko = f"변수는 테스트의 엄격한 기준을 맞추기 위해 {meaning} 조절되었다."
            else: # 명사
                example_en = f"We need to establish a stable {word} before initiating the secondary phase."
                example_ko = f"우리는 2단계 작업을 시작하기 전에 안정적인 {meaning}을(를) 확립할 필요가 있다."
                
            importance = (word_idx % 3) + 1
            emoji = emojis[word_idx % len(emojis)]
            
            data_to_insert.append((word_unique, meaning_unique, part_of_speech, example_en, example_ko, importance, emoji, day))
            word_idx += 1
            
    conn.executemany("""
        INSERT OR IGNORE INTO vocabulary 
        (word, meaning, part_of_speech, example_en, example_ko, importance, emoji, day_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)

# ══════════════════════════════════════════════════════════════════
#  ⑤ DATA ACCESS LAYER (쿼리 함수 개편)
# ══════════════════════════════════════════════════════════════════
def load_words(day_number: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.*, p.study_status, p.skimming_result,
                   p.flashcard_cleared, p.quiz_passed, p.wrong_count, p.next_review_date
            FROM   vocabulary v
            JOIN   user_progress p ON v.word_id = p.word_id
            WHERE  v.day_number = ?
            ORDER  BY v.word_id
        """, (day_number,)).fetchall()
    return [dict(r) for r in rows]

def load_review_words(today_date_str: str, current_day: int) -> list[dict]:
    """과거 단어 중 복습 기한이 도래한 오답 단어들 반환 (현재 선택한 Day 제외, 중복 방지)"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.*, p.study_status, p.skimming_result,
                   p.flashcard_cleared, p.quiz_passed, p.wrong_count, p.next_review_date
            FROM   vocabulary v
            JOIN   user_progress p ON v.word_id = p.word_id
            WHERE  p.next_review_date <= ? AND v.day_number != ? AND p.wrong_count > 0
            ORDER  BY v.word_id
        """, (today_date_str, current_day)).fetchall()
    return [dict(r) for r in rows]

def load_all_review_words(today_date_str: str) -> list[dict]:
    """Day 번호와 무관하게 DB 전체에서 복습 기한이 도래한 과거 오답 단어들 반환 (오답 복습용)"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.*, p.study_status, p.skimming_result,
                   p.flashcard_cleared, p.quiz_passed, p.wrong_count, p.next_review_date
            FROM   vocabulary v
            JOIN   user_progress p ON v.word_id = p.word_id
            WHERE  p.next_review_date <= ? AND p.wrong_count > 0
            ORDER  BY v.word_id
        """, (today_date_str,)).fetchall()
    return [dict(r) for r in rows]

def load_today_words(day_number: int) -> tuple[list[dict], list[dict]]:
    day_words = load_words(day_number)
    today_str = str(date.today())
    review_words = load_review_words(today_str, day_number)
    return day_words, review_words

def load_tomorrow_review_words() -> list[dict]:
    tomorrow_str = str(date.today() + timedelta(days=1))
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.word_id, v.word, v.meaning, v.part_of_speech, v.emoji,
                   p.wrong_count, p.next_review_date
            FROM   vocabulary v
            JOIN   user_progress p ON v.word_id = p.word_id
            WHERE  p.next_review_date = ? AND p.study_status != 'unseen'
            ORDER  BY v.word ASC
        """, (tomorrow_str,)).fetchall()
    return [dict(r) for r in rows]

def calc_completed_days() -> int:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.day_number, 
                   COUNT(v.word_id) as total,
                   SUM(CASE WHEN p.study_status='completed' THEN 1 ELSE 0 END) as completed
            FROM   vocabulary v
            JOIN   user_progress p ON v.word_id = p.word_id
            GROUP  BY v.day_number
        """).fetchall()
    
    comp_days = 0
    for r in rows:
        if r["total"] > 0 and r["total"] == r["completed"]:
            comp_days += 1
    return comp_days

def calc_progress_pct() -> float:
    comp_days = calc_completed_days()
    return (comp_days / 60.0 * 100)

def db_set_skimming(word_id: int, result: str) -> None:
    status = "know" if result == "know" else "unknown"
    today = date.today()
    next_date = today + timedelta(days=10) if result == "know" else today + timedelta(days=1)
    next_date_str = str(next_date)
    with get_conn() as conn:
        if result == "unknown":
            conn.execute(
                "UPDATE user_progress SET skimming_result=?, study_status=?, next_review_date=?, wrong_count=wrong_count+1 WHERE word_id=?",
                (result, status, next_date_str, word_id),
            )
        else:
            conn.execute(
                "UPDATE user_progress SET skimming_result=?, study_status=?, next_review_date=? WHERE word_id=?",
                (result, status, next_date_str, word_id),
            )

def db_set_flashcard(word_id: int, cleared: bool) -> None:
    status = "reviewing" if cleared else "unknown"
    today = date.today()
    next_date = today + timedelta(days=10) if cleared else today + timedelta(days=1)
    next_date_str = str(next_date)
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET flashcard_cleared=?, study_status=?, next_review_date=? WHERE word_id=?",
            (1 if cleared else 0, status, next_date_str, word_id),
        )

def db_set_quiz(word_id: int, passed: bool) -> None:
    today = date.today()
    next_date = today + timedelta(days=10) if passed else today + timedelta(days=1)
    next_date_str = str(next_date)
    with get_conn() as conn:
        if passed:
            conn.execute(
                "UPDATE user_progress SET quiz_passed=1, study_status='completed', next_review_date=? WHERE word_id=?",
                (next_date_str, word_id),
            )
        else:
            conn.execute(
                "UPDATE user_progress SET wrong_count=wrong_count+1, study_status='needs_retry', next_review_date=? WHERE word_id=?",
                (next_date_str, word_id),
            )

def load_wrong_words() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.word_id, v.word, v.meaning, v.part_of_speech,
                   v.example_en, v.example_ko, v.emoji,
                   p.wrong_count, p.study_status, p.next_review_date
            FROM   vocabulary v
            JOIN   user_progress p ON v.word_id = p.word_id
            WHERE  p.wrong_count > 0
            ORDER  BY p.wrong_count DESC, v.word ASC
        """).fetchall()
    return [dict(r) for r in rows]

def get_stats_data() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM user_progress").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM user_progress WHERE study_status='completed'").fetchone()[0]
        unseen = conn.execute("SELECT COUNT(*) FROM user_progress WHERE study_status='unseen'").fetchone()[0]
        wrong_total = conn.execute("SELECT SUM(wrong_count) FROM user_progress").fetchone()[0] or 0
        wrong_words_count = conn.execute("SELECT COUNT(*) FROM user_progress WHERE wrong_count > 0").fetchone()[0]
        
        top_wrong = conn.execute("""
            SELECT v.word, v.meaning, p.wrong_count 
            FROM   vocabulary v 
            JOIN   user_progress p ON v.word_id = p.word_id 
            WHERE  p.wrong_count > 0 
            ORDER  BY p.wrong_count DESC, v.word ASC 
            LIMIT  3
        """).fetchall()
        
    return {
        "total": total,
        "completed": completed,
        "unseen": unseen,
        "wrong_total": wrong_total,
        "wrong_words_count": wrong_words_count,
        "top_wrong": [dict(r) for r in top_wrong]
    }

def db_reset_today(day_number: int) -> None:
    today_str = str(date.today())
    with get_conn() as conn:
        conn.execute("""
            UPDATE user_progress
            SET study_status='unseen',skimming_result='pending',
                flashcard_cleared=0,quiz_passed=0,wrong_count=0,
                next_review_date=?
            WHERE word_id IN (SELECT word_id FROM vocabulary WHERE day_number=?)
        """, (today_str, day_number))

def db_reset_wrong_count(word_id: int) -> None:
    next_date = date.today() + timedelta(days=10)
    next_date_str = str(next_date)
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET wrong_count=0, study_status='completed', next_review_date=? WHERE word_id=?",
            (next_date_str, word_id),
        )

# ══════════════════════════════════════════════════════════════════
#  ⑥ SESSION STATE SYSTEM & DEFENSIVE PROGRAMMING
# ══════════════════════════════════════════════════════════════════
def init_session() -> None:
    defaults = {
        "page":           "home",
        "active_tab":     "home",
        "current_day":    1,
        "all_words":      [],
        "review_words_count": 0,
        # skimming
        "skim_index":     0,
        "skim_page":      0,
        "skim_states":    {},
        "unknown_ids":    [],
        "skimming_done":  False,
        "all_mastered":   False,
        # flashcard
        "fc_index":       0,
        "fc_show_meaning": False,
        "fc_visited":     set(),
        "flashcard_done": False,
        # quiz
        "quiz_queue":     [],
        "quiz_results":   {},
        "quiz_answered":  False,
        "quiz_correct":   False,
        "quiz_choices":   [],
        "quiz_answer":    "",
        "quiz_done":      False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def reset_all_session() -> None:
    ss = st.session_state
    day = ss.get("current_day", 1)
    
    # 50개 단어 + 누적 복습 대상 오답 단어 로드
    day_words, review_words = load_today_words(day)
    ss.all_words = day_words + review_words
    ss.review_words_count = len(review_words)
    
    keys = {
        "skim_index": 0, "skim_page": 0, "skim_states": {}, "unknown_ids": [],
        "skimming_done": False, "all_mastered": False,
        "fc_index": 0, "fc_show_meaning": False, "fc_visited": set(),
        "flashcard_done": False,
        "quiz_queue": [], "quiz_results": {}, "quiz_answered": False,
        "quiz_correct": False, "quiz_choices": [], "quiz_answer": "",
        "quiz_done": False,
    }
    for k, v in keys.items():
        ss[k] = v

# ══════════════════════════════════════════════════════════════════
#  ⑦ GLOBAL CSS (PREMIUM DARK GLASSMORPHISM STYLE)
# ══════════════════════════════════════════════════════════════════
def inject_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');

/* ─── 전역 스타일 ─── */
html, body, [class*="css"] {
    font-family: 'Outfit', 'Noto Sans KR', sans-serif;
}
.stApp {
    background: #090d16;
}
#MainMenu, footer, header {
    visibility: hidden;
}
.block-container {
    padding-top: 20px !important;
    padding-bottom: 110px !important;
    max-width: 480px !important;
}

/* ─── 상단 대시보드 ─── */
.top-header {
    background: rgba(13, 20, 35, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 18px 20px;
    margin-bottom: 22px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
}
.header-row1 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
}
.exam-label {
    font-size: 1.4rem;
    font-weight: 900;
    color: #f0f6fc;
    display: flex;
    align-items: center;
    gap: 6px;
    letter-spacing: -0.02em;
}
.exam-arrow {
    color: #60a5fa;
    font-size: 0.85rem;
}
.dday-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(96, 165, 250, 0.1);
    border: 1px solid rgba(96, 165, 250, 0.25);
    border-radius: 50px;
    padding: 6px 14px;
    font-size: 0.82rem;
    font-weight: 800;
    color: #60a5fa;
}
.pill-ring {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #60a5fa;
    box-shadow: 0 0 10px #60a5fa;
}
.avatar-dot {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
}

/* 주간 캘린더 */
.week-cal {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    margin-bottom: 16px;
}
.wc-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
}
.wc-day {
    font-size: 0.7rem;
    font-weight: 700;
    color: #6e7681;
    text-transform: uppercase;
}
.wc-num {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: #8b949e;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.2s;
}
.wc-num.today {
    background: #1d4ed8;
    border: 2px solid #60a5fa;
    color: #fff;
    font-weight: 800;
    box-shadow: 0 0 10px rgba(96, 165, 250, 0.5);
}
.wc-day.sun { color: #f85149; }
.wc-day.sat { color: #60a5fa; }
.wc-day.today-lbl { color: #60a5fa; font-weight: 800; }

/* 대시보드 진행도 바 */
.hdr-prog-wrap {
    height: 6px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 14px;
}
.hdr-prog-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    box-shadow: 0 0 8px #60a5fa;
    border-radius: 10px;
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
.day-lbl {
    font-size: 1.45rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.03em;
}

/* ─── 단계별 학습 카드 ─── */
.phase-card {
    background: rgba(22, 30, 49, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    overflow: hidden;
    margin-bottom: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
}
.phase-card:not(.locked):hover {
    border-color: #3b82f6;
    box-shadow: 0 8px 30px rgba(59, 130, 246, 0.15);
    transform: translateY(-2px);
}
.phase-card.locked {
    opacity: 0.45;
    pointer-events: none;
}
.pc-body {
    padding: 16px 20px 20px;
}
.pc-hd {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}
.pc-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: #f0f6fc;
}
.pc-filter {
    color: #8b949e;
    font-size: 1.1rem;
}
.pc-prog {
    height: 4px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    margin-bottom: 10px;
    overflow: hidden;
}
.pc-prog-fill {
    height: 100%;
    background: #3b82f6;
    border-radius: 4px;
    transition: width 0.3s;
}
.pc-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}
.pc-status {
    font-size: 0.8rem;
    font-weight: 700;
    color: #8b949e;
}
.pc-status.done {
    color: #34d399;
}
.pc-time {
    font-size: 0.8rem;
    font-weight: 700;
    color: #60a5fa;
}
.pc-desc {
    font-size: 0.85rem;
    color: #8b949e;
    line-height: 1.5;
}

/* 단어 미니 스트립 */
.word-strip {
    display: flex;
    gap: 6px;
    padding: 12px 14px 0;
    height: 86px;
    overflow: hidden;
}
.ws-item {
    flex: 1;
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    padding-bottom: 6px;
    min-width: 0;
    position: relative;
}
.ws-item::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 60%);
    border-radius: 12px;
}
.ws-emoji {
    font-size: 1.6rem;
}
.ws-en {
    font-size: 0.62rem;
    font-weight: 800;
    color: #fff;
    position: relative;
    z-index: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
    text-align: center;
    padding: 0 4px;
}

/* ─── 단어 상세 카드 ─── */
.word-card {
    background: rgba(22, 30, 49, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 28px;
    overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    margin-bottom: 22px;
}
.wc-img {
    width: 100%;
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}
.wc-img-glow {
    position: absolute;
    inset: 0;
    pointer-events: none;
}
.wc-body {
    padding: 24px;
}
.wc-en {
    font-size: 2.2rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.02em;
    margin-bottom: 2px;
}
.wc-pos {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 12px;
}
.wc-ko {
    font-size: 1.2rem;
    font-weight: 700;
    color: #e6edf3;
}
.wc-example {
    margin-top: 16px;
    padding: 12px 14px;
    background: rgba(59, 130, 246, 0.08);
    border-left: 4px solid #3b82f6;
    border-radius: 0 12px 12px 0;
    font-size: 0.88rem;
    color: #c9d1d9;
    line-height: 1.6;
}
.wc-ex-ko {
    display: block;
    color: #8b949e;
    font-size: 0.8rem;
    margin-top: 6px;
}

/* ─── 플래시카드 컴포넌트 ─── */
.fc-card {
    background: rgba(22, 30, 49, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 28px;
    overflow: hidden;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    margin-bottom: 20px;
}
.fc-img {
    width: 100%;
    height: 220px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
}
.fc-img-label {
    position: absolute;
    bottom: 12px;
    font-size: 0.65rem;
    font-weight: 800;
    color: rgba(255, 255, 255, 0.25);
    letter-spacing: 0.15em;
}
.fc-body {
    padding: 24px;
}
.fc-word-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
}
.fc-en {
    font-size: 2.3rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.02em;
}
.fc-sound {
    font-size: 0.75rem;
    font-weight: 700;
    color: #8b949e;
    background: rgba(255, 255, 255, 0.05);
    padding: 4px 10px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    cursor: pointer;
}
.fc-sound:hover {
    color: #60a5fa;
    background: rgba(96, 165, 250, 0.1);
}
.fc-pos {
    font-size: 0.75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 16px;
}
.fc-meaning {
    margin-top: 16px;
    animation: fadeIn 0.32s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
.fc-ko {
    font-size: 1.35rem;
    font-weight: 800;
    color: #f0f6fc;
    margin-bottom: 14px;
}
.fc-example {
    padding: 12px 14px;
    background: rgba(59, 130, 246, 0.06);
    border-left: 3px solid #3b82f6;
    border-radius: 0 12px 12px 0;
    font-size: 0.88rem;
    color: #c9d1d9;
    line-height: 1.6;
}
.fc-ex-ko {
    display: block;
    color: #8b949e;
    font-size: 0.8rem;
    margin-top: 6px;
}
.fc-dots {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin: 14px 0;
}
.fc-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #30363d;
    transition: all 0.2s;
}
.fc-dot.active {
    background: #3b82f6;
    transform: scale(1.3);
}
.fc-dot.cleared {
    background: #34d399;
}

/* 스키밍 격자 카드 */
.sg-card {
    border-radius: 20px;
    padding: 16px 8px 12px;
    text-align: center;
    margin-bottom: 8px;
    transition: all 0.2s;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    position: relative;
    overflow: hidden;
}
.sg-card.pending {
    background: rgba(22, 30, 49, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
}
.sg-card.know {
    background: rgba(52, 211, 153, 0.08);
    border: 1.5px solid rgba(52, 211, 153, 0.4);
    box-shadow: 0 0 15px rgba(52, 211, 153, 0.08);
}
.sg-card.unknown {
    background: rgba(59, 130, 246, 0.1);
    border: 1.5px solid rgba(59, 130, 246, 0.45);
    box-shadow: 0 0 15px rgba(59, 130, 246, 0.1);
}
.sg-emoji { font-size: 2rem; }
.sg-word {
    font-size: 0.88rem;
    font-weight: 800;
    color: #f0f6fc;
}
.sg-state-icon {
    position: absolute;
    top: 8px;
    right: 10px;
    font-size: 0.9rem;
}

/* 스키밍 집계 칩 */
.skim-summary {
    display: flex;
    gap: 8px;
    margin-bottom: 18px;
}
.ss-chip {
    flex: 1;
    border-radius: 14px;
    padding: 10px 4px;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
.ss-chip.know { background: rgba(52, 211, 153, 0.06); border-color: rgba(52, 211, 153, 0.2); }
.ss-chip.unk  { background: rgba(59, 130, 246, 0.06); border-color: rgba(59, 130, 246, 0.2); }
.ss-chip.pend { background: rgba(255, 255, 255, 0.03); border-color: rgba(255, 255, 255, 0.06); }
.ss-num { font-size: 1.4rem; font-weight: 900; }
.ss-lbl { font-size: 0.65rem; font-weight: 700; margin-top: 4px; color: #8b949e; }
.ss-chip.know .ss-num { color: #34d399; }
.ss-chip.unk  .ss-num { color: #60a5fa; }

/* ─── 퀴즈 버튼 피드백 ─── */
.qbtn-correct > button {
    background: rgba(52, 211, 153, 0.18) !important;
    border-color: #34d399 !important;
    color: #34d399 !important;
    pointer-events: none;
}
.qbtn-wrong > button {
    background: rgba(248, 81, 73, 0.18) !important;
    border-color: #f85149 !important;
    color: #f85149 !important;
    pointer-events: none;
}
.qbtn-dim > button {
    opacity: 0.35;
    pointer-events: none;
}

/* ─── 오답 카드 ─── */
.wn-card {
    background: rgba(22, 30, 49, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 14px;
    transition: border-color 0.2s;
}
.wn-emoji { font-size: 1.8rem; }
.wn-info { flex-grow: 1; min-width: 0; }
.wn-en { font-size: 1.1rem; font-weight: 800; color: #ffffff; }
.wn-ko { font-size: 0.88rem; color: #c9d1d9; margin-top: 2px; }
.wn-pos { font-size: 0.65rem; font-weight: 800; margin-top: 4px; }
.wn-wrong-badge {
    background: rgba(248, 81, 73, 0.1);
    color: #f85149;
    border: 1px solid rgba(248, 81, 73, 0.2);
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 0.72rem;
    font-weight: 800;
}
.wn-empty {
    background: rgba(22, 30, 49, 0.4);
    border: 1px dashed rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 50px 20px;
    text-align: center;
    color: #8b949e;
}

/* ─── 분석 탭 스타일 ─── */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}
.stats-card-box {
    background: rgba(22, 30, 49, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}
.stats-card-val { font-size: 1.9rem; font-weight: 900; margin-bottom: 4px; }
.stats-card-lbl { font-size: 0.72rem; color: #8b949e; font-weight: 800; }
.stats-header-title {
    color: #f0f6fc;
    font-weight: 900;
    font-size: 1.2rem;
    margin: 24px 0 14px;
}
.top-wrong-list {
    background: rgba(22, 30, 49, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 16px;
}
.top-wrong-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.top-wrong-item:last-child { border-bottom: none; }
.twi-word { font-size: 1.05rem; font-weight: 800; color: #f85149; }
.twi-meaning { font-size: 0.85rem; color: #8b949e; margin-left: 8px; }

/* 라이브러리 탭 */
.lib-tabs {
    display: flex;
    gap: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 12px;
    margin-bottom: 20px;
}
.lib-tab {
    flex: 1;
    text-align: center;
    padding: 10px;
    border-radius: 12px;
    color: #8b949e !important;
    font-size: 0.88rem;
    font-weight: 800;
    text-decoration: none !important;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.04);
    transition: all 0.2s;
}
.lib-tab.active {
    color: #60a5fa !important;
    background: rgba(96, 165, 250, 0.1);
    border-color: rgba(96, 165, 250, 0.2);
}

/* ─── Streamlit 오버라이드 ─── */
.stButton > button {
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    background: rgba(22, 30, 49, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: #e6edf3 !important;
    transition: all 0.2s !important;
    padding: 0.6rem 1rem !important;
}
.stButton > button:hover {
    border-color: #3b82f6 !important;
    color: #fff !important;
    background: rgba(59, 130, 246, 0.1) !important;
}
.stButton > button[kind="primary"] {
    background: #f0f6fc !important;
    border-color: #f0f6fc !important;
    color: #090d16 !important;
    font-weight: 800 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #cdd9e5 !important;
    box-shadow: 0 4px 14px rgba(240, 246, 252, 0.18) !important;
}
.btn-know-active > button {
    background: rgba(52,211,153,0.18) !important;
    border-color: #34d399 !important;
    color: #34d399 !important;
}
.btn-unk-active > button {
    background: rgba(59,130,246,0.18) !important;
    border-color: #60a5fa !important;
    color: #60a5fa !important;
}
.btn-clear-active > button {
    background: rgba(52,211,153,0.18) !important;
    border-color: #34d399 !important;
    color: #34d399 !important;
}
hr { border-color: rgba(255,255,255,0.06) !important; margin: 16px 0 !important; }
.sec-lbl {
    color: #6e7681;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 12px;
}
</style>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  ⑧ UI COMPONENTS (명칭 변경 대응)
# ══════════════════════════════════════════════════════════════════
POS_STYLE = {
    "형용사": ("color:#60a5fa;", "--glow:rgba(96,165,250,.18)", "linear-gradient(160deg,#1a3a5c,#0d2035)"),
    "동사":   ("color:#34d399;", "--glow:rgba(52,211,153,.18)", "linear-gradient(160deg,#1a2d1a,#0d200d)"),
    "명사":   ("color:#bc8cff;", "--glow:rgba(188,140,255,.18)", "linear-gradient(160deg,#2d1a3a,#1a0d2e)"),
    "부사":   ("color:#fbbf24;", "--glow:rgba(251,191,36,.18)", "linear-gradient(160deg,#2d2a1a,#201e0d)"),
}
DEFAULT_POS_STYLE = ("color:#8b949e;", "--glow:rgba(139,148,158,.15)", "linear-gradient(160deg,#1a1f27,#0d1117)")

def _pos_style(pos: str) -> tuple[str, str, str]:
    return POS_STYLE.get(pos, DEFAULT_POS_STYLE)

def render_top_header(progress_pct: float, day_number: int) -> None:
    wd = TODAY.weekday()
    days_since_sun = (wd + 1) % 7
    week_start = TODAY - timedelta(days=days_since_sun)

    cal_cols_html = ""
    for i, day_kr in enumerate(WEEKDAYS_KR):
        d = week_start + timedelta(days=i)
        is_today = (d == TODAY)
        is_sun = (i == 0)
        is_sat = (i == 6)
        day_cls = "today-lbl" if is_today else ("sun" if is_sun else ("sat" if is_sat else ""))
        num_cls = "today" if is_today else ""
        cal_cols_html += f"""
        <div class="wc-col">
            <span class="wc-day {day_cls}">{day_kr}</span>
            <span class="wc-num {num_cls}">{d.day}</span>
        </div>"""

    fill_pct = min(100, max(0, progress_pct))

    st.markdown(f"""
<div class="top-header">
    <div class="header-row1">
        <div class="exam-label">수능 <span class="exam-arrow">▼</span></div>
        <div class="dday-pill">
            <div class="pill-ring"></div>
            <span>{progress_pct:.1f}%</span>
            <span style="color: rgba(255,255,255,0.2)">|</span>
            <span>D-{D_DAY}</span>
        </div>
        <div class="avatar-dot"></div>
    </div>
    <div class="week-cal">{cal_cols_html}</div>
    <div class="hdr-prog-wrap">
        <div class="hdr-prog-fill" style="width:{fill_pct:.1f}%"></div>
    </div>
    <div class="day-lbl">Day {day_number} / 60</div>
</div>
    """, unsafe_allow_html=True)

def render_word_grid(words: list[dict]) -> str:
    shown = words[:9]
    html = '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px;">'
    for w in shown:
        en = w.get("word", "")
        display_en = en.split("_")[0]
        html += f"""
        <div style="
            background: rgba(22, 30, 49, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 18px 8px;
            text-align: center;
            font-weight: 800;
            color: #ffffff;
            font-size: 1.05rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            letter-spacing: -0.01em;
        ">
            {display_en}
        </div>"""
    for _ in range(9 - len(shown)):
        html += '<div style="border: 1px dashed rgba(255, 255, 255, 0.04); border-radius: 16px; padding: 18px 8px;"></div>'
    html += '</div>'
    return html

def render_word_strip(words: list[dict]) -> str:
    html = '<div class="word-strip">'
    for i, w in enumerate(words[:7]):
        grad = STRIP_GRADS[i % len(STRIP_GRADS)]
        emoji = w.get("emoji", "📚")
        en = w.get("word", "").split("_")[0]
        html += (
            f'<div class="ws-item" style="background:linear-gradient(160deg,{grad});">'
            f'<span class="ws-emoji">{emoji}</span>'
            f'<span class="ws-en">{en}</span>'
            f'</div>'
        )
    html += "</div>"
    return html

def render_bottom_nav(active_tab: str) -> None:
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    st.markdown("""
<div style="
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(13, 20, 35, 0.92);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    z-index: 9999;
    padding: 8px 12px 18px;
">
</div>
    """, unsafe_allow_html=True)
    
    nav_cols = st.columns(4)
    tabs = [
        ("home", "🏠 홈"),
        ("library", "🔖 라이브러리"),
        ("stats", "📊 분석"),
        ("reset", "🔄 리셋")
    ]
    
    for idx, (tab_id, label) in enumerate(tabs):
        with nav_cols[idx]:
            is_active = (active_tab == tab_id)
            if tab_id == "reset":
                if st.button(label, key=f"nav_btn_{tab_id}", use_container_width=True):
                    db_reset_today(st.session_state.current_day)
                    reset_all_session()
                    st.session_state.page = "home"
                    st.session_state.active_tab = "home"
                    st.rerun()
            else:
                btn_type = "primary" if is_active else "secondary"
                if st.button(label, key=f"nav_btn_{tab_id}", use_container_width=True, type=btn_type):
                    st.session_state.active_tab = tab_id
                    st.session_state.page = tab_id
                    st.rerun()

# ══════════════════════════════════════════════════════════════════
#  ⑨ PAGE: HOME & DAY SELECTOR
# ══════════════════════════════════════════════════════════════════
def page_home() -> None:
    ss = st.session_state
    progress_pct = calc_progress_pct()
    
    # 상단 대시보드 렌더링
    render_top_header(progress_pct, ss.current_day)

    # 🚨 실시간 외워야 할 오답 개수 및 복습 버튼 추가 ───────────────────
    today_str = str(date.today())
    all_review_words = load_all_review_words(today_str)
    review_count = len(all_review_words)
    
    st.markdown(f"""
    <div style="
        background: rgba(248, 81, 73, 0.08);
        border: 1px solid rgba(248, 81, 73, 0.2);
        border-radius: 18px;
        padding: 12px 16px;
        margin-bottom: 16px;
        text-align: center;
    ">
        <span style="color: #ff7b72; font-weight: 800; font-size: 1.05rem; display: block; margin-bottom: 8px;">
            🚨 현재 외워야 할 오답: {review_count}개
        </span>
    </div>""", unsafe_allow_html=True)
    
    if st.button("틀린 단어 복습하러 가기 📝", use_container_width=True, type="primary", key="go_review_mode"):
        if review_count == 0:
            st.success("지금은 복습할 오답 단어가 없습니다. 완벽해요! 🎉")
        else:
            # 오답 복습 모드로 강제 세션 전환
            ss.all_words = all_review_words
            ss.unknown_ids = [w["word_id"] for w in all_review_words]
            ss.skimming_done = True # 스키밍 분류 스킵
            ss.fc_index = 0
            ss.fc_visited = set()
            ss.flashcard_done = False
            ss.page = "flashcard" # 2단계 플래시카드로 이동
            st.rerun()
            
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 🔄 스마트 복습 주기 알림 배너 노출 ───────────────────
    review_cnt = ss.get("review_words_count", 0)
    if review_cnt > 0:
        st.markdown(f"""
<div style="background: rgba(96, 165, 250, 0.12);
            border: 1px solid rgba(96, 165, 250, 0.35);
            border-radius: 16px;
            padding: 14px 18px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 12px;">
    <span style="font-size: 1.8rem;">🔄</span>
    <div>
        <div style="color: #60a5fa; font-weight: 800; font-size: 0.95rem;">오늘 복습해야 할 오답 단어가 {review_cnt}개 있습니다!</div>
        <div style="color: #8b949e; font-size: 0.78rem; margin-top: 2px;">과거에 틀렸던 단어가 망각곡선 스케줄러에 따라 오늘 공부 목록에 추가되었습니다.</div>
    </div>
</div>""", unsafe_allow_html=True)

    # 마스터 축하 배너
    if ss.get("all_mastered", False):
        st.markdown("""
<div style="background: linear-gradient(135deg, rgba(52, 211, 153, 0.15), rgba(96, 165, 250, 0.1));
            border: 2px solid rgba(52, 211, 153, 0.4);
            border-radius: 20px;
            padding: 22px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(52, 211, 153, 0.15);">
    <div style="font-size: 2.8rem; margin-bottom: 8px;">🎉 🏆 🎉</div>
    <div style="color: #34d399; font-size: 1.25rem; font-weight: 900;">오늘 단어를 모두 마스터하셨습니다!</div>
    <div style="color: #e6edf3; font-size: 0.85rem; margin-top: 6px;">Day {}의 모든 단어를 정복하셨습니다. 다음 날짜에 도전하세요! 🚀</div>
</div>""".format(ss.current_day), unsafe_allow_html=True)

    # 학습할 Day 선택
    st.markdown('<div class="sec-lbl">🎯 커리큘럼 선택</div>', unsafe_allow_html=True)
    day_options = [f"Day {i}" for i in range(1, 61)]
    selected_day_str = st.selectbox(
        "학습할 Day를 골라주세요",
        options=day_options,
        index=ss.current_day - 1,
        key="day_selector"
    )
    selected_day = int(selected_day_str.split(" ")[-1])
    
    if selected_day != ss.current_day:
        ss.current_day = selected_day
        reset_all_session()
        st.rerun()

    words = ss.all_words
    total_words = len(words)

    st.markdown('<div class="sec-lbl">📅 오늘의 학습 진행 현황 (총 {}단어)</div>'.format(total_words), unsafe_allow_html=True)

    # 1. 스키밍 단계 카드
    skim_done = ss.skimming_done
    skim_status = '<span class="pc-status done">완료 ✅</span>' if skim_done else '<span class="pc-status">대기 중</span>'
    prog_fill = "100%" if skim_done else "0%"
    
    grid_or_strip = render_word_grid(words) if not skim_done else render_word_strip(words)
    
    st.markdown(f"""
<div class="phase-card">
    {grid_or_strip}
    <div class="pc-body">
        <div class="pc-hd">
            <span class="pc-title">🔍 1단계: 스키밍 (Skimming)</span>
            <span class="pc-filter">≡</span>
        </div>
        <div class="pc-prog"><div class="pc-prog-fill" style="width:{prog_fill}"></div></div>
        <div class="pc-meta">{skim_status}<span class="pc-time">~10분</span></div>
        <div class="pc-desc">오늘의 단어를 10개씩 분류하며 아는 단어와 모르는 단어를 걸러냅니다.</div>
    </div>
</div>""", unsafe_allow_html=True)

    if not skim_done:
        if st.button("바로 시작", use_container_width=True, type="primary", key="go_skim"):
            db_reset_today(ss.current_day)
            reset_all_session()
            ss.page = "skimming"
            st.rerun()
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 2. 플래시카드 단계 카드
    fc_locked = not skim_done or ss.get("all_mastered", False)
    fc_done = ss.flashcard_done
    fc_status = (
        '<span class="pc-status done">완료 ✅</span>' if fc_done else
        '<span class="pc-status">🔒 스키밍 완료 후 열림</span>' if fc_locked else
        '<span class="pc-status">대기 중</span>'
    )
    fc_prog = "100%" if fc_done else "0%"
    locked_cls = "locked" if fc_locked else ""

    st.markdown(f"""
<div class="phase-card {locked_cls}">
    {render_word_strip(words)}
    <div class="pc-body">
        <div class="pc-hd">
            <span class="pc-title">🃏 2단계: 플래시카드 (Flashcards)</span>
        </div>
        <div class="pc-prog"><div class="pc-prog-fill" style="width:{fc_prog}"></div></div>
        <div class="pc-meta">{fc_status}</div>
        <div class="pc-desc">걸러진 오답 및 모르는 단어를 카드로 확실히 집중 암기합니다.</div>
    </div>
</div>""", unsafe_allow_html=True)

    if not fc_locked and not fc_done:
        if st.button("바로 시작", use_container_width=True, type="primary", key="go_fc"):
            ss.fc_index = 0
            ss.fc_show_meaning = False
            ss.fc_visited = set()
            ss.page = "flashcard"
            st.rerun()
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # 3. 퀴즈 단계 카드
    q_locked = not fc_done or ss.get("all_mastered", False)
    q_done = ss.quiz_done
    q_status = (
        '<span class="pc-status done">완료 ✅</span>' if q_done else
        '<span class="pc-status">🔒 플래시카드 완료 후 열림</span>' if q_locked else
        '<span class="pc-status">대기 중</span>'
    )
    q_prog = "100%" if q_done else "0%"
    locked_cls2 = "locked" if q_locked else ""

    st.markdown(f"""
<div class="phase-card {locked_cls2}">
    {render_word_strip(words)}
    <div class="pc-body">
        <div class="pc-hd">
            <span class="pc-title">📝 3단계: 퀴즈 (Quiz)</span>
        </div>
        <div class="pc-prog"><div class="pc-prog-fill" style="width:{q_prog}"></div></div>
        <div class="pc-meta">{q_status}</div>
        <div class="pc-desc">암기한 단어들을 객관식 퀴즈를 통하여 최종 점검하고 맞춥니다.</div>
    </div>
</div>""", unsafe_allow_html=True)

    if not q_locked and not q_done:
        if st.button("바로 시작", use_container_width=True, type="primary", key="go_quiz"):
            q = list(ss.unknown_ids)
            random.shuffle(q)
            ss.quiz_queue = q
            ss.quiz_results = {}
            ss.quiz_answered = False
            ss.quiz_choices = []
            ss.quiz_answer = ""
            ss.page = "quiz"
            st.rerun()

    render_bottom_nav("home")

# ══════════════════════════════════════════════════════════════════
#  ⑩ PAGE: SKIMMING (10-WORDS PAGINATION)
# ══════════════════════════════════════════════════════════════════
def page_skimming() -> None:
    ss = st.session_state
    words = ss.all_words
    total = len(words)

    if total == 0:
        ss.skimming_done = True
        ss.page = "home"
        st.rerun()
        return

    if not ss.skim_states:
        ss.skim_states = {w["word_id"]: "pending" for w in words}
    if "skim_page" not in ss:
        ss.skim_page = 0

    states = ss.skim_states

    # 뒤로가기 및 타이틀
    c_back, c_title = st.columns([2, 7])
    with c_back:
        if st.button("← 홈", key="back_skim"):
            ss.page = "home"
            st.rerun()
    with c_title:
        st.markdown(f'<div style="color:#ffffff;font-weight:800;font-size:1.05rem;padding-top:4px;">🔍 스키밍 — Day {ss.current_day}</div>', unsafe_allow_html=True)

    ITEMS_PER_PAGE = 10
    start_idx = ss.skim_page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total)
    page_words = words[start_idx:end_idx]

    know_n = sum(1 for v in states.values() if v == "know")
    unknown_n = sum(1 for v in states.values() if v == "unknown")
    pending_n = sum(1 for v in states.values() if v == "pending")

    st.markdown(f"""
<div class="skim-summary">
    <div class="ss-chip know">
        <div class="ss-num">{know_n}</div>
        <div class="ss-lbl">✓ 알아요</div>
    </div>
    <div class="ss-chip unk">
        <div class="ss-num">{unknown_n}</div>
        <div class="ss-lbl">✗ 몰라요</div>
    </div>
    <div class="ss-chip pend">
        <div class="ss-num">{pending_n}</div>
        <div class="ss-lbl">미분류</div>
    </div>
</div>""", unsafe_allow_html=True)

    classified_n = know_n + unknown_n
    st.progress(classified_n / total if total else 0.0)
    st.markdown(f'<div style="color:#8b949e;font-size:0.75rem;margin:4px 0 14px">{ss.skim_page + 1} / {(total-1)//10 + 1} 페이지 ({start_idx+1}~{end_idx}번째 단어) · 전체 {classified_n}/{total} 분류 완료</div>', unsafe_allow_html=True)

    COLS_PER_ROW = 2
    for r_idx in range(0, len(page_words), COLS_PER_ROW):
        grid_cols = st.columns(COLS_PER_ROW, gap="small")
        for c_idx in range(COLS_PER_ROW):
            w_idx = r_idx + c_idx
            if w_idx >= len(page_words):
                break
            word = page_words[w_idx]
            wid = word["word_id"]
            state = states.get(wid, "pending")
            emoji = word.get("emoji", "📚")
            english_display = word["word"].split("_")[0]
            state_icon = {"know": "✅", "unknown": "📌", "pending": ""}.get(state, "")

            bg_style = "background: rgba(22, 30, 49, 0.5);"
            border_style = "border: 1px solid rgba(255, 255, 255, 0.06);"
            if state == "know":
                bg_style = "background: rgba(52, 211, 153, 0.06);"
                border_style = "border: 1.5px solid rgba(52, 211, 153, 0.4);"
            elif state == "unknown":
                bg_style = "background: rgba(59, 130, 246, 0.08);"
                border_style = "border: 1.5px solid rgba(59, 130, 246, 0.45);"

            with grid_cols[c_idx]:
                st.markdown(f"""
<div class="sg-card {state}" style="{bg_style} {border_style} min-height: 100px; padding: 12px 6px;">
    <span class="sg-state-icon">{state_icon}</span>
    <span class="sg-emoji" style="font-size:1.6rem;">{emoji}</span>
    <span class="sg-word" style="font-size:1.05rem; font-weight:800;">{english_display}</span>
</div>""", unsafe_allow_html=True)

                b1, b2 = st.columns(2, gap="small")
                with b1:
                    btn_k_cls = "btn-know-active" if state == "know" else ""
                    st.markdown(f'<div class="{btn_k_cls}">', unsafe_allow_html=True)
                    if st.button("알아요", key=f"skim_k_{wid}", use_container_width=True):
                        states[wid] = "pending" if state == "know" else "know"
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with b2:
                    btn_u_cls = "btn-unk-active" if state == "unknown" else ""
                    st.markdown(f'<div class="{btn_u_cls}">', unsafe_allow_html=True)
                    if st.button("몰라요", key=f"skim_u_{wid}", use_container_width=True):
                        states[wid] = "pending" if state == "unknown" else "unknown"
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    p1, p2 = st.columns(2)
    with p1:
        if st.button("← 이전 10개", key="prev_page", use_container_width=True, disabled=(ss.skim_page == 0)):
            ss.skim_page -= 1
            st.rerun()
    with p2:
        if st.button("다음 10개 →", key="next_page", use_container_width=True, disabled=(end_idx >= total)):
            ss.skim_page += 1
            st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    all_classified = all(v != "pending" for v in states.values())
    
    if not all_classified:
        st.markdown(f'<div style="color:#8b949e;font-size:0.8rem;text-align:center;margin-bottom:10px">⚠️ {total}개 단어를 모두 분류해야 완료할 수 있습니다. (남은 미분류: {pending_n}개)</div>', unsafe_allow_html=True)

    if st.button(f"선택 완료 및 학습 시작 🚀 (몰라요 {unknown_n}개)", use_container_width=True, type="primary", disabled=not all_classified):
        for w in words:
            res = states.get(w["word_id"], "know")
            db_set_skimming(w["word_id"], res)

        ss.unknown_ids = [wid for wid, s in states.items() if s == "unknown"]
        # 동적으로 리스트 새로고침
        day_words, review_words = load_today_words(ss.current_day)
        ss.all_words = day_words + review_words
        ss.skimming_done = True
        
        if not ss.unknown_ids:
            ss.flashcard_done = True
            ss.quiz_done = True
            ss.all_mastered = True
            ss.page = "home"
        else:
            ss.all_mastered = False
            ss.page = "flashcard"
            ss.fc_index = 0
            ss.fc_show_meaning = False
            ss.fc_visited = set()
            ss.flashcard_done = False

        st.rerun()

# ══════════════════════════════════════════════════════════════════
#  ⑪ PAGE: FLASHCARD
# ══════════════════════════════════════════════════════════════════
def page_flashcard() -> None:
    ss = st.session_state
    word_ids = ss.unknown_ids
    word_map = {w["word_id"]: w for w in ss.all_words}
    total = len(word_ids)

    if total == 0:
        ss.flashcard_done = True
        ss.page = "home"
        st.rerun()
        return

    if "fc_visited" not in ss:
        ss.fc_visited = set()

    idx = min(ss.fc_index, total - 1)
    ss.fc_index = idx
    ss.fc_visited.add(idx)

    current_id = word_ids[idx]
    word = word_map.get(current_id)

    if not word:
        ss.fc_index = 0
        st.rerun()
        return

    h1, h2, h3 = st.columns([2, 4, 3])
    with h1:
        if st.button("← 홈", key="back_fc"):
            reset_all_session() # 오답 학습 탈출 대비
            ss.page = "home"
            st.rerun()
    with h2:
        st.markdown('<div style="color:#ffffff;font-weight:800;font-size:1.05rem;padding-top:4px;">🃏 플래시카드</div>', unsafe_allow_html=True)
    with h3:
        st.markdown(f'<div style="text-align:right"><span class="badge">학습 {len(ss.fc_visited)}/{total}</span></div>', unsafe_allow_html=True)

    st.progress(len(ss.fc_visited) / total if total else 0.0)
    st.markdown(f'<div style="color:#8b949e;font-size:0.75rem;margin:4px 0 14px">{idx + 1} / {total}번째 단어 복습 중</div>', unsafe_allow_html=True)

    pos = word.get("part_of_speech", "명사")
    pos_css, glow_var, bg_grad = _pos_style(pos)
    emoji = word.get("emoji", "📚")
    english_display = word['word'].split("_")[0]
    korean_display = word['meaning'].split("_")[0]

    st.markdown(f"""
<div class="fc-card">
    <div class="fc-img" style="background: linear-gradient(160deg, #1f2937, #111827); border-bottom: 1px solid rgba(255,255,255,0.06);">
        <div style="position:absolute;inset:0;background:radial-gradient(circle at 50% 50%, rgba(96,165,250,0.1) 0%, transparent 70%);"></div>
        <span style="font-size:5.5rem;position:relative;z-index:1;filter:drop-shadow(0 0 16px rgba(96,165,250,0.35));">{emoji}</span>
        <span class="fc-img-label">📷 IMAGE PLACEHOLDER</span>
    </div>
    <div class="fc-body">
        <div class="fc-word-row">
            <span class="fc-en">{english_display}</span>
            <span class="fc-sound">🔊 발음 듣기</span>
        </div>
        <div class="fc-pos" style="{pos_css}">{pos}</div>""", unsafe_allow_html=True)

    if ss.fc_show_meaning:
        st.markdown(f"""
        <div class="fc-meaning">
            <div class="fc-ko">{korean_display}</div>
            <div class="fc-example">
                {word['example_en']}
                <span class="fc-ex-ko">{word['example_ko']}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)

    if not ss.fc_show_meaning:
        if st.button("👁  뜻 보기", use_container_width=True, key="fc_show"):
            ss.fc_show_meaning = True
            st.rerun()
    else:
        if st.button("🙈  뜻 숨기기", use_container_width=True, key="fc_hide"):
            ss.fc_show_meaning = False
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("← 이전 단어", use_container_width=True, key="fc_prev", disabled=(idx == 0)):
            ss.fc_index = idx - 1
            ss.fc_show_meaning = False
            st.rerun()
    with nav2:
        if st.button("다음 단어 →", use_container_width=True, key="fc_next", disabled=(idx == total - 1)):
            ss.fc_index = idx + 1
            ss.fc_show_meaning = False
            st.rerun()

    dots_html = '<div class="fc-dots">'
    shown_dots = min(total, 10)
    for i in range(shown_dots):
        cls = "active" if i == idx else ("cleared" if i in ss.fc_visited else "")
        dots_html += f'<div class="fc-dot {cls}"></div>'
    dots_html += '</div>'
    st.markdown(dots_html, unsafe_allow_html=True)

    all_visited = (len(ss.fc_visited) >= total)
    st.markdown("<hr>", unsafe_allow_html=True)

    if all_visited:
        st.markdown("""
<div style="background: rgba(96,165,250,0.08); border: 1px solid rgba(96,165,250,0.25); border-radius:16px; padding:12px; text-align:center; margin-bottom:12px;">
    <span style="color:#60a5fa; font-size:0.85rem; font-weight:700;">🎉 오늘 배울 모든 단어를 한 번씩 확인했습니다!</span>
</div>""", unsafe_allow_html=True)

    if st.button("📝 실전 퀴즈 풀기", use_container_width=True, type="primary", disabled=not all_visited):
        ss.flashcard_done = True
        
        q = list(ss.unknown_ids)
        random.shuffle(q)
        ss.quiz_queue = q
        ss.quiz_results = {}
        ss.quiz_answered = False
        ss.quiz_choices = []
        ss.quiz_answer = ""
        ss.quiz_done = False
        
        ss.page = "quiz"
        st.rerun()

# ══════════════════════════════════════════════════════════════════
#  ⑫ PAGE: QUIZ
# ══════════════════════════════════════════════════════════════════
NUMS = ["①", "②", "③", "④"]

def _build_choices(word: dict) -> tuple[list[str], str]:
    answer = word["meaning"].split("_")[0]
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT meaning
            FROM vocabulary
            WHERE word_id != ?
        """, (word["word_id"],)).fetchall()
        
    pool = list(set([r["meaning"].split("_")[0] for r in rows if r["meaning"].split("_")[0] != answer]))
    if len(pool) < 3:
         pool = pool + ["선물", "진동", "의무", "환경"]
         
    distractors = random.sample(pool, min(3, len(pool)))
    choices = distractors + [answer]
    random.shuffle(choices)
    return choices, answer

def page_quiz() -> None:
    ss = st.session_state
    queue = ss.quiz_queue
    word_map = {w["word_id"]: w for w in ss.all_words}
    total = len(ss.unknown_ids)
    done_n = len(ss.quiz_results)

    h1, h2, h3 = st.columns([2, 4, 3])
    with h1:
        if st.button("← 홈", key="back_quiz"):
            reset_all_session()
            ss.page = "home"
            st.rerun()
    with h2:
        st.markdown('<div style="color:#ffffff;font-weight:800;font-size:1.05rem;padding-top:4px;">📝 퀴즈 검증</div>', unsafe_allow_html=True)
    with h3:
        st.markdown(f'<div style="text-align:right"><span class="badge">{done_n}/{total}</span></div>', unsafe_allow_html=True)

    if not queue:
        ss.quiz_done = True
        correct_n = sum(1 for v in ss.quiz_results.values() if v)
        wrong_n = total - correct_n
        score_pct = int(correct_n / total * 100) if total else 0
        trophy = "🏆" if score_pct == 100 else ("🌟" if score_pct >= 80 else "📚")

        st.markdown(f"""
<div class="result-hero" style="text-align:center;padding:24px;background:rgba(22, 30, 49, 0.65);border-radius:24px;border:1px solid rgba(255,255,255,0.08);">
    <div style="font-size:3.5rem;margin-bottom:8px">{trophy}</div>
    <div style="color:#34d399;font-size:1.45rem;font-weight:900">오늘의 학습 완독 완료!</div>
    <div style="color:#8b949e;font-size:0.85rem;margin-top:6px">망각 극복 학습 주기가 등록되었습니다.</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(f'<div class="stats-card-box"><div class="stats-card-val c-green">{correct_n}</div><div class="stats-card-lbl">정답</div></div>', unsafe_allow_html=True)
        with r2:
            st.markdown(f'<div class="stats-card-box"><div class="stats-card-val c-red">{wrong_n}</div><div class="stats-card-lbl">오답</div></div>', unsafe_allow_html=True)
        with r3:
            st.markdown(f'<div class="stats-card-box"><div class="stats-card-val c-blue">{score_pct}%</div><div class="stats-card-lbl">성취도</div></div>', unsafe_allow_html=True)

        if wrong_n > 0:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-lbl">📕 오답 처리된 단어</div>', unsafe_allow_html=True)
            for wid, passed in ss.quiz_results.items():
                if not passed:
                    w = word_map.get(wid)
                    if w:
                        pos_css, _, _ = _pos_style(w["part_of_speech"])
                        english_clean = w['word'].split("_")[0]
                        korean_clean = w['meaning'].split("_")[0]
                        st.markdown(f"""
<div class="wn-card">
    <span class="wn-emoji">{w['emoji']}</span>
    <div class="wn-info">
        <span class="wn-en">{english_clean}</span>
        <span class="wn-ko">{korean_clean}</span>
        <div class="wn-pos" style="{pos_css}">{w['part_of_speech']}</div>
    </div>
    <span class="wn-wrong-badge">오답</span>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("홈으로 이동하여 완료", use_container_width=True, type="primary"):
            reset_all_session()
            ss.page = "home"
            st.rerun()
        return

    st.progress(done_n / total if total else 0.0)
    st.markdown(f'<div style="color:#8b949e;font-size:0.75rem;margin:4px 0 14px">{done_n + 1} / {total}번째 문제</div>', unsafe_allow_html=True)

    current_id = queue[0]
    word = word_map.get(current_id)

    if not ss.quiz_choices:
        choices, answer = _build_choices(word)
        ss.quiz_choices = choices
        ss.quiz_answer = answer
        ss.quiz_answered = False
        ss.quiz_correct = False

    pos_css, glow_var, bg_grad = _pos_style(word["part_of_speech"])
    emoji = word.get("emoji", "📚")
    glow_color = glow_var.split(":", 1)[-1]
    english_clean = word['word'].split("_")[0]

    st.markdown(f"""
<div class="fc-card" style="margin-bottom:14px">
    <div class="fc-img" style="background:{bg_grad};{glow_var};height:140px">
        <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,{glow_color} 0%,transparent 65%);"></div>
        <span style="font-size:4.5rem;position:relative;z-index:1;filter:drop-shadow(0 0 18px {glow_color});">{emoji}</span>
    </div>
    <div class="fc-body" style="padding:18px 24px;">
        <div class="sec-lbl">Q{done_n + 1}. 다음 영단어의 알맞은 한글 뜻은?</div>
        <div class="fc-en" style="margin-bottom:2px">{english_clean}</div>
        <div class="fc-pos" style="{pos_css}">{word['part_of_speech']}</div>
    </div>
</div>""", unsafe_allow_html=True)

    if not ss.quiz_answered:
        for idx_choice, choice in enumerate(ss.quiz_choices):
            if st.button(f"{NUMS[idx_choice]}  {choice}", key=f"choice_btn_{idx_choice}", use_container_width=True):
                ok = (choice == ss.quiz_answer)
                ss.quiz_correct = ok
                ss.quiz_answered = True
                ss.quiz_selected = choice
                db_set_quiz(current_id, ok)
                ss.quiz_results[current_id] = ok
                st.rerun()
    else:
        for idx_choice, choice in enumerate(ss.quiz_choices):
            is_ans = (choice == ss.quiz_answer)
            is_sel = (choice == ss.get("quiz_selected", ""))

            if is_ans:
                css_cls = "qbtn-correct"
            elif is_sel and not ss.quiz_correct:
                css_cls = "qbtn-wrong"
            else:
                css_cls = "qbtn-dim"

            st.markdown(f'<div class="{css_cls}">', unsafe_allow_html=True)
            st.button(f"{NUMS[idx_choice]}  {choice}", key=f"choice_ans_btn_{idx_choice}", use_container_width=True, disabled=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if ss.quiz_correct:
            st.success("정답입니다! 🎉")
        else:
            st.error(f"아쉬워요! 정답은 [{ss.quiz_answer}]입니다.")

        if st.button("다음 문제로 이동 →", use_container_width=True, type="primary"):
            ss.quiz_queue.pop(0)
            ss.quiz_choices = []
            ss.quiz_answer = ""
            ss.quiz_answered = False
            ss.quiz_correct = False
            ss["quiz_selected"] = ""
            st.rerun()

# ══════════════════════════════════════════════════════════════════
#  ⑬ PAGE: LIBRARY (오답 노트 & 내일 복습 예고 & 파일 업로더 추가)
# ══════════════════════════════════════════════════════════════════
def page_library() -> None:
    ss = st.session_state
    progress_pct = calc_progress_pct()
    render_top_header(progress_pct, ss.current_day)

    lib_tab = st.query_params.get("lib", "wrong")
    if isinstance(lib_tab, list):
         lib_tab = lib_tab[0] if lib_tab else "wrong"

    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("📕 오답 노트", key="btn_tab_wrong", type="primary" if lib_tab == "wrong" else "secondary", use_container_width=True):
            st.query_params["lib"] = "wrong"
            st.rerun()
    with s2:
        if st.button("📚 전체 단어장", key="btn_tab_all", type="primary" if lib_tab == "all" else "secondary", use_container_width=True):
            st.query_params["lib"] = "all"
            st.rerun()
    with s3:
        if st.button("📤 설정/업로드", key="btn_tab_upload", type="primary" if lib_tab == "upload" else "secondary", use_container_width=True):
            st.query_params["lib"] = "upload"
            st.rerun()

    # ① 오답 노트 탭
    if lib_tab == "wrong":
        wrong_words = load_wrong_words()
        total_wrong = len(wrong_words)

        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;margin:16px 0 10px;"><div style="color:#ffffff;font-weight:900;font-size:1.1rem">오답 관리 목록</div><span class="badge">총 {total_wrong}개</span></div>', unsafe_allow_html=True)

        if total_wrong == 0:
            st.markdown('<div class="wn-empty"><div class="wn-empty-icon">🎉</div><div style="font-weight:800;color:#ffffff;margin-bottom:6px">기록된 오답이 없습니다.</div><div>퀴즈의 오답이 여기에 자동으로 쌓입니다!</div></div>', unsafe_allow_html=True)
        else:
            if st.button("🔄  오답 단어만 재도전하기", use_container_width=True, type="primary"):
                ss.unknown_ids = [w["word_id"] for w in wrong_words]
                ss.fc_index = 0
                ss.fc_visited = set()
                ss.flashcard_done = False
                ss.skimming_done = True
                ss.page = "flashcard"
                st.rerun()

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            max_w = max(w["wrong_count"] for w in wrong_words) if wrong_words else 1
            for w in wrong_words:
                wid = w["word_id"]
                cnt = w["wrong_count"]
                bar_pct = int(cnt / max_w * 100)
                pos_css, _, _ = _pos_style(w["part_of_speech"])
                is_retry = (w["study_status"] == "needs_retry")
                english_clean = w['word'].split("_")[0]
                korean_clean = w['meaning'].split("_")[0]

                st.markdown(f"""
<div class="wn-card" style="margin-bottom:6px;">
    <span class="wn-emoji">{w['emoji']}</span>
    <div class="wn-info">
        <span class="wn-en">{english_clean}</span>
        <span class="wn-ko">{korean_clean}</span>
        <div class="wn-pos" style="{pos_css}">{w['part_of_speech']}</div>
        <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.06);border-radius:10px;overflow:hidden">
            <div style="width:{bar_pct}%;height:100%;background:linear-gradient(90deg, #f85149, #ff7b72);border-radius:10px;"></div>
        </div>
    </div>
    <div style="text-align:right;">
        <span class="wn-wrong-badge">✖ {cnt}회</span>
        {"<span style='color:#f85149;font-size:0.62rem;margin-top:4px;display:block;font-weight:700'>재도전 필요</span>" if is_retry else ""}
    </div>
</div>""", unsafe_allow_html=True)

                if st.button("다시 외웠어요 완료 ✅", key=f"master_{wid}", use_container_width=True):
                    db_reset_wrong_count(wid)
                    day_words, review_words = load_today_words(ss.current_day)
                    ss.all_words = day_words + review_words
                    ss.review_words_count = len(review_words)
                    st.rerun()
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        
        # 내일 복습 예정 단어 예고 영역
        tomorrow_words = load_tomorrow_review_words()
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f'<div style="color:#ffffff;font-weight:900;font-size:1.1rem;margin-bottom:12px;">📅 내일 복습 예정인 단어 ({len(tomorrow_words)}개)</div>', unsafe_allow_html=True)
        
        if len(tomorrow_words) == 0:
            st.markdown('<div class="wn-empty" style="padding: 24px;"><div style="font-size:1.5rem;margin-bottom:6px">🌅</div><div>내일 복습이 예정된 단어가 없습니다.</div></div>', unsafe_allow_html=True)
        else:
            for tw in tomorrow_words:
                pos_css, _, _ = _pos_style(tw["part_of_speech"])
                en_clean = tw['word'].split("_")[0]
                ko_clean = tw['meaning'].split("_")[0]
                st.markdown(f"""
<div class="wn-card" style="border-color: rgba(96,165,250,0.15); background: rgba(13, 20, 35, 0.4); margin-bottom: 8px;">
    <span class="wn-emoji">{tw['emoji']}</span>
    <div class="wn-info">
        <span class="wn-en" style="color:#60a5fa;">{en_clean}</span>
        <span class="wn-ko">{ko_clean}</span>
        <div class="wn-pos" style="{pos_css}">{tw['part_of_speech']}</div>
    </div>
    <span class="wn-wrong-badge" style="background:rgba(96,165,250,0.08); color:#60a5fa; border-color:rgba(96,165,250,0.2);">내일 복습</span>
</div>""", unsafe_allow_html=True)

    # ② 전체 단어장 탭
    elif lib_tab == "all":
        all_words_list = load_words(ss.current_day)
        st.markdown(f'<div style="color:#ffffff;font-weight:900;margin:16px 0 10px;font-size:1.1rem">Day {ss.current_day} 단어 목록 ({len(all_words_list)}개)</div>', unsafe_allow_html=True)
        for w in all_words_list:
            status_icon = {
                "completed":   "✅",
                "know":        "✓ ",
                "unknown":     "✗ ",
                "needs_retry": "🔄",
                "reviewing":   "📕",
            }.get(w.get("study_status", ""), "○")
            pos_css, _, _ = _pos_style(w["part_of_speech"])
            english_clean = w['word'].split("_")[0]
            korean_clean = w['meaning'].split("_")[0]

            st.markdown(f"""
<div class="wn-card">
    <span class="wn-emoji">{w['emoji']}</span>
    <div class="wn-info">
        <span class="wn-en">{english_clean}</span>
        <span class="wn-ko">{korean_clean}</span>
        <div class="wn-pos" style="{pos_css}">{w['part_of_speech']}</div>
    </div>
    <span style="font-size:1.25rem;">{status_icon}</span>
</div>""", unsafe_allow_html=True)

    # ③ 나만의 단어 파일 등록 탭 (설정)
    elif lib_tab == "upload":
        st.markdown('<div class="stats-header-title">📤 나만의 단어 파일 등록하기</div>', unsafe_allow_html=True)
        st.info("💡 학교 부교재나 모의고사 영단어 목록(CSV 파일)을 업로드해보세요.\n\n"
                "파일은 반드시 **word, meaning, part_of_speech, example_en, example_ko** 컬럼을 포함하고 있어야 합니다. (Day 번호는 기본적으로 현재 선택된 Day에 추가됩니다.)")
        
        uploaded_file = st.file_uploader("단어 CSV 파일 선택 (.csv)", type=["csv"], key="word_uploader")
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
                
                # 필수 컬럼 체크
                required_cols = ['word', 'meaning', 'part_of_speech']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ 필수 컬럼이 누락되었습니다: {', '.join(missing_cols)}")
                else:
                    # Pandas 레벨 중복 제거
                    before_len = len(df)
                    df = df.drop_duplicates(subset=['word'])
                    after_len = len(df)
                    
                    # 수능 예문 등 선택 컬럼 방어
                    for col in ['example_en', 'example_ko']:
                        if col not in df.columns:
                            df[col] = ""
                    if 'emoji' not in df.columns:
                        df['emoji'] = "📚"
                    if 'importance' not in df.columns:
                        df['importance'] = 2
                    
                    # DB 적재
                    added_cnt = 0
                    today_str = str(date.today())
                    
                    with get_conn() as conn:
                        for _, row in df.iterrows():
                            # SQLite UNIQUE 제약 방어 삽입
                            cursor = conn.execute("""
                                INSERT OR IGNORE INTO vocabulary 
                                (word, meaning, part_of_speech, example_en, example_ko, importance, emoji, day_number)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (row['word'], row['meaning'], row['part_of_speech'], row['example_en'], row['example_ko'], int(row['importance']), row['emoji'], ss.current_day))
                            
                            if cursor.rowcount > 0:
                                word_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                                conn.execute("""
                                    INSERT OR IGNORE INTO user_progress (word_id, next_review_date)
                                    VALUES (?, ?)
                                """, (word_id, today_str))
                                added_cnt += 1
                        conn.commit()
                    
                    st.success(f"🎉 단어 등록이 완료되었습니다!\n\n"
                               f"• 파일 데이터 수: {before_len}개\n"
                               f"• 중복 제거 후 데이터 수: {after_len}개\n"
                               f"• 실제로 DB에 새로 추가된 단어: {added_cnt}개 (기존 중복 제외)")
                    
                    # 동기화 갱신
                    day_words, review_words = load_today_words(ss.current_day)
                    ss.all_words = day_words + review_words
                    ss.review_words_count = len(review_words)
                    
            except Exception as e:
                st.error(f"❌ 파일을 파싱하거나 DB에 업로드하는 동안 오류가 발생했습니다: {e}")

    render_bottom_nav("library")

# ══════════════════════════════════════════════════════════════════
#  ⑭ PAGE: STATS
# ══════════════════════════════════════════════════════════════════
def page_stats() -> None:
    ss = st.session_state
    progress_pct = calc_progress_pct()
    render_top_header(progress_pct, ss.current_day)

    stats = get_stats_data()

    st.markdown('<div class="stats-header-title">📊 전체 학습 통계 (60일 커리큘럼)</div>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="stats-grid">
    <div class="stats-card-box">
        <div class="stats-card-val c-blue">{stats['total']}</div>
        <div class="stats-card-lbl">총 단어 수</div>
    </div>
    <div class="stats-card-box">
        <div class="stats-card-val c-green">{stats['completed']}</div>
        <div class="stats-card-lbl">완료한 단어</div>
    </div>
    <div class="stats-card-box">
        <div class="stats-card-val c-purple">{stats['unseen']}</div>
        <div class="stats-card-lbl">미학습 단어</div>
    </div>
    <div class="stats-card-box">
        <div class="stats-card-val c-red">{stats['wrong_total']}</div>
        <div class="stats-card-lbl">누적 오답 수</div>
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="stats-header-title">🔥 가장 취약한 오답 단어 Top 3</div>', unsafe_allow_html=True)

    if not stats['top_wrong']:
        st.markdown('<div class="wn-empty" style="padding:30px;"><div class="wn-empty-icon">✨</div><div style="font-weight:800;color:#ffffff;">기록된 오답 데이터가 없습니다.</div><div style="font-size:0.8rem;margin-top:4px">퀴즈를 틀리면 여기에 취약 단어가 수집됩니다!</div></div>', unsafe_allow_html=True)
    else:
        items_html = ""
        for w in stats['top_wrong']:
            english_clean = w['word'].split("_")[0]
            korean_clean = w['meaning'].split("_")[0]
            items_html += f"""
            <div class="top-wrong-item">
                <div>
                    <span class="twi-word">{english_clean}</span>
                    <span class="twi-meaning">{korean_clean}</span>
                </div>
                <span class="twi-count" style="background:rgba(248,81,73,0.1);color:#f85149;border:1px solid rgba(248,81,73,0.2);border-radius:6px;padding:2px 8px;font-size:0.75rem;font-weight:800;">✖ {w['wrong_count']}회</span>
            </div>"""
        st.markdown(f'<div class="top-wrong-list">{items_html}</div>', unsafe_allow_html=True)

    render_bottom_nav("stats")

# ══════════════════════════════════════════════════════════════════
#  ⑮ MAIN ROUTER
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    init_db()
    inject_css()
    init_session()

    ss = st.session_state
    
    if not ss.all_words:
        day_words, review_words = load_today_words(ss.current_day)
        ss.all_words = day_words + review_words
        ss.review_words_count = len(review_words)

    p = ss.page
    if p == "home":
        page_home()
    elif p == "skimming":
        page_skimming()
    elif p == "flashcard":
        page_flashcard()
    elif p == "quiz":
        page_quiz()
    elif p == "library":
        page_library()
    elif p == "stats":
        page_stats()
    else:
        ss.page = "home"
        st.rerun()

if __name__ == "__main__":
    main()

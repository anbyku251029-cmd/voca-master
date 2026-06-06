"""
🚀 ANTIGRAVITY — 망각의 중력을 거스르는 수능 영단어 앱 (v3.0)
===========================================================
기술 스택 : Python 3.10+ · Streamlit · SQLite3
실행 방법 : streamlit run app.py
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
import streamlit as st

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
#  ③ DATABASE LAYER & 3,000단어 대량 더미 데이터 구축
# ══════════════════════════════════════════════════════════════════
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS words (
                word_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                english        TEXT    NOT NULL UNIQUE,
                korean         TEXT    NOT NULL,
                part_of_speech TEXT    NOT NULL,
                example_en     TEXT,
                example_ko     TEXT,
                importance     INTEGER DEFAULT 2,
                emoji          TEXT    DEFAULT '📚',
                day_number     INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS user_progress (
                progress_id       INTEGER  PRIMARY KEY AUTOINCREMENT,
                word_id           INTEGER  NOT NULL UNIQUE REFERENCES words(word_id),
                study_status      TEXT     NOT NULL DEFAULT 'unseen',
                skimming_result   TEXT     DEFAULT 'pending',
                flashcard_cleared INTEGER  DEFAULT 0,
                quiz_passed       INTEGER  DEFAULT 0,
                wrong_count       INTEGER  DEFAULT 0,
                last_studied_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 현재 DB 단어 개수 체크
        count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        if count < 3000:
            # 60일치 x 일일 50개 = 3,000개 고속 대량 더미 단어 생성
            poses = ["형용사", "동사", "명사", "부사"]
            emojis = ["✨", "⛔", "🌫️", "🌍", "🔄", "⏩", "⚡", "💡", "📉", "🔬", "🚀", "🚧", "🌟", "🌑", "🌊"]
            
            # 단어 조합용 고등 기출 15종 베이스 단어
            word_bases = [
                ("pure", "순수한, 순결한"),
                ("preclude", "방해하다, 불가능하게 하다"),
                ("ambiguous", "모호한, 불분명한"),
                ("phenomenon", "현상"),
                ("persist", "지속하다, 고집하다"),
                ("subsequent", "그 다음의, 뒤이은"),
                ("inevitable", "불가피한, 필연적인"),
                ("comprehend", "이해하다, 파악하다"),
                ("diminish", "줄어들다, 감소시키다"),
                ("elaborate", "정교한; 상세히 설명하다"),
                ("facilitate", "용이하게 하다, 촉진하다"),
                ("impede", "방해하다, 저해하다"),
                ("manifest", "나타내다; 명백한"),
                ("obscure", "불분명한; 가리다"),
                ("profound", "깊은, 심오한")
            ]
            
            data_to_insert = []
            word_idx = 1
            for day in range(1, 61):
                for in_day in range(1, 51):
                    base_en, base_ko = word_bases[(word_idx - 1) % len(word_bases)]
                    english = f"{base_en}_{word_idx}"
                    korean = f"{base_ko}_{word_idx}"
                    pos = poses[(word_idx - 1) % len(poses)]
                    emoji = emojis[(word_idx - 1) % len(emojis)]
                    example_en = f"This is an example sentence for {english}."
                    example_ko = f"이것은 {korean}을(를) 위한 수능 예문입니다."
                    importance = (word_idx % 3) + 1
                    
                    data_to_insert.append((english, korean, pos, example_en, example_ko, importance, emoji, day))
                    word_idx += 1
            
            conn.executemany("""
                INSERT OR IGNORE INTO words 
                (english, korean, part_of_speech, example_en, example_ko, importance, emoji, day_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
        # user_progress 테이블 동기화
        conn.execute("""
            INSERT OR IGNORE INTO user_progress (word_id)
            SELECT word_id FROM words
            WHERE word_id NOT IN (SELECT word_id FROM user_progress)
        """)

def load_words(day_number: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT w.*, p.study_status, p.skimming_result,
                   p.flashcard_cleared, p.quiz_passed, p.wrong_count
            FROM   words w
            JOIN   user_progress p ON w.word_id = p.word_id
            WHERE  w.day_number = ?
            ORDER  BY w.word_id
        """, (day_number,)).fetchall()
    return [dict(r) for r in rows]

def calc_completed_days() -> int:
    """모든 단어가 completed(완료) 처리된 Day의 총 개수 계산"""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT w.day_number, 
                   COUNT(w.word_id) as total,
                   SUM(CASE WHEN p.study_status='completed' THEN 1 ELSE 0 END) as completed
            FROM   words w
            JOIN   user_progress p ON w.word_id = p.word_id
            GROUP  BY w.day_number
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
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET skimming_result=?,study_status=? WHERE word_id=?",
            (result, status, word_id),
        )

def db_set_flashcard(word_id: int, cleared: bool) -> None:
    status = "reviewing" if cleared else "unknown"
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET flashcard_cleared=?,study_status=? WHERE word_id=?",
            (1 if cleared else 0, status, word_id),
        )

def db_set_quiz(word_id: int, passed: bool) -> None:
    with get_conn() as conn:
        if passed:
            conn.execute(
                "UPDATE user_progress SET quiz_passed=1,study_status='completed' WHERE word_id=?",
                (word_id,),
            )
        else:
            conn.execute(
                "UPDATE user_progress SET wrong_count=wrong_count+1,study_status='needs_retry' WHERE word_id=?",
                (word_id,),
            )

def load_wrong_words() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT w.word_id, w.english, w.korean, w.part_of_speech,
                   w.example_en, w.example_ko, w.emoji,
                   p.wrong_count, p.study_status
            FROM   words w
            JOIN   user_progress p ON w.word_id = p.word_id
            WHERE  p.wrong_count > 0
            ORDER  BY p.wrong_count DESC, w.english ASC
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
            SELECT w.english, w.korean, p.wrong_count 
            FROM   words w 
            JOIN   user_progress p ON w.word_id = p.word_id 
            WHERE  p.wrong_count > 0 
            ORDER  BY p.wrong_count DESC, w.english ASC 
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
    with get_conn() as conn:
        conn.execute("""
            UPDATE user_progress
            SET study_status='unseen',skimming_result='pending',
                flashcard_cleared=0,quiz_passed=0,wrong_count=0
            WHERE word_id IN (SELECT word_id FROM words WHERE day_number=?)
        """, (day_number,))

def db_reset_wrong_count(word_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET wrong_count=0, study_status='completed' WHERE word_id=?",
            (word_id,),
        )

# ══════════════════════════════════════════════════════════════════
#  ⑤ SESSION STATE SYSTEM & DEFENSIVE PROGRAMMING
# ══════════════════════════════════════════════════════════════════
def init_session() -> None:
    defaults = {
        "page":           "home",
        "active_tab":     "home",
        "current_day":    1,
        "all_words":      [],
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
    ss.all_words = load_words(day)

# ══════════════════════════════════════════════════════════════════
#  ⑥ GLOBAL CSS (PREMIUM DARK GLASSMORPHISM STYLE)
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
    position: relative;
    z-index: 1;
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
    background: rgba(255,255,255,0.02);
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
#  ⑦ UI COMPONENTS
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
    """오늘 학습 후보 단어 중 9개를 3x3 격자 형태로 예고 렌더링 (스펠링만 크게)"""
    shown = words[:9]
    html = '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px;">'
    for w in shown:
        en = w.get("english", "")
        # '_' 이후의 숫자를 잘라내어 프리미엄 표시 (더미데이터용)
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
        en = w.get("english", "").split("_")[0]
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
#  ⑧ PAGE: HOME & DAY SELECTOR
# ══════════════════════════════════════════════════════════════════
def page_home() -> None:
    ss = st.session_state
    progress_pct = calc_progress_pct()
    
    # ── 학습할 Day 선택 (60일치 셀렉트박스 연동) ────────────────
    day_options = [f"Day {i}" for i in range(1, 61)]
    
    # 상단 대시보드 렌더링
    render_top_header(progress_pct, ss.current_day)

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

    # 1. 학습할 Day 골라 세팅
    st.markdown('<div class="sec-lbl">🎯 커리큘럼 선택</div>', unsafe_allow_html=True)
    selected_day_str = st.selectbox(
        "학습할 Day를 골라주세요",
        options=day_options,
        index=ss.current_day - 1,
        key="day_selector"
    )
    selected_day = int(selected_day_str.split(" ")[-1])
    
    # Day 변경 시 안정적인 세션 리셋
    if selected_day != ss.current_day:
        ss.current_day = selected_day
        reset_all_session()
        st.rerun()

    # 단어 로드
    words = ss.all_words
    total_day_words = len(words)  # 50개

    st.markdown('<div class="sec-lbl">📅 오늘의 학습 진행 현황 (총 {}단어)</div>'.format(total_day_words), unsafe_allow_html=True)

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
        <div class="pc-desc">오늘의 50단어를 10개씩 분류하며 아는 단어와 모르는 단어를 걸러냅니다.</div>
    </div>
</div>""", unsafe_allow_html=True)

    if not skim_done:
        if st.button("바로 시작", use_container_width=True, type="primary", key="go_skim"):
            db_reset_today(ss.current_day)
            ss.all_words = load_words(ss.current_day)
            ss.skim_index = 0
            ss.skim_page = 0
            ss.skim_states = {w["word_id"]: "pending" for w in ss.all_words}
            ss.unknown_ids = []
            ss.skimming_done = False
            ss.all_mastered = False
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

    # ── 데이터 엑셀/CSV 업로드 가이드라인 확장성 추가 ────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    with st.expander("📂 대량 단어 엑셀/CSV 데이터 업로드"):
        st.info(" Day 1~60번 대량 단어를 CSV 파일로 로드할 수 있는 기능 템플릿입니다.")
        uploaded_file = st.file_uploader("단어 CSV 파일 선택 (.csv)", type=["csv"])
        if uploaded_file is not None:
            st.success("파일 업로드 완료! (추후 로컬 DB 대량 삽입 기능에 연결됨)")

    render_bottom_nav("home")

# ══════════════════════════════════════════════════════════════════
#  ⑨ PAGE: SKIMMING (10-WORDS PAGINATION OPTIMIZED FOR MOBILE)
# ══════════════════════════════════════════════════════════════════
def page_skimming() -> None:
    ss = st.session_state
    words = ss.all_words
    total = len(words)  # 50개

    if total == 0:
        ss.skimming_done = True
        ss.page = "home"
        st.rerun()
        return

    # 세션 상태 방어 코드
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

    # 10개 슬라이싱 계산
    ITEMS_PER_PAGE = 10
    start_idx = ss.skim_page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total)
    page_words = words[start_idx:end_idx]

    # 집계 통계
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
    st.markdown(f'<div style="color:#8b949e;font-size:0.75rem;margin:4px 0 14px">{ss.skim_page + 1} / 5 페이지 ({start_idx+1}~{end_idx}번째 단어) · 전체 {classified_n}/{total} 분류 완료</div>', unsafe_allow_html=True)

    # 모바일용 가로 2열 배치 그리드
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
            # '_' 이후의 숫자 제거 및 노출
            english_display = word["english"].split("_")[0]
            state_icon = {"know": "✅", "unknown": "📌", "pending": ""}.get(state, "")

            # 분류 상태별 동적 배경/테두리
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

    # 10개 단위 페이지네이션 제어
    p1, p2 = st.columns(2)
    with p1:
        if st.button("← 이전 10개", key="prev_page", use_container_width=True, disabled=(ss.skim_page == 0)):
            ss.skim_page -= 1
            st.rerun()
    with p2:
        if st.button("다음 10개 →", key="next_page", use_container_width=True, disabled=(ss.skim_page == 4 or end_idx >= total)):
            ss.skim_page += 1
            st.rerun()

    # 스키밍 최종 완료
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    all_classified = all(v != "pending" for v in states.values())
    
    if not all_classified:
        st.markdown(f'<div style="color:#8b949e;font-size:0.8rem;text-align:center;margin-bottom:10px">⚠️ 50개 단어를 모두 분류해야 완료할 수 있습니다. (남은 미분류: {pending_n}개)</div>', unsafe_allow_html=True)

    if st.button(f"선택 완료 및 학습 시작 🚀 (몰라요 {unknown_n}개)", use_container_width=True, type="primary", disabled=not all_classified):
        for w in words:
            res = states.get(w["word_id"], "know")
            db_set_skimming(w["word_id"], res)

        ss.unknown_ids = [wid for wid, s in states.items() if s == "unknown"]
        ss.all_words = load_words(ss.current_day)
        ss.skimming_done = True
        
        if not ss.unknown_ids:
            ss.flashcard_done = True
            ss.quiz_done = True
            ss.all_mastered = True
            ss.page = "home"
        else:
            ss.all_mastered = False
            # 플래시카드로 바로 진입
            ss.page = "flashcard"
            ss.fc_index = 0
            ss.fc_show_meaning = False
            ss.fc_visited = set()
            ss.flashcard_done = False

        st.rerun()

# ══════════════════════════════════════════════════════════════════
#  ⑩ PAGE: FLASHCARD
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
    english_display = word['english'].split("_")[0]
    korean_display = word['korean'].split("_")[0]
    example_en_display = word['example_en']
    example_ko_display = word['example_ko']

    # 플래시카드 렌더링
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
                {example_en_display}
                <span class="fc-ex-ko">{example_ko_display}</span>
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
    # 50개 단어로 늘어난 경우 돗 개수 최대 10개만 간접 표시
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
#  ⑪ PAGE: QUIZ
# ══════════════════════════════════════════════════════════════════
NUMS = ["①", "②", "③", "④"]

def _build_choices(word: dict, all_words: list[dict]) -> tuple[list[str], str]:
    answer = word["korean"].split("_")[0]
    # 오답 풀을 구성 (Day 전체 단어에서 다른 단어 뜻 3개 추출)
    pool = list(set([w["korean"].split("_")[0] for w in all_words if w["word_id"] != word["word_id"] and w["korean"].split("_")[0] != answer]))
    
    # 만약 풀이 부족할 경우 대비
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
                        english_clean = w['english'].split("_")[0]
                        korean_clean = w['korean'].split("_")[0]
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
            ss.page = "home"
            st.rerun()
        return

    st.progress(done_n / total if total else 0.0)
    st.markdown(f'<div style="color:#8b949e;font-size:0.75rem;margin:4px 0 14px">{done_n + 1} / {total}번째 문제</div>', unsafe_allow_html=True)

    current_id = queue[0]
    word = word_map.get(current_id)

    if not ss.quiz_choices:
        choices, answer = _build_choices(word, ss.all_words)
        ss.quiz_choices = choices
        ss.quiz_answer = answer
        ss.quiz_answered = False
        ss.quiz_correct = False

    pos_css, glow_var, bg_grad = _pos_style(word["part_of_speech"])
    emoji = word.get("emoji", "📚")
    glow_color = glow_var.split(":", 1)[-1]
    english_clean = word['english'].split("_")[0]

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
#  ⑫ PAGE: LIBRARY (오답 노트 & 마스터)
# ══════════════════════════════════════════════════════════════════
def page_library() -> None:
    ss = st.session_state
    progress_pct = calc_progress_pct()
    render_top_header(progress_pct, ss.current_day)

    lib_tab = st.query_params.get("lib", "wrong")
    if isinstance(lib_tab, list):
         lib_tab = lib_tab[0] if lib_tab else "wrong"

    s1, s2 = st.columns(2)
    with s1:
        if st.button("📕  오답 노트", key="btn_tab_wrong", type="primary" if lib_tab == "wrong" else "secondary", use_container_width=True):
            st.query_params["lib"] = "wrong"
            st.rerun()
    with s2:
        if st.button("📚  전체 단어장", key="btn_tab_all", type="primary" if lib_tab == "all" else "secondary", use_container_width=True):
            st.query_params["lib"] = "all"
            st.rerun()

    if lib_tab != "all":
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
                english_clean = w['english'].split("_")[0]
                korean_clean = w['korean'].split("_")[0]

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
                    ss.all_words = load_words(ss.current_day)
                    st.rerun()
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    else:
        # 현재 선택된 Day의 전체 단어 리스트 노출
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
            english_clean = w['english'].split("_")[0]
            korean_clean = w['korean'].split("_")[0]

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

    render_bottom_nav("library")

# ══════════════════════════════════════════════════════════════════
#  ⑬ PAGE: STATS
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
            english_clean = w['english'].split("_")[0]
            korean_clean = w['korean'].split("_")[0]
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
#  ⑭ MAIN ROUTER & STABILITY CHECK
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    init_db()
    inject_css()
    init_session()

    ss = st.session_state
    
    # 단어 목록 최초 로드 방어
    if not ss.all_words:
        ss.all_words = load_words(ss.current_day)

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

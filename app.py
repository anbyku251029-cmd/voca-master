"""
🚀 ANTIGRAVITY — 망각의 중력을 거스르는 수능 영단어 앱
=======================================================
기술 스택 : Python 3.10+ · Streamlit · SQLite3
실행 방법 : streamlit run app.py
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

# ══════════════════════════════════════════════════════════════════
#  ① PAGE CONFIG
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Antigravity — 수능 영단어",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════
#  ② CONSTANTS
# ══════════════════════════════════════════════════════════════════
DB_PATH        = Path(__file__).parent / "antigravity.db"
SUNEUNG_DATE   = date(2027, 11, 18)
STUDY_START    = date(2026, 1, 10)
TODAY          = date.today()
D_DAY          = max(0, (SUNEUNG_DATE - TODAY).days)
STUDY_DAY      = max(1, (TODAY - STUDY_START).days + 1)
UNKNOWN_TARGET = 5           # 스키밍에서 선택할 '모르는 단어' 수

WEEKDAYS_KR    = ["일", "월", "화", "수", "목", "금", "토"]

# 단어 스트립 카드 그라디언트 (위치별 고정)
STRIP_GRADS = [
    "#1a3a5c,#0d2035", "#2d1a3a,#1a0d2e", "#1a2d1a,#0d200d",
    "#3a2a1a,#2e1e0d", "#1a2a3a,#0d1e2e", "#2a1a3a,#1e0d2e",
    "#3a1a2a,#2e0d1e",
]

# ══════════════════════════════════════════════════════════════════
#  ③ SEED DATA
# ══════════════════════════════════════════════════════════════════
SEED_WORDS = [
    # (english, korean, part_of_speech, example_en, example_ko, importance, emoji)
    ("pure",       "순수한, 순결한",           "형용사", "Her motives were pure.",                    "그녀의 동기는 순수했다.",             2, "✨"),
    ("preclude",   "방해하다, 불가능하게 하다", "동사",   "His injury precluded him from running.",    "부상이 그의 달리기를 불가능하게 했다.", 1, "⛔"),
    ("ambiguous",  "모호한, 불분명한",          "형용사", "The statement was ambiguous.",              "그 진술은 모호했다.",                 2, "🌫️"),
    ("phenomenon", "현상",                    "명사",   "It is a global phenomenon.",               "그것은 세계적인 현상이다.",            1, "🌍"),
    ("persist",    "지속하다, 고집하다",        "동사",   "The problem persists.",                    "문제가 지속된다.",                    2, "🔄"),
    ("subsequent", "그 다음의, 뒤이은",        "형용사", "Subsequent events proved him right.",      "다음 사건이 그가 옳음을 증명했다.",     2, "⏩"),
    ("inevitable", "불가피한, 필연적인",       "형용사", "Change is inevitable.",                    "변화는 불가피하다.",                  1, "⚡"),
    ("comprehend", "이해하다, 파악하다",        "동사",   "I could not comprehend the instructions.", "나는 지시를 이해할 수 없었다.",         2, "💡"),
    ("diminish",   "줄어들다, 감소시키다",      "동사",   "The pain began to diminish.",              "통증이 줄어들기 시작했다.",            2, "📉"),
    ("elaborate",  "정교한; 상세히 설명하다",   "형용사", "She elaborated on her plan.",              "그녀는 계획을 상세히 설명했다.",        3, "🔬"),
    ("facilitate", "용이하게 하다, 촉진하다",   "동사",   "Technology facilitates communication.",    "기술은 소통을 용이하게 한다.",          1, "🚀"),
    ("impede",     "방해하다, 저해하다",        "동사",   "Lack of funds impeded the project.",       "자금 부족이 프로젝트를 저해했다.",      2, "🚧"),
    ("manifest",   "나타내다; 명백한",          "동사",   "Symptoms manifest differently.",            "증상은 다르게 나타난다.",              2, "🌟"),
    ("obscure",    "불분명한; 가리다",          "형용사", "The meaning was obscure.",                 "의미가 불분명했다.",                  3, "🌑"),
    ("profound",   "깊은, 심오한",             "형용사", "He had a profound impact on science.",     "그는 과학에 심오한 영향을 미쳤다.",     1, "🌊"),
]

# ══════════════════════════════════════════════════════════════════
#  ④ DATABASE LAYER
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
        for w in SEED_WORDS:
            conn.execute(
                "INSERT OR IGNORE INTO words "
                "(english,korean,part_of_speech,example_en,example_ko,importance,emoji,day_number) "
                "VALUES(?,?,?,?,?,?,?,1)",
                (w[0], w[1], w[2], w[3], w[4], w[5], w[6]),
            )
        conn.execute("""
            INSERT OR IGNORE INTO user_progress (word_id)
            SELECT word_id FROM words
            WHERE word_id NOT IN (SELECT word_id FROM user_progress)
        """)


def load_words() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT w.*, p.study_status, p.skimming_result,
                   p.flashcard_cleared, p.quiz_passed, p.wrong_count
            FROM   words w
            JOIN   user_progress p ON w.word_id = p.word_id
            WHERE  w.day_number = 1
            ORDER  BY w.word_id
        """).fetchall()
    return [dict(r) for r in rows]


def calc_progress_pct() -> float:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM user_progress").fetchone()[0]
        done  = conn.execute(
            "SELECT COUNT(*) FROM user_progress WHERE study_status='completed'"
        ).fetchone()[0]
    return (done / total * 100) if total else 0.0


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
    """퀴즈 결과 저장: 오답 시 wrong_count +1"""
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
    """오답 횟수가 1 이상인 단어를 오답 많은 순으로 반환"""
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


def db_reset_today() -> None:
    with get_conn() as conn:
        conn.execute("""
            UPDATE user_progress
            SET study_status='unseen',skimming_result='pending',
                flashcard_cleared=0,quiz_passed=0,wrong_count=0
            WHERE word_id IN (SELECT word_id FROM words WHERE day_number=1)
        """)


def get_stats_data() -> dict:
    """분석 탭에서 시각화할 전체 학습 통계 및 취약 단어 정보를 반환"""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM user_progress").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM user_progress WHERE study_status='completed'").fetchone()[0]
        unseen = conn.execute("SELECT COUNT(*) FROM user_progress WHERE study_status='unseen'").fetchone()[0]
        wrong_total = conn.execute("SELECT SUM(wrong_count) FROM user_progress").fetchone()[0] or 0
        wrong_words_count = conn.execute("SELECT COUNT(*) FROM user_progress WHERE wrong_count > 0").fetchone()[0]
        
        # 오답률 Top 3 단어 가져오기
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



# ══════════════════════════════════════════════════════════════════
#  ⑤ SESSION STATE 초기화
# ══════════════════════════════════════════════════════════════════
def init_session() -> None:
    defaults: dict = {
        "page":           "home",
        "active_tab":     "home",
        "all_words":      [],
        # skimming
        "skim_index":     0,
        "skim_states":    {},   # {word_id: 'know'|'unknown'|'pending'}
        "unknown_ids":    [],
        "skimming_done":  False,
        # flashcard (새 구조: 인덱스 기반 + 뜻 토글 + 기억 추적)
        "fc_index":       0,       # 현재 카드 인덱스
        "fc_show_meaning": False,  # 뜻 보기 토글 상태
        "fc_cleared_ids": [],      # '기억했어요' 완료된 word_id 목록
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
    keys: dict = {
        "skim_index": 0, "skim_states": {}, "unknown_ids": [],
        "skimming_done": False,
        "fc_index": 0, "fc_show_meaning": False, "fc_cleared_ids": [],
        "flashcard_done": False,
        "quiz_queue": [], "quiz_results": {}, "quiz_answered": False,
        "quiz_correct": False, "quiz_choices": [], "quiz_answer": "",
        "quiz_done": False,
    }
    for k, v in keys.items():
        st.session_state[k] = v
    st.session_state.all_words = load_words()


# ══════════════════════════════════════════════════════════════════
#  ⑥ GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
def inject_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ─── 전역 ─── */
html, body, [class*="css"] {
    font-family: 'Inter','Apple SD Gothic Neo','Noto Sans KR',sans-serif;
}
.stApp { background: #0d1117; }
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 0 !important;
    padding-bottom: 100px !important;
    max-width: 480px !important;
}

/* ─── 상단 헤더 (sticky) ─── */
.top-header {
    background: rgba(13,17,23,0.96);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding: 14px 4px 12px;
    margin-bottom: 18px;
    position: sticky; top: 0; z-index: 200;
}
.header-row1 {
    display: flex; align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}
.exam-label {
    font-size: 1.35rem; font-weight: 800;
    color: #f0f6fc; cursor: pointer;
    display: flex; align-items: center; gap: 5px;
}
.exam-arrow { color: #8b949e; font-size: 0.8rem; margin-top: 2px; }
.dday-pill {
    display: flex; align-items: center; gap: 7px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 50px;
    padding: 6px 14px;
    font-size: 0.82rem; font-weight: 700; color: #f0f6fc;
}
.pill-ring {
    width: 14px; height: 14px;
    border-radius: 50%;
    border: 2px solid rgba(255,255,255,0.2);
    border-top-color: #60a5fa;
    flex-shrink: 0;
}
.pill-sep { color: rgba(255,255,255,0.22); }
.avatar-dot {
    width: 32px; height: 32px; border-radius: 50%;
    background: linear-gradient(135deg,#3b82f6,#8b5cf6);
    flex-shrink: 0;
}

/* ─── 주간 캘린더 ─── */
.week-cal {
    display: grid; grid-template-columns: repeat(7,1fr);
    gap: 4px; margin-bottom: 14px;
}
.wc-col {
    display: flex; flex-direction: column;
    align-items: center; gap: 5px;
}
.wc-day {
    font-size: 0.68rem; font-weight: 500;
    color: #6e7681; text-transform: uppercase;
}
.wc-num {
    width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%;
    color: #6e7681; font-size: 0.8rem; font-weight: 500;
}
.wc-num.today {
    background: #1f2937;
    border: 2px solid #3b82f6;
    color: #fff; font-weight: 800;
}
.wc-num.has-study {
    background: rgba(52,211,153,0.12);
    color: #34d399;
}
.wc-day.sun { color: #f85149; }
.wc-day.sat { color: #60a5fa; }
.wc-day.today-lbl { color: #60a5fa; font-weight: 700; }

/* ─── 진척도 바 (헤더 내부) ─── */
.hdr-prog-wrap {
    height: 3px;
    background: rgba(255,255,255,0.07);
    border-radius: 3px; overflow: hidden;
    margin-bottom: 12px;
}
.hdr-prog-fill {
    height: 100%;
    background: linear-gradient(90deg,#3b82f6,#8b5cf6);
    border-radius: 3px;
    transition: width .4s ease;
}

/* ─── Day 레이블 ─── */
.day-lbl {
    font-size: 1.3rem; font-weight: 800;
    color: #f0f6fc; letter-spacing: -0.01em;
}

/* ─── 홈 단계 카드 ─── */
.phase-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 20px; overflow: hidden;
    margin-bottom: 14px;
    transition: border-color .25s, box-shadow .25s;
}
.phase-card:not(.locked):hover {
    border-color: #3b82f6;
    box-shadow: 0 0 0 1px rgba(59,130,246,.2);
}
.phase-card.locked { opacity: .42; pointer-events: none; }

/* 단어 미리보기 스트립 */
.word-strip {
    display: flex; gap: 5px;
    padding: 10px 12px 0;
    height: 82px; overflow: hidden;
}
.ws-item {
    flex: 1; border-radius: 9px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: flex-end;
    padding-bottom: 5px; min-width: 0;
    overflow: hidden; position: relative;
}
.ws-item:first-child { flex: 1.5; }
.ws-item::after {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,.55) 0%, transparent 55%);
    border-radius: 9px;
}
.ws-emoji { font-size: 1.5rem; position: relative; z-index: 1; }
.ws-en {
    font-size: 0.56rem; font-weight: 700; color: #fff;
    position: relative; z-index: 1;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; width: 100%; text-align: center;
    padding: 0 2px;
}
.ws-ko {
    font-size: 0.50rem; color: rgba(255,255,255,.65);
    position: relative; z-index: 1;
    white-space: nowrap; text-align: center;
}

/* 단계 카드 바디 */
.pc-body { padding: 11px 16px 15px; }
.pc-hd {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 8px;
}
.pc-title { font-size: .98rem; font-weight: 700; color: #f0f6fc; }
.pc-filter { color: #6e7681; font-size: .9rem; }
.pc-prog {
    height: 4px; background: rgba(255,255,255,.07);
    border-radius: 4px; margin-bottom: 7px; overflow: hidden;
}
.pc-prog-fill {
    height: 100%; background: #3b82f6;
    border-radius: 4px; transition: width .3s;
}
.pc-meta {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 8px;
}
.pc-status { font-size: .76rem; color: #6e7681; }
.pc-status.done { color: #34d399; }
.pc-time { font-size: .76rem; font-weight: 600; color: #3b82f6; }
.pc-desc { font-size: .80rem; color: #6e7681; line-height: 1.5; margin-bottom: 11px; }

/* ─── 단어 학습 카드 ─── */
.word-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 24px; overflow: hidden;
    margin: 0 auto 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,.45);
}
.wc-img {
    width: 100%; height: 180px;
    display: flex; align-items: center; justify-content: center;
    font-size: 5.5rem; position: relative;
}
.wc-img-glow {
    position: absolute; inset: 0;
    background: radial-gradient(ellipse at center,
        var(--glow) 0%, transparent 70%);
    pointer-events: none;
}
.wc-body { padding: 20px 22px 18px; }
.wc-en {
    font-size: 1.95rem; font-weight: 900;
    color: #f0f6fc; letter-spacing: -.02em; margin-bottom: 2px;
}
.wc-pos {
    font-size: .72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em;
    margin-bottom: 10px;
}
.wc-ko { font-size: 1.12rem; font-weight: 600; color: #e6edf3; }
.wc-example {
    margin-top: 14px; padding: 10px 12px;
    background: rgba(59,130,246,.07);
    border-left: 3px solid #3b82f6;
    border-radius: 0 10px 10px 0;
    font-size: .82rem; color: #8b949e; line-height: 1.65;
}
.wc-ex-ko { color: #60a5fa; font-size: .78rem; }

/* ─── 퀴즈 문제 카드 ─── */
.quiz-qcard {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 22px; padding: 22px; margin-bottom: 18px;
}
.qq-label {
    font-size: .7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .12em; color: #6e7681; margin-bottom: 12px;
}
.qq-word {
    font-size: 2.1rem; font-weight: 900;
    color: #f0f6fc; letter-spacing: -.02em;
}
.qq-pos { color: #3b82f6; font-size: .78rem; font-weight: 600; margin-top: 5px; }

/* ─── 결과 ─── */
.result-hero {
    background: linear-gradient(135deg,rgba(52,211,153,.08),rgba(59,130,246,.05));
    border: 1px solid rgba(52,211,153,.2);
    border-radius: 24px; padding: 28px 20px;
    text-align: center; margin-bottom: 18px;
}
.stat-card {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 16px; padding: 14px 10px; text-align: center;
}
.sc-lbl { color:#6e7681; font-size:.66rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em; margin-bottom:6px; }
.sc-val { font-size:1.55rem; font-weight:900; line-height:1.1; }

/* ─── 오답 아이템 ─── */
.wrong-item {
    background: rgba(248,81,73,.07); border: 1px solid rgba(248,81,73,.14);
    border-radius: 12px; padding: 10px 14px; margin-bottom: 8px;
    display: flex; justify-content: space-between; align-items: center;
}
.wi-en { color: #f85149; font-weight:700; font-size:.92rem; }
.wi-ko { color: #8b949e; font-size:.78rem; }

/* ─── 색상 유틸 ─── */
.c-green { color: #34d399 !important; }
.c-red   { color: #f85149 !important; }
.c-blue  { color: #60a5fa !important; }
.c-purple { color: #bc8cff !important; }

/* ─── 섹션 레이블 ─── */
.sec-lbl {
    color: #6e7681; font-size: .68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .15em; margin-bottom: 10px;
}

/* ─── 배지 ─── */
.badge {
    display: inline-block;
    background: linear-gradient(135deg,#1d4ed8,#5b21b6);
    color: #fff; border-radius: 50px;
    padding: 4px 13px; font-size: .78rem; font-weight: 700;
}

/* ─── 하단 고정 네비게이션 ─── */
.bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: rgba(13,17,23,.97);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-top: 1px solid rgba(255,255,255,.06);
    padding: 10px 0 18px;
    display: flex; justify-content: space-around; align-items: center;
    z-index: 9999;
}
.nav-item {
    display: flex; flex-direction: column;
    align-items: center; gap: 3px;
    text-decoration: none !important;
    color: #484f58; font-size: .63rem; font-weight: 600;
    transition: color .2s; min-width: 56px;
    cursor: pointer;
}
.nav-item:hover { color: #60a5fa; text-decoration: none !important; }
.nav-item.active { color: #60a5fa; }
.nav-icon { font-size: 1.25rem; line-height: 1; }
.nav-fab {
    width: 42px; height: 42px;
    background: linear-gradient(135deg,#3b82f6,#8b5cf6);
    border-radius: 50%; display: flex;
    align-items: center; justify-content: center;
    color: #fff; font-size: 1.1rem; font-weight: 800;
    box-shadow: 0 4px 16px rgba(59,130,246,.45);
    cursor: pointer;
}

/* ─── 라이브러리 / 분석 플레이스홀더 ─── */
.placeholder-box {
    background: #161b22; border: 1px dashed #30363d;
    border-radius: 20px; padding: 50px 30px; text-align: center;
    margin-top: 20px;
}
.ph-icon { font-size: 3rem; margin-bottom: 12px; }
.ph-title { color: #e6edf3; font-size: 1rem; font-weight: 700; margin-bottom: 6px; }
.ph-desc { color: #6e7681; font-size: .82rem; line-height: 1.6; }

/* ─── Streamlit 기본 요소 오버라이드 ─── */
.stButton > button {
    border-radius: 14px !important; font-weight: 700 !important;
    font-size: .88rem !important;
    background: #161b22 !important; border: 1px solid #30363d !important;
    color: #e6edf3 !important; transition: all .2s !important;
    padding: .55rem .9rem !important;
}
.stButton > button:hover {
    background: #21262d !important; border-color: #3b82f6 !important;
    color: #fff !important;
}
.stButton > button[kind="primary"] {
    background: #f0f6fc !important; border-color: #f0f6fc !important;
    color: #0d1117 !important; font-weight: 800 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #cdd9e5 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(240,246,252,.15) !important;
}
/* st.progress 오버라이드 */
.stProgress > div > div {
    background: linear-gradient(90deg,#3b82f6,#8b5cf6) !important;
    border-radius: 4px !important;
}
.stProgress > div {
    background: rgba(255,255,255,.07) !important;
    border-radius: 4px !important; height: 5px !important;
}
div[data-testid="stMarkdownContainer"] p { color: #8b949e; }
hr { border-color: rgba(255,255,255,.06) !important; margin: 14px 0 !important; }

/* ─── 스키밍 그리드 카드 ─── */
.sg-card {
    border-radius: 18px;
    padding: 14px 8px 10px;
    text-align: center;
    margin-bottom: 6px;
    transition: border-color .2s, background .2s, box-shadow .2s;
    min-height: 120px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 6px;
    cursor: default;
    position: relative;
    overflow: hidden;
}
.sg-card.pending {
    background: #161b22;
    border: 1.5px solid #21262d;
}
.sg-card.know {
    background: rgba(52,211,153,.09);
    border: 1.5px solid rgba(52,211,153,.5);
    box-shadow: 0 0 14px rgba(52,211,153,.10);
}
.sg-card.unknown {
    background: rgba(59,130,246,.10);
    border: 1.5px solid rgba(59,130,246,.55);
    box-shadow: 0 0 14px rgba(59,130,246,.12);
}
.sg-emoji { font-size: 1.8rem; line-height: 1; }
.sg-word {
    font-size: .82rem; font-weight: 800;
    color: #f0f6fc; letter-spacing: -.01em;
    word-break: break-all; line-height: 1.2;
    padding: 0 2px;
}
.sg-state-icon {
    position: absolute; top: 7px; right: 8px;
    font-size: .85rem; line-height: 1;
}

/* 스키밍 요약 바 */
.skim-summary {
    display: flex; gap: 8px;
    margin: 14px 0 16px;
}
.ss-chip {
    flex: 1; border-radius: 12px;
    padding: 8px 4px; text-align: center;
    border: 1px solid;
}
.ss-chip.know   { background:rgba(52,211,153,.08);  border-color:rgba(52,211,153,.3);  }
.ss-chip.unk    { background:rgba(59,130,246,.08);  border-color:rgba(59,130,246,.3);  }
.ss-chip.pend   { background:rgba(255,255,255,.04); border-color:rgba(255,255,255,.1); }
.ss-num  { font-size: 1.3rem; font-weight: 900; line-height: 1; }
.ss-lbl  { font-size: .62rem; font-weight: 600; letter-spacing: .05em;
           text-transform: uppercase; margin-top: 3px; }
.ss-chip.know  .ss-num { color: #34d399; }
.ss-chip.unk   .ss-num { color: #60a5fa; }
.ss-chip.pend  .ss-num { color: #8b949e; }
.ss-chip.know  .ss-lbl { color: #34d399; }
.ss-chip.unk   .ss-lbl { color: #60a5fa; }
.ss-chip.pend  .ss-lbl { color: #6e7681; }

/* 스키밍 버튼: 알아요(초록) / 몰라요(파랑) 활성 상태 오버라이드 */
.btn-know-active > button {
    background: rgba(52,211,153,.18) !important;
    border-color: #34d399 !important;
    color: #34d399 !important;
}
.btn-unk-active > button {
    background: rgba(59,130,246,.18) !important;
    border-color: #60a5fa !important;
    color: #60a5fa !important;
}

/* ─── 플래시카드 디자인 ─── */
.fc-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 24px;
    overflow: hidden;
    margin: 0 auto 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,.45);
}
.fc-img {
    width: 100%;
    height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
}
.fc-img-label {
    position: absolute;
    bottom: 10px;
    font-size: 0.65rem;
    font-weight: 700;
    color: rgba(255,255,255,0.3);
    letter-spacing: 0.1em;
}
.fc-body {
    padding: 22px;
}
.fc-word-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
}
.fc-en {
    font-size: 2.1rem;
    font-weight: 900;
    color: #f0f6fc;
    letter-spacing: -0.02em;
}
.fc-sound {
    font-size: 0.72rem;
    font-weight: 700;
    color: #8b949e;
    background: rgba(255,255,255,0.06);
    padding: 4px 8px;
    border-radius: 8px;
    cursor: pointer;
    border: 1px solid rgba(255,255,255,0.05);
}
.fc-sound:hover {
    color: #60a5fa;
    background: rgba(96,165,250,0.1);
}
.fc-pos {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 14px;
}
.fc-meaning {
    margin-top: 14px;
    animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}
.fc-ko {
    font-size: 1.25rem;
    font-weight: 700;
    color: #e6edf3;
    margin-bottom: 12px;
}
.fc-example {
    padding: 12px;
    background: rgba(59,130,246,0.06);
    border-left: 3px solid #3b82f6;
    border-radius: 0 12px 12px 0;
    font-size: 0.85rem;
    color: #c9d1d9;
    line-height: 1.6;
}
.fc-ex-ko {
    display: block;
    color: #8b949e;
    font-size: 0.78rem;
    margin-top: 4px;
}

/* ─── 플래시카드 점 표시기 ─── */
.fc-dots {
    display: flex;
    justify-content: center;
    gap: 6px;
    margin: 12px 0;
}
.fc-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #30363d;
    transition: all 0.25s ease;
}
.fc-dot.active {
    background: #3b82f6;
    transform: scale(1.3);
}
.fc-dot.cleared {
    background: #34d399;
}

/* ─── 퀴즈 버튼 스타일 ─── */
.qbtn-correct > button {
    background: rgba(52,211,153,0.18) !important;
    border-color: #34d399 !important;
    color: #34d399 !important;
    pointer-events: none;
}
.qbtn-wrong > button {
    background: rgba(248,81,73,0.18) !important;
    border-color: #f85149 !important;
    color: #f85149 !important;
    pointer-events: none;
}
.qbtn-dim > button {
    opacity: 0.4;
    pointer-events: none;
}

/* ─── 오답 노트 카드 ─── */
.wn-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 16px;
    padding: 14px 16px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 14px;
    transition: border-color 0.2s;
}
.wn-card:hover {
    border-color: #30363d;
}
.wn-emoji {
    font-size: 1.8rem;
    flex-shrink: 0;
}
.wn-info {
    flex-grow: 1;
    min-width: 0;
}
.wn-en {
    font-size: 1.05rem;
    font-weight: 800;
    color: #f0f6fc;
}
.wn-ko {
    font-size: 0.85rem;
    color: #c9d1d9;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.wn-pos {
    font-size: 0.65rem;
    font-weight: 700;
    margin-top: 4px;
}
.wn-wrong-badge {
    background: rgba(248,81,73,0.1);
    color: #f85149;
    border: 1px solid rgba(248,81,73,0.2);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 700;
    flex-shrink: 0;
}
.wn-empty {
    background: #161b22;
    border: 1px dashed #30363d;
    border-radius: 20px;
    padding: 40px 20px;
    text-align: center;
    color: #8b949e;
    font-size: 0.85rem;
}
.wn-empty-icon {
    font-size: 2.5rem;
    margin-bottom: 10px;
}

/* ─── 라이브러리 서브탭 ─── */
.lib-tabs {
    display: flex;
    gap: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 10px;
    margin-bottom: 18px;
}
.lib-tab {
    flex: 1;
    text-align: center;
    padding: 8px 12px;
    border-radius: 10px;
    color: #8b949e !important;
    font-size: 0.85rem;
    font-weight: 700;
    text-decoration: none !important;
    transition: all 0.2s;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
}
.lib-tab:hover {
    color: #f0f6fc !important;
    background: rgba(255,255,255,0.05);
}
.lib-tab.active {
    color: #60a5fa !important;
    background: rgba(96,165,250,0.1);
    border-color: rgba(96,165,250,0.2);
}
</style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  ⑦ UI 컴포넌트
# ══════════════════════════════════════════════════════════════════

# 품사별 스타일 매핑
POS_STYLE = {
    "형용사": ("color:#60a5fa;", "--glow:rgba(96,165,250,.18)",
               "linear-gradient(160deg,#1a3a5c,#0d2035)"),
    "동사":   ("color:#34d399;", "--glow:rgba(52,211,153,.18)",
               "linear-gradient(160deg,#1a2d1a,#0d200d)"),
    "명사":   ("color:#bc8cff;", "--glow:rgba(188,140,255,.18)",
               "linear-gradient(160deg,#2d1a3a,#1a0d2e)"),
    "부사":   ("color:#fbbf24;", "--glow:rgba(251,191,36,.18)",
               "linear-gradient(160deg,#2d2a1a,#201e0d)"),
}
DEFAULT_POS_STYLE = ("color:#8b949e;", "--glow:rgba(139,148,158,.15)",
                     "linear-gradient(160deg,#1a1f27,#0d1117)")


def _pos_style(pos: str) -> tuple[str, str, str]:
    return POS_STYLE.get(pos, DEFAULT_POS_STYLE)


def render_top_header(progress_pct: float) -> None:
    """레퍼런스와 동일한 상단 헤더 렌더링"""
    # ── 주간 캘린더 날짜 계산 (일~토 기준)
    wd = TODAY.weekday()              # 0=Mon … 6=Sun
    days_since_sun = (wd + 1) % 7    # 이번 주 일요일까지 거슬러 올라갈 일수
    week_start = TODAY - timedelta(days=days_since_sun)

    cal_cols_html = ""
    for i, day_kr in enumerate(WEEKDAYS_KR):
        d = week_start + timedelta(days=i)
        is_today = (d == TODAY)
        is_sun   = (i == 0)
        is_sat   = (i == 6)
        day_cls  = "today-lbl" if is_today else ("sun" if is_sun else ("sat" if is_sat else ""))
        num_cls  = "today" if is_today else ""
        cal_cols_html += f"""
        <div class="wc-col">
            <span class="wc-day {day_cls}">{day_kr}</span>
            <span class="wc-num {num_cls}">{d.day}</span>
        </div>"""

    # ── 진척도 바 (커스텀 HTML)
    fill_pct = min(100, max(0, progress_pct))

    st.markdown(f"""
<div class="top-header">
    <!-- Row 1: 시험 라벨 + D-Day 뱃지 + 아바타 -->
    <div class="header-row1">
        <div class="exam-label">수능 <span class="exam-arrow">∨</span></div>
        <div class="dday-pill">
            <div class="pill-ring"></div>
            <span>{progress_pct:.1f}%</span>
            <span class="pill-sep">|</span>
            <span>D-{D_DAY}</span>
        </div>
        <div class="avatar-dot"></div>
    </div>
    <!-- Row 2: 주간 캘린더 -->
    <div class="week-cal">{cal_cols_html}</div>
    <!-- Row 3: 진척도 바 -->
    <div class="hdr-prog-wrap">
        <div class="hdr-prog-fill" style="width:{fill_pct:.1f}%"></div>
    </div>
    <!-- Row 4: Day 라벨 -->
    <div class="day-lbl">Day {STUDY_DAY}</div>
</div>
    """, unsafe_allow_html=True)


def render_bottom_nav(active_tab: str) -> None:
    """하단 고정 네비게이션 바"""
    tabs = [
        ("home",    "🏠", "홈"),
        ("library", "🔖", "라이브러리"),
        ("stats",   "📊", "분석"),
        ("member",  "💳", "멤버십"),
    ]
    items_html = ""
    for tab_id, icon, label in tabs:
        cls = "active" if active_tab == tab_id else ""
        items_html += (
            f'<a class="nav-item {cls}" href="?nav={tab_id}">'
            f'<span class="nav-icon">{icon}</span>'
            f'<span>{label}</span></a>'
        )
    st.markdown(
        f'<div class="bottom-nav">{items_html}'
        f'<div class="nav-fab">ㄱ</div></div>',
        unsafe_allow_html=True,
    )


def render_word_strip(words: list[dict]) -> str:
    """홈 단계 카드 상단 단어 미리보기 스트립 HTML 생성"""
    html = '<div class="word-strip">'
    shown = words[:7]
    for i, w in enumerate(shown):
        grad = STRIP_GRADS[i % len(STRIP_GRADS)]
        emoji = w.get("emoji", "📚")
        en = w.get("english", "")
        ko = w.get("korean", "")[:5]
        html += (
            f'<div class="ws-item" style="background:linear-gradient(160deg,{grad});">'
            f'<span class="ws-emoji">{emoji}</span>'
            f'<span class="ws-en">{en}</span>'
            f'<span class="ws-ko">{ko}</span>'
            f'</div>'
        )
    html += "</div>"
    return html


def render_word_card(word: dict, show_back: bool = False) -> None:
    """단어 학습 카드 (스키밍 / 플래시카드 공용)"""
    pos = word.get("part_of_speech", "명사")
    pos_color, glow_var, bg_grad = _pos_style(pos)
    emoji = word.get("emoji", "📚")

    back_html = ""
    if show_back:
        back_html = f"""
        <div class="wc-example">
            {word['example_en']}<br>
            <span class="wc-ex-ko">{word['example_ko']}</span>
        </div>"""

    st.markdown(f"""
<div class="word-card">
    <div class="wc-img" style="background:{bg_grad};{glow_var}">
        <div class="wc-img-glow"></div>
        <span style="position:relative;z-index:1;filter:drop-shadow(0 0 18px var(--glow,transparent))">
            {emoji}
        </span>
    </div>
    <div class="wc-body">
        <div class="wc-en">{word['english']}</div>
        <div class="wc-pos" style="{pos_color}">{pos}</div>
        <div class="wc-ko">{word['korean']}</div>
        {back_html}
    </div>
</div>
    """, unsafe_allow_html=True)


def render_page_header(icon: str, title: str, badge: str, back_key: str) -> None:
    """학습 내부 화면 상단 헤더 (← 홈 / 제목 / 배지)"""
    c1, c2, c3 = st.columns([2, 4, 3])
    with c1:
        if st.button("← 홈", key=back_key):
            st.session_state.page = "home"
            st.rerun()
    with c2:
        st.markdown(
            f'<div style="color:#f0f6fc;font-weight:700;font-size:1rem;padding-top:4px;">'
            f'{icon} {title}</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(f'<div style="text-align:right"><span class="badge">{badge}</span></div>',
                    unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  ⑧ PAGE: HOME
# ══════════════════════════════════════════════════════════════════
def page_home() -> None:
    ss           = st.session_state
    progress_pct = calc_progress_pct()
    words        = ss.all_words

    render_top_header(progress_pct)

    # ── st.progress (Streamlit 기본 위젯) ──────────────────────
    st.markdown('<div class="sec-lbl">📅 오늘의 학습 세션</div>', unsafe_allow_html=True)
    st.progress(progress_pct / 100)
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── 스키밍 단계 카드 ────────────────────────────────────────
    skim_done   = ss.skimming_done
    skim_status = '<span class="pc-status done">완료 ✅</span>' if skim_done else '<span class="pc-status">시작 전</span>'
    time_html   = '<span class="pc-time">~3분</span>'
    prog_fill   = "100%" if skim_done else "0%"

    st.markdown(
        f"""
<div class="phase-card">
    {render_word_strip(words)}
    <div class="pc-body">
        <div class="pc-hd">
            <span class="pc-title">🔍 스키밍</span>
            <span class="pc-filter">≡</span>
        </div>
        <div class="pc-prog"><div class="pc-prog-fill" style="width:{prog_fill}"></div></div>
        <div class="pc-meta">{skim_status}{time_html}</div>
        <div class="pc-desc">모르는 단어 {UNKNOWN_TARGET}개를 골라주세요.</div>
    </div>
</div>""",
        unsafe_allow_html=True,
    )
    if not skim_done:
        if st.button("바로 시작", use_container_width=True, type="primary", key="go_skim"):
            db_reset_today()
            ss.all_words   = load_words()
            ss.skim_index  = 0
            ss.unknown_ids = []
            ss.skimming_done = False
            ss.page = "skimming"
            st.rerun()
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── 플래시카드 단계 카드 ────────────────────────────────────
    fc_locked = not skim_done
    fc_done   = ss.flashcard_done
    fc_status = (
        '<span class="pc-status done">완료 ✅</span>' if fc_done else
        '<span class="pc-status">🔒 스키밍 완료 후 시작</span>' if fc_locked else
        '<span class="pc-status">시작 전</span>'
    )
    fc_prog   = "100%" if fc_done else "0%"
    locked_cls = "locked" if fc_locked else ""

    st.markdown(
        f"""
<div class="phase-card {locked_cls}">
    {render_word_strip(words)}
    <div class="pc-body">
        <div class="pc-hd">
            <span class="pc-title">🃏 플래시카드</span>
        </div>
        <div class="pc-prog"><div class="pc-prog-fill" style="width:{fc_prog}"></div></div>
        <div class="pc-meta">{fc_status}</div>
        <div class="pc-desc">선택된 {UNKNOWN_TARGET}개 단어를 집중 암기합니다.</div>
    </div>
</div>""",
        unsafe_allow_html=True,
    )
    if not fc_locked and not fc_done:
        if st.button("바로 시작", use_container_width=True, key="go_fc"):
            ss.fc_index        = 0
            ss.fc_show_meaning = False
            ss.fc_cleared_ids  = []
            ss.page = "flashcard"
            st.rerun()
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── 퀴즈 단계 카드 ──────────────────────────────────────────
    q_locked = not fc_done
    q_done   = ss.quiz_done
    q_status = (
        '<span class="pc-status done">완료 ✅</span>' if q_done else
        '<span class="pc-status">🔒 플래시카드 완료 후 시작</span>' if q_locked else
        '<span class="pc-status">시작 전</span>'
    )
    q_prog   = "100%" if q_done else "0%"
    locked_cls2 = "locked" if q_locked else ""

    st.markdown(
        f"""
<div class="phase-card {locked_cls2}">
    {render_word_strip(words)}
    <div class="pc-body">
        <div class="pc-hd">
            <span class="pc-title">📝 퀴즈</span>
        </div>
        <div class="pc-prog"><div class="pc-prog-fill" style="width:{q_prog}"></div></div>
        <div class="pc-meta">{q_status}</div>
        <div class="pc-desc">실력을 확인하세요.</div>
    </div>
</div>""",
        unsafe_allow_html=True,
    )
    if not q_locked and not q_done:
        if st.button("바로 시작", use_container_width=True, key="go_quiz"):
            q = list(ss.unknown_ids)
            random.shuffle(q)
            ss.quiz_queue   = q
            ss.quiz_results = {}
            ss.quiz_answered = False
            ss.quiz_choices  = []
            ss.quiz_answer   = ""
            ss.page = "quiz"
            st.rerun()

    # ── 리셋 버튼 ───────────────────────────────────────────────
    if skim_done or fc_done or q_done:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("🔄 오늘 학습 처음부터 다시 시작", use_container_width=True, key="reset_all"):
            db_reset_today()
            reset_all_session()
            st.rerun()

    render_bottom_nav(ss.active_tab)


# ══════════════════════════════════════════════════════════════════
#  ⑨ PAGE: SKIMMING  (그리드 방식 전면 재설계)
# ══════════════════════════════════════════════════════════════════
def page_skimming() -> None:
    ss    = st.session_state
    words = ss.all_words

    # ── skim_states 초기화 (최초 진입 시)
    if not ss.skim_states:
        ss.skim_states = {w["word_id"]: "pending" for w in words}

    states = ss.skim_states

    # ── 상단 헤더
    c_back, c_title = st.columns([2, 7])
    with c_back:
        if st.button("← 홈", key="back_skim"):
            ss.page = "home"
            st.rerun()
    with c_title:
        st.markdown(
            '<div style="color:#f0f6fc;font-weight:700;font-size:1rem;padding-top:4px;">'
            '🔍 스키밍 — 알아요 / 몰라요로 분류하세요</div>',
            unsafe_allow_html=True,
        )

    # ── 상태 집계
    know_n    = sum(1 for v in states.values() if v == "know")
    unknown_n = sum(1 for v in states.values() if v == "unknown")
    pending_n = sum(1 for v in states.values() if v == "pending")
    total     = len(words)

    # ── 요약 바 (HTML)
    st.markdown(
        f"""
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
</div>""",
        unsafe_allow_html=True,
    )

    # ── 전체 진척도 바
    classified = know_n + unknown_n
    st.progress(classified / total if total else 0)
    st.markdown(
        f'<div style="color:#6e7681;font-size:.76rem;margin:6px 0 16px">'
        f'{classified} / {total} 분류 완료</div>',
        unsafe_allow_html=True,
    )

    # ══ 3열 그리드 렌더링 ══════════════════════════════════════════
    COLS_PER_ROW = 3
    for row_start in range(0, total, COLS_PER_ROW):
        grid_cols = st.columns(COLS_PER_ROW, gap="small")
        for col_idx in range(COLS_PER_ROW):
            word_idx = row_start + col_idx
            if word_idx >= total:
                break
            word     = words[word_idx]
            wid      = word["word_id"]
            state    = states.get(wid, "pending")
            emoji    = word.get("emoji", "📚")
            english  = word["english"]

            # 상태별 아이콘
            state_icon = {"know": "✅", "unknown": "📌", "pending": ""}.get(state, "")

            with grid_cols[col_idx]:
                # ── 단어 카드 (HTML)
                st.markdown(
                    f'<div class="sg-card {state}">'
                    f'<span class="sg-state-icon">{state_icon}</span>'
                    f'<span class="sg-emoji">{emoji}</span>'
                    f'<span class="sg-word">{english}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # ── 버튼 2개 (알아요 / 몰라요)
                btn_know_cls = "btn-know-active" if state == "know" else ""
                btn_unk_cls  = "btn-unk-active"  if state == "unknown" else ""

                b1, b2 = st.columns(2, gap="small")
                with b1:
                    st.markdown(f'<div class="{btn_know_cls}">', unsafe_allow_html=True)
                    if st.button("알아요", key=f"k_{wid}", use_container_width=True):
                        # 토글: 이미 know면 pending으로 되돌림
                        states[wid] = "pending" if state == "know" else "know"
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                with b2:
                    st.markdown(f'<div class="{btn_unk_cls}">', unsafe_allow_html=True)
                    if st.button("몰라요", key=f"u_{wid}", use_container_width=True):
                        # 토글: 이미 unknown이면 pending으로 되돌림
                        states[wid] = "pending" if state == "unknown" else "unknown"
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    # ══ 하단: 학습 시작 버튼 ══════════════════════════════════════
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    can_start = unknown_n > 0

    # 미분류가 있으면 안내 메시지
    if pending_n > 0:
        st.markdown(
            f'<div style="color:#6e7681;font-size:.80rem;text-align:center;margin-bottom:10px">'
            f'⚠️ 아직 <b style="color:#f0f6fc">{pending_n}개</b> 단어를 분류하지 않았어요. '
            f'미분류 단어는 <b style="color:#34d399">알아요</b>로 자동 처리됩니다.</div>',
            unsafe_allow_html=True,
        )

    if not can_start:
        st.markdown(
            '<div style="color:#6e7681;font-size:.80rem;text-align:center;margin-bottom:10px">'
            '✗ <b style="color:#60a5fa">몰라요</b> 단어를 1개 이상 선택해야 학습을 시작할 수 있어요.</div>',
            unsafe_allow_html=True,
        )

    btn_label = f"🚀  학습 시작 (몰라요 {unknown_n}개)"
    if st.button(btn_label, use_container_width=True, type="primary",
                 key="skim_start", disabled=not can_start):
        # ── 1. DB 업데이트
        for w in words:
            result = states.get(w["word_id"], "know")
            if result == "pending":
                result = "know"   # 미분류 → 알아요 처리
            db_set_skimming(w["word_id"], result)

        # ── 2. 오늘의 학습 리스트 = 몰라요 단어 ID만 저장
        ss.unknown_ids   = [
            wid for wid, st_val in states.items() if st_val == "unknown"
        ]
        # ── 3. 상태 업데이트
        ss.all_words     = load_words()
        ss.skimming_done = True
        ss.page          = "home"
        st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑩ PAGE: FLASHCARD  (새 UI: 이미지 플레이스홀더 + 뜻 토글 + 이전/다음)
# ══════════════════════════════════════════════════════════════════
def page_flashcard() -> None:
    ss       = st.session_state
    word_ids = ss.unknown_ids
    word_map = {w["word_id"]: w for w in ss.all_words}
    total    = len(word_ids)

    # ── 단어 없으면 완료 처리
    if total == 0:
        ss.flashcard_done = True
        ss.page = "home"; st.rerun(); return

    # ── 인덱스 범위 보정
    idx = min(ss.fc_index, total - 1)
    ss.fc_index = idx

    current_id   = word_ids[idx]
    word         = word_map.get(current_id)
    cleared_ids  = ss.fc_cleared_ids
    cleared_n    = len(cleared_ids)
    is_cleared   = current_id in cleared_ids

    if not word:
        ss.fc_index = (idx + 1) % total
        ss.fc_show_meaning = False
        st.rerun(); return

    # ── 품사별 스타일
    pos                          = word.get("part_of_speech", "명사")
    pos_css, glow_var, bg_grad   = _pos_style(pos)
    emoji                        = word.get("emoji", "📚")
    glow_color                   = glow_var.split(":", 1)[-1]  # rgba(...)

    # ══ 상단 헤더 ══════════════════════════════════════════════════
    h1, h2, h3 = st.columns([2, 4, 3])
    with h1:
        if st.button("← 홈", key="back_fc"):
            ss.page = "home"; st.rerun()
    with h2:
        st.markdown(
            '<div style="color:#f0f6fc;font-weight:700;font-size:1rem;padding-top:4px;">'
            '🃏 플래시카드</div>',
            unsafe_allow_html=True,
        )
    with h3:
        st.markdown(
            f'<div style="text-align:right">'
            f'<span class="badge">기억 {cleared_n}/{total}</span></div>',
            unsafe_allow_html=True,
        )

    # ── 진척도 바
    st.progress(cleared_n / total if total else 0)
    st.markdown(
        f'<div style="color:#6e7681;font-size:.76rem;margin:5px 0 14px">'
        f'{idx + 1} / {total}번째 카드'
        f'{" · ✅ 기억 완료" if is_cleared else ""}</div>',
        unsafe_allow_html=True,
    )

    # ══ 플래시카드 본체 ════════════════════════════════════════════
    st.markdown(
        f"""
<div class="fc-card">
  <!-- ① 이미지 플레이스홀더 -->
  <div class="fc-img" style="background:{bg_grad};{glow_var}">
    <div style="position:absolute;inset:0;
         background:radial-gradient(ellipse at 50% 40%,
         {glow_color} 0%, transparent 68%);
         pointer-events:none"></div>
    <span style="font-size:5.8rem;position:relative;z-index:1;
         filter:drop-shadow(0 0 22px {glow_color});">{emoji}</span>
    <span class="fc-img-label">📷 IMAGE PLACEHOLDER</span>
  </div>
  <!-- ② 단어 정보 -->
  <div class="fc-body">
    <div class="fc-word-row">
      <span class="fc-en">{word['english']}</span>
      <span class="fc-sound">🔊 발음</span>
    </div>
    <div class="fc-pos" style="{pos_css}">{pos}</div>""",
        unsafe_allow_html=True,
    )

    # ── 뜻 토글 영역 (session_state로 제어)
    if ss.fc_show_meaning:
        st.markdown(
            f"""
    <div class="fc-meaning">
      <div class="fc-ko">{word['korean']}</div>
      <div class="fc-example">
        {word['example_en']}
        <span class="fc-ex-ko">{word['example_ko']}</span>
      </div>
    </div>""",
            unsafe_allow_html=True,
        )

    # 카드 닫기 태그
    st.markdown("  </div>\n</div>", unsafe_allow_html=True)

    # ══ 뜻 보기 / 숨기기 버튼 ════════════════════════════════════
    if not ss.fc_show_meaning:
        if st.button("👁  뜻 보기", use_container_width=True, key="fc_show"):
            ss.fc_show_meaning = True; st.rerun()
    else:
        if st.button("🙈  뜻 숨기기", use_container_width=True, key="fc_hide"):
            ss.fc_show_meaning = False; st.rerun()

        # 기억했어요 / 다시보기 (뜻이 보일 때만 활성)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            if st.button("🔄  다시보기", use_container_width=True, key="fc_retry"):
                db_set_flashcard(current_id, False)
                if current_id in cleared_ids:
                    cleared_ids.remove(current_id)
                ss.fc_show_meaning = False
                st.rerun()
        with g2:
            clear_cls = "btn-clear-active" if is_cleared else ""
            st.markdown(f'<div class="{clear_cls}">', unsafe_allow_html=True)
            if st.button("✅  기억했어요!", use_container_width=True,
                         type="primary" if not is_cleared else "secondary",
                         key="fc_clear"):
                db_set_flashcard(current_id, True)
                if current_id not in cleared_ids:
                    cleared_ids.append(current_id)
                ss.fc_show_meaning = False
                # 자동으로 다음 카드로
                ss.fc_index = (idx + 1) % total
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ══ 점 인디케이터 + 이전/다음 네비게이션 ══════════════════════
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # 점 인디케이터 (최대 7개 표시)
    MAX_DOTS = 7
    dots_html = '<div class="fc-dots">'
    if total <= MAX_DOTS:
        for i in range(total):
            wid_i  = word_ids[i]
            cls    = "active" if i == idx else ("cleared" if wid_i in cleared_ids else "")
            dots_html += f'<div class="fc-dot {cls}"></div>'
    else:
        # 현재 인덱스 주변 점만 표시
        half  = MAX_DOTS // 2
        start = max(0, min(idx - half, total - MAX_DOTS))
        for i in range(start, start + MAX_DOTS):
            wid_i = word_ids[i]
            cls   = "active" if i == idx else ("cleared" if wid_i in cleared_ids else "")
            dots_html += f'<div class="fc-dot {cls}"></div>'
    dots_html += '</div>'
    st.markdown(dots_html, unsafe_allow_html=True)

    # 이전 / 다음 버튼
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("← 이전 단어", use_container_width=True, key="fc_prev",
                     disabled=(idx == 0)):
            ss.fc_index = idx - 1
            ss.fc_show_meaning = False
            st.rerun()
    with nav2:
        if st.button("다음 단어 →", use_container_width=True, key="fc_next",
                     disabled=(idx >= total - 1)):
            ss.fc_index = idx + 1
            ss.fc_show_meaning = False
            st.rerun()

    # ══ 전체 완료 배너 ════════════════════════════════════════════
    if cleared_n >= total:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("""
<div style="background:linear-gradient(135deg,rgba(52,211,153,.10),rgba(59,130,246,.07));
            border:1px solid rgba(52,211,153,.3);
            border-radius:20px;padding:22px;text-align:center;">
  <div style="font-size:2.5rem;margin-bottom:8px">🎉</div>
  <div style="color:#34d399;font-size:1.1rem;font-weight:800">모든 단어를 기억했어요!</div>
  <div style="color:#6e7681;font-size:.82rem;margin-top:6px">퀴즈로 최종 실력을 확인하세요.</div>
</div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("🏠  홈으로 → 퀴즈 시작", use_container_width=True,
                     type="primary", key="fc_done"):
            ss.flashcard_done = True
            ss.page = "home"; st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑪ PAGE: QUIZ  (개선된 피드백 + 선택지 색상 + 오답 DB 저장)
# ══════════════════════════════════════════════════════════════════
NUMS = ["①", "②", "③", "④"]


def _build_choices(word: dict, all_words: list[dict]) -> tuple[list[str], str]:
    """4지선다 보기 배포: 정답 1 + DB 무작위 오답 3"""
    answer = word["korean"]
    # 정답이 아닌 다른 단어들의 의미만 추릴 (중복 제거)
    pool = [
        w["korean"] for w in all_words
        if w["word_id"] != word["word_id"] and w["korean"] != answer
    ]
    distractors = random.sample(pool, min(3, len(pool)))
    choices = distractors + [answer]
    random.shuffle(choices)
    return choices, answer


def page_quiz() -> None:
    ss       = st.session_state
    queue    = ss.quiz_queue
    word_map = {w["word_id"]: w for w in ss.all_words}
    total    = len(ss.unknown_ids)
    done_n   = len(ss.quiz_results)

    # ── 상단 헤더
    h1, h2, h3 = st.columns([2, 4, 3])
    with h1:
        if st.button("← 홈", key="back_quiz"):
            ss.page = "home"; st.rerun()
    with h2:
        st.markdown(
            '<div style="color:#f0f6fc;font-weight:700;font-size:1rem;padding-top:4px;">'
            '📝 퀴즈</div>',
            unsafe_allow_html=True,
        )
    with h3:
        correct_n = sum(1 for v in ss.quiz_results.values() if v)
        st.markdown(
            f'<div style="text-align:right">'
            f'<span class="badge">{done_n}/{total}</span></div>',
            unsafe_allow_html=True,
        )

    # ══ 퀴즈 완료 화면 ════════════════════════════════════════
    if not queue:
        ss.quiz_done = True
        results  = ss.quiz_results
        correct  = sum(1 for v in results.values() if v)
        wrong    = total - correct
        pct      = int(correct / total * 100) if total else 0

        # ─ 성장 애니메이션 이모지
        trophy = "🏆" if pct == 100 else ("🌟" if pct >= 80 else ("💪" if pct >= 60 else "📚"))

        st.markdown(f"""
<div class="result-hero">
    <div style="font-size:3rem;margin-bottom:10px">{trophy}</div>
    <div style="color:#34d399;font-size:1.45rem;font-weight:900">Day {STUDY_DAY} 완료!</div>
    <div style="color:#6e7681;font-size:.82rem;margin-top:6px">오늘의 모든 학습을 마쳤습니다</div>
</div>""", unsafe_allow_html=True)

        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(
                f'<div class="stat-card"><div class="sc-lbl">✅ 정답</div>'
                f'<div class="sc-val c-green">{correct}</div></div>', unsafe_allow_html=True)
        with r2:
            st.markdown(
                f'<div class="stat-card"><div class="sc-lbl">❌ 오답</div>'
                f'<div class="sc-val c-red">{wrong}</div></div>', unsafe_allow_html=True)
        with r3:
            st.markdown(
                f'<div class="stat-card"><div class="sc-lbl">🎯 성취도</div>'
                f'<div class="sc-val c-blue">{pct}%</div></div>', unsafe_allow_html=True)

        # 오답 단어 상세 보기
        if wrong > 0:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown(
                '<div class="sec-lbl">📕 오답 노트 — 틀린 단어</div>',
                unsafe_allow_html=True,
            )
            for wid, passed in results.items():
                if not passed:
                    w = word_map.get(wid)
                    if w:
                        pos_css, _, _ = _pos_style(w["part_of_speech"])
                        st.markdown(
                            f'<div class="wn-card">'
                            f'<span class="wn-emoji">{w["emoji"]}</span>'
                            f'<div class="wn-info">'
                            f'<div class="wn-en">{w["english"]}</div>'
                            f'<div class="wn-ko">{w["korean"]}</div>'
                            f'<div class="wn-pos" style="{pos_css}">{w["part_of_speech"]}</div>'
                            f'</div>'
                            f'<span class="wn-wrong-badge">오답 ✖</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
            st.markdown(
                '<div style="color:#6e7681;font-size:.76rem;text-align:center;margin-top:8px">'
                '📌 오답 횟수는 DB에 저장되었습니다. 라이브러리 → 오답 노트에서 확인할 수 있어요.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("🏠  홈으로 돌아가기", use_container_width=True,
                     type="primary", key="q_home"):
            ss.page = "home"; st.rerun()
        return

    # ══ 진행 바 ══════════════════════════════════════════════
    st.progress(done_n / total if total else 0)
    st.markdown(
        f'<div style="color:#6e7681;font-size:.76rem;margin:5px 0 16px">'
        f'{done_n + 1} / {total} 문제</div>',
        unsafe_allow_html=True,
    )

    current_id = queue[0]
    word       = word_map.get(current_id)
    if not word:
        ss.quiz_queue.pop(0); st.rerun(); return

    # 선택지 생성 (미답변 시)
    if not ss.quiz_choices:
        choices, answer  = _build_choices(word, ss.all_words)
        ss.quiz_choices  = choices
        ss.quiz_answer   = answer
        ss.quiz_answered = False
        ss.quiz_correct  = False

    # ── 문제 카드
    pos_css, glow_var, bg_grad = _pos_style(word["part_of_speech"])
    emoji = word.get("emoji", "📚")
    glow_color = glow_var.split(":", 1)[-1]

    st.markdown(f"""
<div class="fc-card" style="margin-bottom:14px">
  <div class="fc-img" style="background:{bg_grad};{glow_var};height:140px">
    <div style="position:absolute;inset:0;
         background:radial-gradient(ellipse at 50% 40%,{glow_color} 0%,transparent 65%);
         pointer-events:none"></div>
    <span style="font-size:4.5rem;position:relative;z-index:1;
         filter:drop-shadow(0 0 18px {glow_color});">{emoji}</span>
  </div>
  <div class="fc-body">
    <div class="qq-label">Q{done_n + 1}. 다음 영단어의 뜻은?</div>
    <div class="fc-en" style="margin-bottom:4px">{word['english']}</div>
    <div class="fc-pos" style="{pos_css}">{word['part_of_speech']}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── 선택지 버튼
    if not ss.quiz_answered:
        for i, choice in enumerate(ss.quiz_choices):
            if st.button(
                f"{NUMS[i]}  {choice}",
                use_container_width=True,
                key=f"qc_{i}",
            ):
                ok = (choice == ss.quiz_answer)
                ss.quiz_correct   = ok
                ss.quiz_answered  = True
                ss.quiz_selected  = choice        # 사용자가 선택한 보기 저장
                db_set_quiz(current_id, ok)       # DB: 오답이면 wrong_count +1
                ss.quiz_results[current_id] = ok
                st.rerun()
    else:
        # ── 선택지별 색상 피드백
        for i, choice in enumerate(ss.quiz_choices):
            is_answer   = (choice == ss.quiz_answer)
            is_selected = (choice == ss.get("quiz_selected", ""))

            if is_answer:
                css_cls = "qbtn-correct"               # 정답: 초록
            elif is_selected and not ss.quiz_correct:
                css_cls = "qbtn-wrong"                 # 내가 고른 오답: 빨강
            else:
                css_cls = "qbtn-dim"                   # 나머지: 흐리게

            st.markdown(f'<div class="{css_cls}">', unsafe_allow_html=True)
            st.button(
                f"{NUMS[i]}  {choice}",
                use_container_width=True,
                key=f"qca_{i}",
                disabled=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # ── 피드백 배너
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if ss.quiz_correct:
            st.markdown("""
<div style="background:rgba(52,211,153,.10);border:1.5px solid rgba(52,211,153,.4);
            border-radius:16px;padding:14px 18px;display:flex;align-items:center;gap:12px">
  <span style="font-size:1.8rem">✅</span>
  <div>
    <div style="color:#34d399;font-weight:800;font-size:.95rem">정답입니다! 🎉</div>
    <div style="color:#6e7681;font-size:.78rem;margin-top:2px">오늘도 낙승!</div>
  </div>
</div>""", unsafe_allow_html=True)
        else:
            correct_word = ss.quiz_answer
            st.markdown(f"""
<div style="background:rgba(248,81,73,.10);border:1.5px solid rgba(248,81,73,.35);
            border-radius:16px;padding:14px 18px;display:flex;align-items:center;gap:12px">
  <span style="font-size:1.8rem">❌</span>
  <div>
    <div style="color:#f85149;font-weight:800;font-size:.95rem">오답입니다.</div>
    <div style="color:#e6edf3;font-size:.84rem;margin-top:4px">
      정답은 &nbsp;<b style="color:#34d399">"{correct_word}"</b>&nbsp; 입니다.
    </div>
    <div style="color:#6e7681;font-size:.74rem;margin-top:3px">
      오답 데이터가 DB에 저장되었습니다.
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("다음 문제 →", use_container_width=True,
                     type="primary", key="next_q"):
            ss.quiz_queue.pop(0)
            ss.quiz_answered = False
            ss.quiz_choices  = []
            ss.quiz_answer   = ""
            ss.quiz_correct  = False
            ss["quiz_selected"] = ""
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑫ PAGE: LIBRARY  (오답 노트 탭 포함)
# ══════════════════════════════════════════════════════════════════
def page_library() -> None:
    ss = st.session_state
    progress_pct = calc_progress_pct()
    render_top_header(progress_pct)

    # ── 라이브러리 서브탭 (query param 방식)
    lib_tab = st.query_params.get("lib", "wrong")

    # 서브탭 네비게이션 HTML
    tabs_html = (
        f'<div class="lib-tabs">'
        f'<a class="lib-tab {"active" if lib_tab == "wrong" else ""}" href="?nav=library&lib=wrong">'
        f'📕 오답 노트</a>'
        f'<a class="lib-tab {"active" if lib_tab == "all" else ""}" href="?nav=library&lib=all">'
        f'📚 전체 단어장</a>'
        f'</div>'
    )
    st.markdown(tabs_html, unsafe_allow_html=True)

    # ── ❌ 오답 노트 탭
    if lib_tab != "all":
        wrong_words = load_wrong_words()
        total_wrong = len(wrong_words)

        # 요약 헤더
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;margin-bottom:14px;">'
            f'<div style="color:#f0f6fc;font-weight:700;font-size:1rem">오답 노트</div>'
            f'<span class="badge">총 {total_wrong}개</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if total_wrong == 0:
            st.markdown("""
<div class="wn-empty">
    <div class="wn-empty-icon">🎉</div>
    <div style="color:#e6edf3;font-weight:700;margin-bottom:6px">오답이 없어요!</div>
    <div>퀴즈에서 틀린 단어가 없습니다. 훌륭합니다! 🚀</div>
</div>""", unsafe_allow_html=True)
        else:
            # 오답 횟수 시각화 바
            max_wrong = max(w["wrong_count"] for w in wrong_words) if wrong_words else 1

            for w in wrong_words:
                cnt = w["wrong_count"]
                bar_w = int(cnt / max_wrong * 100)
                pos_css, _, _ = _pos_style(w["part_of_speech"])
                is_retry = w["study_status"] == "needs_retry"

                st.markdown(
                    f'<div class="wn-card">'
                    f'<span class="wn-emoji">{w["emoji"]}</span>'
                    f'<div class="wn-info">'
                    f'<div class="wn-en">{w["english"]}</div>'
                    f'<div class="wn-ko">{w["korean"]}</div>'
                    f'<div class="wn-pos" style="{pos_css}">{w["part_of_speech"]}</div>'
                    f'<div style="margin-top:6px;height:3px;background:rgba(255,255,255,.08);'
                    f'border-radius:3px;overflow:hidden">'
                    f'<div style="width:{bar_w}%;height:100%;'
                    f'background:linear-gradient(90deg,#f85149,#fca5a5);'
                    f'border-radius:3px;"></div></div>'
                    f'</div>'
                    f'<div style="text-align:right;flex-shrink:0">'
                    f'<span class="wn-wrong-badge">❌ {cnt}회</span>'
                    f'{"<br><span style=\"color:#6e7681;font-size:.62rem;margin-top:4px;display:block\">재도전 필요</span>" if is_retry else ""}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div style="color:#6e7681;font-size:.74rem;text-align:center;'
                f'margin-top:12px;padding:10px;">'
                f'📌 오답 횟수는 퀴즈를 틀릴 때마다 자동으로 +1 증가합니다.</div>',
                unsafe_allow_html=True,
            )

    # ── 전체 단어장 탭
    else:
        all_w = ss.all_words if ss.all_words else load_words()
        st.markdown(
            f'<div style="color:#f0f6fc;font-weight:700;margin-bottom:14px">전체 단어장 ({len(all_w)}개)</div>',
            unsafe_allow_html=True,
        )
        for w in all_w:
            status_icon = {
                "completed":   "✅",
                "know":        "✓ ",
                "unknown":     "✗ ",
                "needs_retry": "🔄",
                "reviewing":   "📕",
            }.get(w.get("study_status", ""), "○")
            pos_css, _, _ = _pos_style(w["part_of_speech"])

            st.markdown(
                f'<div class="wn-card">'
                f'<span class="wn-emoji">{w["emoji"]}</span>'
                f'<div class="wn-info">'
                f'<div class="wn-en">{w["english"]}</div>'
                f'<div class="wn-ko">{w["korean"]}</div>'
                f'<div class="wn-pos" style="{pos_css}">{w["part_of_speech"]}</div>'
                f'</div>'
                f'<span style="font-size:1.1rem">{status_icon}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    render_bottom_nav("library")


# ══════════════════════════════════════════════════════════════════
#  ⑬ PAGE: STATS (플레이스홀더)
# ══════════════════════════════════════════════════════════════════
def page_stats() -> None:
    progress_pct = calc_progress_pct()
    render_top_header(progress_pct)
    
    stats = get_stats_data()
    
    st.markdown("""
<style>
.stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}
.stats-card-box {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.stats-card-val {
    font-size: 1.8rem;
    font-weight: 900;
    margin-bottom: 4px;
}
.stats-card-lbl {
    font-size: 0.72rem;
    color: #8b949e;
    font-weight: 700;
    text-transform: uppercase;
}
.stats-header-title {
    color: #f0f6fc;
    font-weight: 800;
    font-size: 1.15rem;
    margin: 22px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.top-wrong-list {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 18px;
    padding: 16px;
}
.top-wrong-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.top-wrong-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
}
.top-wrong-item:first-child {
    padding-top: 0;
}
.twi-word {
    font-size: 1rem;
    font-weight: 800;
    color: #f85149;
}
.twi-meaning {
    font-size: 0.8rem;
    color: #8b949e;
    margin-left: 10px;
}
.twi-count {
    background: rgba(248,81,73,0.1);
    color: #f85149;
    border: 1px solid rgba(248,81,73,0.2);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-weight: 700;
}
</style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="stats-header-title">📊 전체 학습 통계</div>', unsafe_allow_html=True)
    
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
        <div class="stats-card-lbl">학습 전 단어</div>
    </div>
    <div class="stats-card-box">
        <div class="stats-card-val c-red">{stats['wrong_total']}</div>
        <div class="stats-card-lbl">누적 오답 수</div>
    </div>
</div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="stats-header-title">🔥 취약 단어 Top 3</div>', unsafe_allow_html=True)
    
    if not stats['top_wrong']:
        st.markdown("""
<div class="wn-empty" style="padding: 30px;">
    <div class="wn-empty-icon">✨</div>
    <div style="color:#e6edf3;font-weight:700;">취약 단어가 없습니다.</div>
    <div style="font-size: 0.8rem; margin-top:4px;">퀴즈를 진행하여 학습을 기록해 보세요!</div>
</div>
        """, unsafe_allow_html=True)
    else:
        items_html = ""
        for w in stats['top_wrong']:
            items_html += f"""
            <div class="top-wrong-item">
                <div>
                    <span class="twi-word">{w['english']}</span>
                    <span class="twi-meaning">{w['korean']}</span>
                </div>
                <span class="twi-count">❌ {w['wrong_count']}회</span>
            </div>
            """
        st.markdown(f'<div class="top-wrong-list">{items_html}</div>', unsafe_allow_html=True)
        
    render_bottom_nav("stats")



# ══════════════════════════════════════════════════════════════════
#  ⑭ MAIN ROUTER
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    init_db()
    inject_css()
    init_session()

    ss = st.session_state

    # 단어 목록 최초 로드
    if not ss.all_words:
        ss.all_words = load_words()

    # ── 하단 네비게이션 쿼리 파라미터 처리 ──────────────────────
    nav_param = st.query_params.get("nav", "")
    if nav_param in ("library", "stats", "member") and ss.page not in ("skimming", "flashcard", "quiz"):
        ss.active_tab = nav_param
        ss.page       = nav_param
        # 쿼리 파라미터 초기화 (무한 루프 방지)
        st.query_params.clear()
        st.rerun()
    elif nav_param == "home" and ss.page not in ("skimming", "flashcard", "quiz"):
        ss.active_tab = "home"
        ss.page       = "home"
        st.query_params.clear()
        st.rerun()

    # ── 페이지 라우팅 ────────────────────────────────────────────
    page = ss.page
    if page == "home":
        page_home()
    elif page == "skimming":
        page_skimming()
    elif page == "flashcard":
        page_flashcard()
    elif page == "quiz":
        page_quiz()
    elif page == "library":
        page_library()
    elif page == "stats":
        page_stats()
    else:
        ss.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()

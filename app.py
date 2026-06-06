"""
🚀 ANTIGRAVITY — 망각의 중력을 거스르는 수능 영단어 앱
=======================================================
기술 스택 : Python 3.10+ · Streamlit · SQLite3
실행 방법 : streamlit run app.py
"""

import sqlite3
import random
from datetime import date
from pathlib import Path

import streamlit as st

# ══════════════════════════════════════════════════════════════════
#  ① PAGE CONFIG  (반드시 첫 번째 st 호출)
# ══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="🚀 Antigravity — 수능 영단어",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════
#  ② CONSTANTS
# ══════════════════════════════════════════════════════════════════
DB_PATH         = Path(__file__).parent / "antigravity.db"
SUNEUNG_DATE    = date(2027, 11, 18)   # 수능 목표일 (예시)
STUDY_START     = date(2026, 1, 10)    # 학습 시작일 (예시)
TODAY           = date.today()
D_DAY           = max(0, (SUNEUNG_DATE - TODAY).days)
STUDY_DAY       = max(1, (TODAY - STUDY_START).days + 1)
UNKNOWN_TARGET  = 5    # 스키밍에서 고를 '모르는 단어' 수 (15개 세트 기준)

# ══════════════════════════════════════════════════════════════════
#  ③ SEED DATA — 수능 필수 영단어 15개
# ══════════════════════════════════════════════════════════════════
SEED_WORDS = [
    # (english, korean, part_of_speech, example_en, example_ko, importance, emoji)
    ("pure",        "순수한, 순결한",              "형용사", "Her motives were pure and honest.",            "그녀의 동기는 순수하고 정직했다.",           2, "✨"),
    ("preclude",    "방해하다, 불가능하게 하다",    "동사",   "His injury precluded him from running.",       "부상이 그의 달리기를 불가능하게 했다.",      1, "⛔"),
    ("ambiguous",   "모호한, 불분명한",            "형용사", "The statement was ambiguous.",                 "그 진술은 모호했다.",                        2, "🌫️"),
    ("phenomenon",  "현상",                       "명사",   "Global warming is a worldwide phenomenon.",    "지구 온난화는 전 세계적인 현상이다.",        1, "🌍"),
    ("persist",     "지속하다, 고집하다",           "동사",   "The problem continues to persist.",            "그 문제는 계속 지속된다.",                   2, "🔄"),
    ("subsequent",  "그 다음의, 뒤이은",           "형용사", "Subsequent events proved him right.",          "그 다음 사건들이 그가 옳음을 증명했다.",     2, "⏩"),
    ("inevitable",  "불가피한, 필연적인",          "형용사", "Change is inevitable in life.",                "삶에서 변화는 불가피하다.",                  1, "⚡"),
    ("comprehend",  "이해하다, 파악하다",           "동사",   "I could not comprehend the instructions.",     "나는 지시를 이해할 수 없었다.",              2, "💡"),
    ("diminish",    "줄어들다, 감소시키다",         "동사",   "The pain began to diminish slowly.",           "통증이 천천히 줄어들기 시작했다.",           2, "📉"),
    ("elaborate",   "정교한; 상세히 설명하다",      "형용사", "She elaborated on her detailed plan.",         "그녀는 계획을 상세히 설명했다.",             3, "🔬"),
    ("facilitate",  "용이하게 하다, 촉진하다",      "동사",   "Technology facilitates communication.",        "기술은 소통을 용이하게 한다.",               1, "🚀"),
    ("impede",      "방해하다, 저해하다",           "동사",   "Lack of funds impeded the project.",           "자금 부족이 프로젝트를 저해했다.",           2, "🚧"),
    ("manifest",    "나타내다; 명백한",            "동사",   "Symptoms may manifest differently.",           "증상은 다르게 나타날 수 있다.",              2, "🌟"),
    ("obscure",     "불분명한; 가리다",            "형용사", "The meaning of the poem was obscure.",         "시의 의미가 불분명했다.",                    3, "🌑"),
    ("profound",    "깊은, 심오한",               "형용사", "He had a profound impact on science.",         "그는 과학에 심오한 영향을 미쳤다.",          1, "🌊"),
]

# ══════════════════════════════════════════════════════════════════
#  ④ DATABASE LAYER
# ══════════════════════════════════════════════════════════════════
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """최초 실행 시 테이블 생성 + 씨드 데이터 삽입"""
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

        # 씨드 데이터 삽입 (중복 무시)
        for w in SEED_WORDS:
            conn.execute(
                "INSERT OR IGNORE INTO words "
                "(english, korean, part_of_speech, example_en, example_ko, importance, emoji, day_number) "
                "VALUES (?,?,?,?,?,?,?,1)",
                (w[0], w[1], w[2], w[3], w[4], w[5], w[6]),
            )
        # 진행 레코드가 없는 단어에 초기 레코드 생성
        conn.execute("""
            INSERT OR IGNORE INTO user_progress (word_id)
            SELECT word_id FROM words
            WHERE word_id NOT IN (SELECT word_id FROM user_progress)
        """)


def load_words() -> list[dict]:
    """오늘 학습 Day의 모든 단어 + 진행 상태 조회"""
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
            "SELECT COUNT(*) FROM user_progress WHERE study_status = 'completed'"
        ).fetchone()[0]
    return (done / total * 100) if total else 0.0


def db_set_skimming(word_id: int, result: str) -> None:
    status = "know" if result == "know" else "unknown"
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET skimming_result=?, study_status=? WHERE word_id=?",
            (result, status, word_id),
        )


def db_set_flashcard(word_id: int, cleared: bool) -> None:
    status = "reviewing" if cleared else "unknown"
    with get_conn() as conn:
        conn.execute(
            "UPDATE user_progress SET flashcard_cleared=?, study_status=? WHERE word_id=?",
            (1 if cleared else 0, status, word_id),
        )


def db_set_quiz(word_id: int, passed: bool) -> None:
    if passed:
        with get_conn() as conn:
            conn.execute(
                "UPDATE user_progress SET quiz_passed=1, study_status='completed' WHERE word_id=?",
                (word_id,),
            )
    else:
        with get_conn() as conn:
            conn.execute(
                "UPDATE user_progress SET wrong_count=wrong_count+1, study_status='needs_retry' WHERE word_id=?",
                (word_id,),
            )


def db_reset_today() -> None:
    with get_conn() as conn:
        conn.execute("""
            UPDATE user_progress
            SET study_status='unseen', skimming_result='pending',
                flashcard_cleared=0, quiz_passed=0, wrong_count=0
            WHERE word_id IN (SELECT word_id FROM words WHERE day_number=1)
        """)


# ══════════════════════════════════════════════════════════════════
#  ⑤ SESSION STATE 초기화
# ══════════════════════════════════════════════════════════════════
def init_session() -> None:
    defaults: dict = {
        "page":                   "home",   # 'home' | 'skimming' | 'flashcard' | 'quiz'
        "all_words":              [],       # DB에서 로드한 단어 목록
        # 스키밍
        "skim_index":             0,        # 현재 보고 있는 카드 인덱스
        "unknown_ids":            [],       # 모르는 단어 word_id 리스트
        "skimming_done":          False,
        # 플래시카드
        "fc_queue":               [],       # 처리할 카드 큐
        "fc_flipped":             False,    # 현재 카드 뒤집힘 여부
        "flashcard_done":         False,
        # 퀴즈
        "quiz_queue":             [],       # 퀴즈 출제 순서
        "quiz_results":           {},       # {word_id: True/False}
        "quiz_answered":          False,    # 현재 문제 답변 여부
        "quiz_correct":           False,
        "quiz_choices":           [],       # 현재 문제 선택지
        "quiz_answer":            "",       # 현재 문제 정답
        "quiz_done":              False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_all_session() -> None:
    """오늘 학습 전체 리셋"""
    keys_to_clear = [
        "skim_index", "unknown_ids", "skimming_done",
        "fc_queue", "fc_flipped", "flashcard_done",
        "quiz_queue", "quiz_results", "quiz_answered",
        "quiz_correct", "quiz_choices", "quiz_answer", "quiz_done",
    ]
    for k in keys_to_clear:
        if isinstance(st.session_state.get(k), list):
            st.session_state[k] = []
        elif isinstance(st.session_state.get(k), dict):
            st.session_state[k] = {}
        elif isinstance(st.session_state.get(k), bool):
            st.session_state[k] = False
        elif isinstance(st.session_state.get(k), int):
            st.session_state[k] = 0
        else:
            st.session_state[k] = ""
    st.session_state.all_words = load_words()


# ══════════════════════════════════════════════════════════════════
#  ⑥ GLOBAL CSS
# ══════════════════════════════════════════════════════════════════
def inject_css() -> None:
    st.markdown(
        """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');

/* ── 전역 기본값 ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans KR', sans-serif;
}
.stApp {
    background: linear-gradient(160deg, #060b18 0%, #0d1527 55%, #060b18 100%);
    min-height: 100vh;
}
.block-container {
    padding-top: 1.5rem !important;
    max-width: 480px !important;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── 대시보드 카드 ── */
.dash-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 18px;
    padding: 14px 12px;
    text-align: center;
    backdrop-filter: blur(12px);
}
.dash-label {
    color: #64748b;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 5px;
}
.dash-val      { color: #fff;     font-size: 1.65rem; font-weight: 900; line-height: 1.1; }
.c-blue        { color: #60a5fa !important; }
.c-green       { color: #34d399 !important; }
.c-purple      { color: #a78bfa !important; }
.c-red         { color: #f87171 !important; }

/* ── 앱 타이틀 ── */
.app-brand {
    display: flex; flex-direction: column;
    margin-bottom: 20px;
}
.app-title {
    color: #fff;
    font-size: 1.4rem;
    font-weight: 900;
    letter-spacing: 0.18em;
    text-transform: uppercase;
}
.app-sub {
    color: #4f6fa8;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    margin-top: 2px;
}

/* ── 단어 카드 ── */
.word-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 26px;
    overflow: hidden;
    max-width: 440px;
    margin: 0 auto;
    box-shadow: 0 24px 64px rgba(0,0,0,0.55);
}
.wc-image {
    width: 100%;
    height: 190px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 5rem;
    position: relative;
    overflow: hidden;
}
.wc-body { padding: 22px 24px 20px; }
.wc-en   { color: #fff;    font-size: 2rem;  font-weight: 900; letter-spacing: -0.02em; }
.wc-pos  { color: #60a5fa; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; margin: 5px 0 10px; }
.wc-ko   { color: #e2e8f0; font-size: 1.2rem; font-weight: 600; }
.wc-ex   {
    margin-top: 14px;
    padding: 10px 14px;
    background: rgba(96,165,250,0.07);
    border-left: 3px solid #3b82f6;
    border-radius: 0 10px 10px 0;
    color: #94a3b8;
    font-size: 0.82rem;
    line-height: 1.7;
}
.wc-ex-ko { color: #60a5fa; font-size: 0.78rem; }

/* ── 단계 카드 (홈) ── */
.phase-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px;
    padding: 18px 20px;
    margin-bottom: 14px;
    transition: border-color 0.25s;
}
.phase-card:hover { border-color: rgba(96,165,250,0.35); }
.phase-locked { opacity: 0.42; pointer-events: none; }
.phase-hd {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.phase-name { color: #fff; font-size: 1.05rem; font-weight: 700; }
.phase-time { color: #60a5fa; font-size: 0.78rem; font-weight: 600; }
.phase-desc { color: #64748b; font-size: 0.80rem; line-height: 1.5; }
.phase-stat { color: #475569; font-size: 0.76rem; margin-top: 8px; }
.phase-done { color: #34d399 !important; }

/* ── 배지 ── */
.badge {
    display: inline-block;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: #fff;
    border-radius: 50px;
    padding: 5px 15px;
    font-weight: 700;
    font-size: 0.85rem;
    margin-bottom: 14px;
}

/* ── 섹션 레이블 ── */
.sec-label {
    color: #475569;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* ── 결과 카드 ── */
.result-hero {
    background: linear-gradient(135deg, rgba(52,211,153,0.10), rgba(96,165,250,0.07));
    border: 1px solid rgba(52,211,153,0.25);
    border-radius: 24px;
    padding: 28px 20px;
    text-align: center;
    margin-bottom: 20px;
}
.result-icon   { font-size: 3.5rem; margin-bottom: 10px; }
.result-title  { color: #34d399; font-size: 1.5rem; font-weight: 900; }
.result-sub    { color: #64748b; font-size: 0.82rem; margin-top: 6px; }

/* ── 오답 항목 ── */
.wrong-item {
    background: rgba(248,113,113,0.08);
    border: 1px solid rgba(248,113,113,0.18);
    border-radius: 12px;
    padding: 11px 16px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.wi-en { color: #f87171; font-weight: 700; }
.wi-ko { color: #94a3b8; font-size: 0.82rem; }

/* ── Streamlit 기본 요소 오버라이드 ── */
.stProgress > div > div {
    background: linear-gradient(90deg, #3b82f6, #8b5cf6) !important;
    border-radius: 8px !important;
}
.stProgress > div {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    height: 6px !important;
}
.stButton > button {
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 0.93rem !important;
    padding: 0.55rem 1rem !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    background: rgba(255,255,255,0.06) !important;
    color: #e2e8f0 !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: rgba(255,255,255,0.11) !important;
    border-color: rgba(96,165,250,0.5) !important;
    color: #fff !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3b82f6, #6d28d9) !important;
    border-color: transparent !important;
    color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb, #5b21b6) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(59,130,246,0.35) !important;
}
.stButton > button:disabled {
    opacity: 0.35 !important;
}
div[data-testid="stMarkdownContainer"] p { color: #e2e8f0; }
hr { border-color: rgba(255,255,255,0.07) !important; margin: 18px 0 !important; }
</style>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════
#  ⑦ 공통 UI 컴포넌트
# ══════════════════════════════════════════════════════════════════
# 품사별 그라디언트 색상 매핑
GRADIENT_MAP = {
    "형용사": "linear-gradient(135deg,#1e3a5f 0%,#1a1040 100%)",
    "동사":   "linear-gradient(135deg,#1a2e1a 0%,#0f2020 100%)",
    "명사":   "linear-gradient(135deg,#2e1a3a 0%,#1a0f2e 100%)",
    "부사":   "linear-gradient(135deg,#2e2a1a 0%,#1a1810 100%)",
}
GLOW_MAP = {
    "형용사": "rgba(96,165,250,0.20)",
    "동사":   "rgba(52,211,153,0.20)",
    "명사":   "rgba(167,139,250,0.20)",
    "부사":   "rgba(251,191,36,0.20)",
}


def render_dashboard(progress_pct: float) -> None:
    st.markdown(
        '<div class="app-brand">'
        '<span class="app-title">🚀 Antigravity</span>'
        '<span class="app-sub">망각의 중력을 거스르다</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="dash-card"><div class="dash-label">수능까지</div>'
            f'<div class="dash-val c-blue">D-{D_DAY}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="dash-card"><div class="dash-label">진척도</div>'
            f'<div class="dash-val c-green">{progress_pct:.1f}%</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="dash-card"><div class="dash-label">오늘</div>'
            f'<div class="dash-val c-purple">Day {STUDY_DAY}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)


def render_word_card(word: dict, show_back: bool = False) -> None:
    """단어 카드 렌더링 (앞면 / 뒷면 공용)"""
    pos   = word.get("part_of_speech", "명사")
    grad  = GRADIENT_MAP.get(pos, GRADIENT_MAP["명사"])
    glow  = GLOW_MAP.get(pos, GLOW_MAP["명사"])
    emoji = word.get("emoji", "📚")

    back_html = ""
    if show_back:
        back_html = f"""
        <div class="wc-ex">
            {word['example_en']}<br>
            <span class="wc-ex-ko">{word['example_ko']}</span>
        </div>"""

    st.markdown(
        f"""
        <div class="word-card">
            <div class="wc-image" style="background:{grad};">
                <span style="filter:drop-shadow(0 0 18px {glow});font-size:5.5rem;">{emoji}</span>
            </div>
            <div class="wc-body">
                <div class="wc-en">{word['english']}</div>
                <div class="wc-pos">{pos}</div>
                <div class="wc-ko">{word['korean']}</div>
                {back_html}
            </div>
        </div>
        <div style='height:18px'></div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(emoji: str, title: str, badge_text: str, back_key: str) -> None:
    """스키밍 / 플래시카드 / 퀴즈 화면 공통 상단"""
    c1, c2, c3 = st.columns([2, 4, 3])
    with c1:
        if st.button("← 홈", key=back_key):
            st.session_state.page = "home"
            st.rerun()
    with c2:
        st.markdown(
            f'<div style="color:#fff;font-weight:700;font-size:1.05rem;padding-top:4px;">{emoji} {title}</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(f'<div class="badge">{badge_text}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  ⑧ PAGE: HOME
# ══════════════════════════════════════════════════════════════════
def page_home() -> None:
    progress_pct = calc_progress_pct()
    render_dashboard(progress_pct)

    st.markdown('<div class="sec-label">📅 오늘의 학습 세션 — Day {}</div>'.format(STUDY_DAY), unsafe_allow_html=True)

    ss = st.session_state  # 짧은 별칭

    # ─── 스키밍 카드 ──────────────────────────────────────────
    skim_stat_html = (
        '<span class="phase-done">완료 ✅</span>'
        if ss.skimming_done
        else '<span>시작 전</span>'
    )
    st.markdown(
        f"""
        <div class="phase-card">
            <div class="phase-hd">
                <span class="phase-name">🔍 스키밍</span>
                <span class="phase-time">~3분</span>
            </div>
            <div class="phase-desc">모르는 단어 {UNKNOWN_TARGET}개를 골라주세요.</div>
            <div class="phase-stat">{skim_stat_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not ss.skimming_done:
        if st.button("🔍 스키밍 시작하기", use_container_width=True, type="primary", key="go_skim"):
            db_reset_today()
            ss.all_words    = load_words()
            ss.skim_index   = 0
            ss.unknown_ids  = []
            ss.skimming_done = False
            ss.page = "skimming"
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── 플래시카드 카드 ──────────────────────────────────────
    fc_locked = not ss.skimming_done
    fc_stat_html = (
        '<span class="phase-done">완료 ✅</span>'
        if ss.flashcard_done
        else ('<span style="color:#475569">🔒 스키밍 완료 후 활성화</span>' if fc_locked else '<span>시작 전</span>')
    )
    lock_cls = "phase-locked" if fc_locked else ""
    st.markdown(
        f"""
        <div class="phase-card {lock_cls}">
            <div class="phase-hd">
                <span class="phase-name">🃏 플래시카드</span>
            </div>
            <div class="phase-desc">선택된 {UNKNOWN_TARGET}개 단어를 집중 암기합니다.</div>
            <div class="phase-stat">{fc_stat_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not fc_locked and not ss.flashcard_done:
        if st.button("🃏 플래시카드 시작하기", use_container_width=True, key="go_fc"):
            ss.fc_queue  = list(ss.unknown_ids)
            ss.fc_flipped = False
            ss.page = "flashcard"
            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── 퀴즈 카드 ────────────────────────────────────────────
    q_locked = not ss.flashcard_done
    q_stat_html = (
        '<span class="phase-done">완료 ✅</span>'
        if ss.quiz_done
        else ('<span style="color:#475569">🔒 플래시카드 완료 후 활성화</span>' if q_locked else '<span>시작 전</span>')
    )
    lock_cls2 = "phase-locked" if q_locked else ""
    st.markdown(
        f"""
        <div class="phase-card {lock_cls2}">
            <div class="phase-hd">
                <span class="phase-name">📝 퀴즈</span>
            </div>
            <div class="phase-desc">실력을 확인하세요.</div>
            <div class="phase-stat">{q_stat_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not q_locked and not ss.quiz_done:
        if st.button("📝 퀴즈 시작하기", use_container_width=True, key="go_quiz"):
            q = list(ss.unknown_ids)
            random.shuffle(q)
            ss.quiz_queue   = q
            ss.quiz_results = {}
            ss.quiz_answered = False
            ss.quiz_choices  = []
            ss.quiz_answer   = ""
            ss.page = "quiz"
            st.rerun()

    # ─── 전체 리셋 버튼 ───────────────────────────────────────
    if ss.skimming_done or ss.flashcard_done or ss.quiz_done:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("🔄 오늘 학습 처음부터 다시 시작", use_container_width=True, key="reset_all"):
            db_reset_today()
            reset_all_session()
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑨ PAGE: SKIMMING
# ══════════════════════════════════════════════════════════════════
def page_skimming() -> None:
    ss     = st.session_state
    words  = ss.all_words
    idx    = ss.skim_index
    unk_n  = len(ss.unknown_ids)
    total  = len(words)

    render_page_header("🔍", "스키밍", f"모름 {unk_n} / {UNKNOWN_TARGET}", "back_skim")

    # ─── 스키밍 완료 조건: 전체 카드를 다 봤거나 UNKNOWN_TARGET 달성
    if idx >= total or unk_n >= UNKNOWN_TARGET:
        # 미분류 단어는 자동으로 'know' 처리
        for w in words:
            if w["skimming_result"] == "pending":
                db_set_skimming(w["word_id"], "know")

        ss.all_words     = load_words()
        ss.skimming_done = True

        st.markdown(
            f"""
            <div style="text-align:center;padding:50px 20px;">
                <div style="font-size:4rem;margin-bottom:14px;">🎉</div>
                <div style="color:#34d399;font-size:1.5rem;font-weight:900;">스키밍 완료!</div>
                <div style="color:#64748b;margin-top:8px;">모르는 단어 <b style="color:#fff">{unk_n}개</b>를 선택했습니다.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🏠 홈으로 돌아가기", use_container_width=True, type="primary", key="skim_to_home"):
            ss.page = "home"
            st.rerun()
        return

    # ─── 진행 바
    st.progress(idx / total)
    st.markdown(
        f'<div style="color:#475569;font-size:0.78rem;margin-bottom:14px;">{idx + 1} / {total} 단어</div>',
        unsafe_allow_html=True,
    )

    word = words[idx]
    render_word_card(word, show_back=False)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✓ 알아요", use_container_width=True, key=f"know_{idx}"):
            db_set_skimming(word["word_id"], "know")
            ss.all_words[idx]["skimming_result"] = "know"
            ss.skim_index += 1
            st.rerun()
    with c2:
        if st.button("✗ 몰라요", use_container_width=True, type="primary", key=f"unk_{idx}"):
            db_set_skimming(word["word_id"], "unknown")
            ss.all_words[idx]["skimming_result"] = "unknown"
            ss.unknown_ids.append(word["word_id"])
            ss.skim_index += 1
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑩ PAGE: FLASHCARD
# ══════════════════════════════════════════════════════════════════
def page_flashcard() -> None:
    ss       = st.session_state
    queue    = ss.fc_queue
    word_map = {w["word_id"]: w for w in ss.all_words}
    total    = len(ss.unknown_ids)
    done_n   = total - len(queue)

    render_page_header("🃏", "플래시카드", f"남은 {len(queue)}개", "back_fc")

    # ─── 플래시카드 완료
    if not queue:
        ss.flashcard_done = True
        st.markdown(
            """
            <div style="text-align:center;padding:50px 20px;">
                <div style="font-size:4rem;margin-bottom:14px;">🚀</div>
                <div style="color:#60a5fa;font-size:1.5rem;font-weight:900;">플래시카드 완료!</div>
                <div style="color:#64748b;margin-top:8px;">이제 퀴즈로 실력을 확인하세요.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🏠 홈으로 돌아가기", use_container_width=True, type="primary", key="fc_to_home"):
            ss.page = "home"
            st.rerun()
        return

    # ─── 진행 바
    st.progress(done_n / total if total else 0)
    st.markdown(
        f'<div style="color:#475569;font-size:0.78rem;margin-bottom:14px;">{done_n + 1} / {total}</div>',
        unsafe_allow_html=True,
    )

    current_id = queue[0]
    word = word_map.get(current_id)
    if not word:
        ss.fc_queue.pop(0)
        st.rerun()
        return

    render_word_card(word, show_back=ss.fc_flipped)

    if not ss.fc_flipped:
        if st.button("👁 뒤집어서 뜻 확인하기", use_container_width=True, key="flip"):
            ss.fc_flipped = True
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 다시보기", use_container_width=True, key="fc_again"):
                db_set_flashcard(current_id, False)
                ss.fc_queue.pop(0)
                ss.fc_queue.append(current_id)   # 큐 맨 뒤로 이동
                ss.fc_flipped = False
                st.rerun()
        with c2:
            if st.button("✓ 기억했어요!", use_container_width=True, type="primary", key="fc_ok"):
                db_set_flashcard(current_id, True)
                ss.fc_queue.pop(0)
                ss.fc_flipped = False
                st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑪ PAGE: QUIZ
# ══════════════════════════════════════════════════════════════════
CHOICE_NUMS = ["①", "②", "③", "④"]


def _build_choices(word: dict, all_words: list[dict]) -> tuple[list[str], str]:
    """정답 1개 + 오답 3개 랜덤 선택지 생성"""
    answer  = word["korean"]
    others  = [w["korean"] for w in all_words if w["word_id"] != word["word_id"]]
    wrongs  = random.sample(others, min(3, len(others)))
    choices = [answer] + wrongs
    random.shuffle(choices)
    return choices, answer


def page_quiz() -> None:
    ss       = st.session_state
    queue    = ss.quiz_queue
    word_map = {w["word_id"]: w for w in ss.all_words}
    total    = len(ss.unknown_ids)
    done_n   = len(ss.quiz_results)

    render_page_header("📝", "퀴즈", f"{done_n} / {total}", "back_quiz")

    # ─── 퀴즈 완료
    if not queue:
        ss.quiz_done = True
        results  = ss.quiz_results
        correct  = sum(1 for v in results.values() if v)
        wrong    = total - correct
        pct      = int(correct / total * 100) if total else 0

        st.markdown(
            f"""
            <div class="result-hero">
                <div class="result-icon">🎯</div>
                <div class="result-title">Day {STUDY_DAY} 완료!</div>
                <div class="result-sub">오늘의 모든 학습을 마쳤습니다</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown(
                f'<div class="dash-card"><div class="dash-label">정답</div><div class="dash-val c-green">{correct}</div></div>',
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                f'<div class="dash-card"><div class="dash-label">오답</div><div class="dash-val c-red">{wrong}</div></div>',
                unsafe_allow_html=True,
            )
        with r3:
            st.markdown(
                f'<div class="dash-card"><div class="dash-label">성취도</div><div class="dash-val c-blue">{pct}%</div></div>',
                unsafe_allow_html=True,
            )

        if wrong > 0:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="sec-label">🔄 다음에 재도전할 단어</div>', unsafe_allow_html=True)
            for wid, passed in results.items():
                if not passed:
                    w = word_map.get(wid)
                    if w:
                        st.markdown(
                            f'<div class="wrong-item"><span class="wi-en">{w["english"]}</span>'
                            f'<span class="wi-ko">{w["korean"]}</span></div>',
                            unsafe_allow_html=True,
                        )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button("🏠 홈으로 돌아가기", use_container_width=True, type="primary", key="quiz_home"):
            ss.page = "home"
            st.rerun()
        return

    # ─── 진행 바
    st.progress(done_n / total if total else 0)
    st.markdown(
        f'<div style="color:#475569;font-size:0.78rem;margin-bottom:16px;">{done_n + 1} / {total} 문제</div>',
        unsafe_allow_html=True,
    )

    current_id = queue[0]
    word       = word_map.get(current_id)
    if not word:
        ss.quiz_queue.pop(0)
        st.rerun()
        return

    # 선택지가 아직 없으면 생성
    if not ss.quiz_choices:
        choices, answer       = _build_choices(word, ss.all_words)
        ss.quiz_choices       = choices
        ss.quiz_answer        = answer
        ss.quiz_answered      = False
        ss.quiz_correct       = False

    # ─── 문제 카드
    st.markdown(
        f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.09);
                    border-radius:22px;padding:22px 24px;margin-bottom:20px;">
            <div style="color:#475569;font-size:0.76rem;font-weight:700;
                        letter-spacing:0.12em;margin-bottom:10px;">다음 영단어의 뜻은?</div>
            <div style="color:#fff;font-size:2.3rem;font-weight:900;letter-spacing:-0.02em;">
                {word['english']}
            </div>
            <div style="color:#60a5fa;font-size:0.8rem;margin-top:6px;">{word['part_of_speech']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─── 선택지 버튼 or 피드백
    if not ss.quiz_answered:
        for i, choice in enumerate(ss.quiz_choices):
            if st.button(
                f"{CHOICE_NUMS[i]}  {choice}",
                use_container_width=True,
                key=f"q_choice_{i}",
            ):
                is_correct             = (choice == ss.quiz_answer)
                ss.quiz_correct        = is_correct
                ss.quiz_answered       = True
                db_set_quiz(current_id, is_correct)
                ss.quiz_results[current_id] = is_correct
                st.rerun()
    else:
        if ss.quiz_correct:
            st.success("✅ 정답입니다! 🚀")
        else:
            st.error(f"❌ 오답!  정답은  **'{ss.quiz_answer}'**  입니다.")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("다음 문제 →", use_container_width=True, type="primary", key="next_q"):
            ss.quiz_queue.pop(0)
            ss.quiz_answered = False
            ss.quiz_choices  = []
            ss.quiz_answer   = ""
            ss.quiz_correct  = False
            st.rerun()


# ══════════════════════════════════════════════════════════════════
#  ⑫ MAIN ROUTER
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    # 1. DB 초기화 (최초 1회)
    init_db()

    # 2. CSS 주입
    inject_css()

    # 3. 세션 초기화
    init_session()

    # 4. 단어 목록 최초 로드
    if not st.session_state.all_words:
        st.session_state.all_words = load_words()

    # 5. 페이지 라우팅
    page = st.session_state.page
    if page == "home":
        page_home()
    elif page == "skimming":
        page_skimming()
    elif page == "flashcard":
        page_flashcard()
    elif page == "quiz":
        page_quiz()
    else:
        st.session_state.page = "home"
        st.rerun()


if __name__ == "__main__":
    main()

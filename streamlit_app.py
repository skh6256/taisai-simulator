from __future__ import annotations

import math
import secrets
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components


def _running_inside_streamlit() -> bool:
    """Return True when this script is being executed by Streamlit's ScriptRunner."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        try:
            return get_script_run_ctx(suppress_warning=True) is not None
        except TypeError:
            return get_script_run_ctx() is not None
    except Exception:
        return False


def _launch_with_streamlit_if_needed() -> None:
    """Allow local execution with: py TaiSai_Simulator_v11_stage_pinch_zoom.py"""
    if __name__ == "__main__" and not _running_inside_streamlit():
        script_path = str(Path(__file__).resolve())
        cmd = [sys.executable, "-m", "streamlit", "run", script_path]
        raise SystemExit(subprocess.call(cmd))


_launch_with_streamlit_if_needed()


# ============================================================
# 기본 설정
# ============================================================
st.set_page_config(
    page_title="강원랜드 다이사이 시뮬레이터",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def enable_mobile_pinch_zoom() -> None:
    """Install Animation-style full-stage pinch zoom/pan on the Streamlit page.

    Mobile behavior:
    - Two fingers: zoom the whole Streamlit content around the pinch midpoint.
    - One finger while zoomed: pan the enlarged content.
    - Pinch back near 1.0x: reset position and scale.
    - At 1.0x, ordinary one-finger page scrolling remains available.

    This intentionally uses CSS transform (translate + scale), not CSS ``zoom``.
    """
    components.html(
        r"""
        <script>
        (function () {
          try {
            const w = window.parent;
            const doc = w.document;

            // Keep the browser itself at 1x. Pinch zoom is handled on the
            // Streamlit stage so every visible element scales together.
            let viewport = doc.querySelector('meta[name="viewport"]');
            if (!viewport) {
              viewport = doc.createElement('meta');
              viewport.name = 'viewport';
              doc.head.appendChild(viewport);
            }
            viewport.setAttribute(
              'content',
              'width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover'
            );

            // A Streamlit rerun recreates this component iframe. Keep one
            // controller on the parent window so event handlers are installed once.
            if (!w.__taisaiStagePinchZoom) {
              const state = {
                scale: 1.0,
                translateX: 0.0,
                translateY: 0.0,
                pinchStartDistance: 0.0,
                pinchStartScale: 1.0,
                pinchLocalX: 0.0,
                pinchLocalY: 0.0,
                panStartX: 0.0,
                panStartY: 0.0,
                panStartTranslateX: 0.0,
                panStartTranslateY: 0.0,
                panning: false,
                gestureOnStage: false,
                MIN_SCALE: 1.0,
                MAX_SCALE: 4.0,
              };

              function getStage() {
                return doc.querySelector('.block-container')
                  || doc.querySelector('[data-testid="stMainBlockContainer"]');
              }

              function getViewport() {
                return doc.querySelector('[data-testid="stAppViewContainer"]')
                  || doc.querySelector('[data-testid="stMain"]')
                  || doc.body;
              }

              function prepareStage(stage) {
                if (!stage) return;
                stage.style.setProperty('transform-origin', '0 0', 'important');
                stage.style.setProperty('will-change', 'transform', 'important');
              }

              function setTouchMode(zoomed) {
                const app = doc.querySelector('.stApp');
                const view = getViewport();
                const stage = getStage();

                // At 1x: normal one-finger scrolling, but native browser pinch is off.
                // Zoomed: all one-finger movement is reserved for stage panning.
                const mode = zoomed ? 'none' : 'pan-x pan-y';
                for (const el of [doc.documentElement, doc.body, app, view, stage]) {
                  if (el) el.style.setProperty('touch-action', mode, 'important');
                }
                if (view) {
                  view.style.setProperty('overscroll-behavior', 'contain', 'important');
                  view.style.setProperty('overflow-x', zoomed ? 'hidden' : '', 'important');
                }
              }

              function applyTransform() {
                const stage = getStage();
                if (!stage) return;
                prepareStage(stage);

                if (state.scale <= 1.001) {
                  state.scale = 1.0;
                  state.translateX = 0.0;
                  state.translateY = 0.0;
                }

                stage.style.setProperty(
                  'transform',
                  `translate(${state.translateX}px, ${state.translateY}px) scale(${state.scale})`,
                  'important'
                );
                setTouchMode(state.scale > 1.001);
              }

              function distance(t0, t1) {
                return Math.hypot(
                  t1.clientX - t0.clientX,
                  t1.clientY - t0.clientY
                );
              }

              function midpoint(t0, t1) {
                return {
                  x: (t0.clientX + t1.clientX) / 2,
                  y: (t0.clientY + t1.clientY) / 2,
                };
              }

              function eventStartedOnStage(event) {
                const stage = getStage();
                if (!stage) return false;
                const target = event.target;
                return !!(target && stage.contains(target));
              }

              doc.addEventListener('touchstart', function (event) {
                const stage = getStage();
                if (!stage) return;
                prepareStage(stage);

                if (event.touches.length === 2) {
                  if (!state.gestureOnStage && !eventStartedOnStage(event)) return;
                  state.gestureOnStage = true;

                  const t0 = event.touches[0];
                  const t1 = event.touches[1];
                  state.pinchStartDistance = Math.max(1, distance(t0, t1));
                  state.pinchStartScale = state.scale;

                  const mid = midpoint(t0, t1);
                  const rect = stage.getBoundingClientRect();

                  // rect.left/top already include the current translation.
                  state.pinchLocalX = (mid.x - rect.left) / state.scale;
                  state.pinchLocalY = (mid.y - rect.top) / state.scale;
                  state.panning = false;
                } else if (
                  event.touches.length === 1
                  && state.scale > 1.001
                  && eventStartedOnStage(event)
                ) {
                  state.gestureOnStage = true;
                  const t = event.touches[0];
                  state.panStartX = t.clientX;
                  state.panStartY = t.clientY;
                  state.panStartTranslateX = state.translateX;
                  state.panStartTranslateY = state.translateY;
                  state.panning = true;
                }
              }, { passive: true, capture: true });

              doc.addEventListener('touchmove', function (event) {
                if (!state.gestureOnStage) return;
                const stage = getStage();
                if (!stage) return;

                if (event.touches.length === 2 && state.pinchStartDistance > 0) {
                  event.preventDefault();

                  const t0 = event.touches[0];
                  const t1 = event.touches[1];
                  const newDistance = Math.max(1, distance(t0, t1));
                  let newScale = state.pinchStartScale
                    * (newDistance / state.pinchStartDistance);
                  newScale = Math.max(
                    state.MIN_SCALE,
                    Math.min(state.MAX_SCALE, newScale)
                  );

                  const mid = midpoint(t0, t1);
                  const rect = stage.getBoundingClientRect();

                  // Recover the stage's untransformed screen origin from the
                  // current transformed rect, then keep the pinch midpoint fixed.
                  const baseLeft = rect.left - state.translateX;
                  const baseTop = rect.top - state.translateY;

                  state.scale = newScale;
                  state.translateX = mid.x - baseLeft - state.pinchLocalX * state.scale;
                  state.translateY = mid.y - baseTop - state.pinchLocalY * state.scale;
                  applyTransform();
                } else if (
                  event.touches.length === 1
                  && state.panning
                  && state.scale > 1.001
                ) {
                  event.preventDefault();
                  const t = event.touches[0];
                  state.translateX = state.panStartTranslateX + (t.clientX - state.panStartX);
                  state.translateY = state.panStartTranslateY + (t.clientY - state.panStartY);
                  applyTransform();
                }
              }, { passive: false, capture: true });

              function finishTouch(event) {
                if (event.touches && event.touches.length < 2) {
                  state.pinchStartDistance = 0.0;
                }

                if (!event.touches || event.touches.length === 0) {
                  state.panning = false;
                  state.gestureOnStage = false;

                  if (state.scale <= 1.03) {
                    state.scale = 1.0;
                    state.translateX = 0.0;
                    state.translateY = 0.0;
                  }
                  applyTransform();
                }
              }

              doc.addEventListener('touchend', finishTouch, { passive: true, capture: true });
              doc.addEventListener('touchcancel', finishTouch, { passive: true, capture: true });

              // Streamlit replaces inner content on rerun. Reapply the transform
              // so the zoom level remains stable while buttons/reruns are used.
              const observer = new MutationObserver(function () {
                w.requestAnimationFrame(applyTransform);
              });
              observer.observe(doc.body, { childList: true, subtree: true });

              state.applyTransform = applyTransform;
              w.__taisaiStagePinchZoom = state;
              applyTransform();
            } else {
              // Component recreated after a Streamlit rerun: simply reapply.
              const controller = w.__taisaiStagePinchZoom;
              if (controller.applyTransform) {
                w.requestAnimationFrame(controller.applyTransform);
              }
            }
          } catch (e) {
            console.log('TaiSai stage pinch zoom:', e);
          }
        })();
        </script>
        """,
        height=0,
        width=0,
    )

enable_mobile_pinch_zoom()

KST = ZoneInfo("Asia/Seoul")
DEFAULT_CAPITAL = 200_000
MIN_MONEY_UNIT = 1_000
MAX_TOTAL_BET = 100_000
DEFAULT_BET = 10_000

COLORS = {
    "page_bg": "#0F172A",       # 짙은 네이비
    "panel_bg": "#F8FAFC",      # 밝은 회백색
    "text": "#0F172A",
    "muted": "#64748B",
    "border": "#CBD5E1",
    "bet_active": "#DBEAFE",    # 연한 파랑
    "win": "#DCFCE7",           # 연한 민트
    "win_active": "#A7F3D0",    # 내가 베팅한 자리가 당첨: 조금 더 진한 민트
    "danger": "#FEE2E2",
    "accent": "#2563EB",
}

DICE_CHARS = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
TOTAL_COUNTS = {
    3: 1, 4: 3, 5: 6, 6: 10, 7: 15, 8: 21, 9: 25,
    10: 27, 11: 27, 12: 25, 13: 21, 14: 15, 15: 10,
    16: 6, 17: 3, 18: 1,
}
TOTAL_ODDS = {
    4: 50, 5: 30, 6: 18, 7: 12, 8: 8, 9: 6, 10: 6,
    11: 6, 12: 6, 13: 8, 14: 12, 15: 18, 16: 30, 17: 50,
}


# ============================================================
# 베팅 정의
# ============================================================
def build_bet_definitions() -> dict[str, dict]:
    bets: dict[str, dict] = {
        "BIG": {
            "name": "BIG",
            "detail": "합계 11~17 (Triple 제외)",
            "odds": 1,
            "win_count": 105,
            "help_note": "세 주사위가 모두 같은 Triple이면 합계가 11~17이어도 BIG은 패배합니다.",
        },
        "SMALL": {
            "name": "SMALL",
            "detail": "합계 4~10 (Triple 제외)",
            "odds": 1,
            "win_count": 105,
            "help_note": "세 주사위가 모두 같은 Triple이면 합계가 4~10이어도 SMALL은 패배합니다.",
        },
        "EVEN": {
            "name": "EVEN",
            "detail": "합계 짝수 (Triple 제외)",
            "odds": 1,
            "win_count": 105,
            "help_note": "세 주사위가 모두 같은 Triple이면 합계가 짝수여도 EVEN은 패배합니다.",
        },
        "ODD": {
            "name": "ODD",
            "detail": "합계 홀수 (Triple 제외)",
            "odds": 1,
            "win_count": 105,
            "help_note": "세 주사위가 모두 같은 Triple이면 합계가 홀수여도 ODD는 패배합니다.",
        },
        "ANY_TRIPLE": {
            "name": "ANY TRIPLE",
            "detail": "어떤 숫자든 세 주사위가 모두 같음",
            "odds": 24,
            "win_count": 6,
        },
    }

    for n in range(1, 7):
        bets[f"PAIR_{n}"] = {
            "name": f"PAIR {n}-{n}",
            "detail": f"숫자 {n}이 2개 이상",
            "odds": 8,
            "win_count": 16,
            "help_note": "이 시뮬레이터는 해당 숫자의 Triple도 Pair 당첨에 포함하여 계산합니다.",
        }
        bets[f"TRIPLE_{n}"] = {
            "name": f"TRIPLE {n}-{n}-{n}",
            "detail": f"정확히 {n}-{n}-{n}",
            "odds": 150,
            "win_count": 1,
        }
        bets[f"SINGLE_{n}"] = {
            "name": f"SINGLE {n}",
            "detail": f"숫자 {n} 출현 개수에 따라 1/2/3배",
            "odds": None,
            "win_count": 91,
        }

    for total in range(4, 18):
        bets[f"TOTAL_{total}"] = {
            "name": f"TOTAL {total}",
            "detail": f"세 주사위 합계가 정확히 {total}",
            "odds": TOTAL_ODDS[total],
            "win_count": TOTAL_COUNTS[total],
        }

    for a in range(1, 7):
        for b in range(a + 1, 7):
            bets[f"DOMINO_{a}_{b}"] = {
                "name": f"DOMINO {a} & {b}",
                "detail": f"주사위 3개에 {a}와 {b}가 모두 포함",
                "odds": 5,
                "win_count": 30,
            }

    return bets


BET_DEFINITIONS = build_bet_definitions()


# ============================================================
# 상태 / 계산 함수
# ============================================================
def fmt_money(value: int | float) -> str:
    return f"{int(math.floor(value)):,}원"


def fmt_pct(value: float) -> str:
    if value < 1:
        return f"{value:.3f}%"
    return f"{value:.2f}%"


def current_time() -> datetime:
    return datetime.now(KST)


def is_triple(dice: list[int] | tuple[int, int, int]) -> bool:
    return dice[0] == dice[1] == dice[2]


def payout_multiplier(bet_id: str, dice: list[int] | tuple[int, int, int]) -> int | None:
    """당첨 시 순수 배당배수(원금 제외)를 반환. 패배 시 None."""
    total = sum(dice)
    triple = is_triple(dice)

    if bet_id == "BIG":
        return 1 if (not triple and 11 <= total <= 17) else None
    if bet_id == "SMALL":
        return 1 if (not triple and 4 <= total <= 10) else None
    if bet_id == "EVEN":
        return 1 if (not triple and total % 2 == 0) else None
    if bet_id == "ODD":
        return 1 if (not triple and total % 2 == 1) else None
    if bet_id == "ANY_TRIPLE":
        return 24 if triple else None

    if bet_id.startswith("PAIR_"):
        n = int(bet_id.split("_")[1])
        return 8 if dice.count(n) >= 2 else None

    if bet_id.startswith("TRIPLE_"):
        n = int(bet_id.split("_")[1])
        return 150 if tuple(dice) == (n, n, n) else None

    if bet_id.startswith("TOTAL_"):
        target = int(bet_id.split("_")[1])
        return TOTAL_ODDS[target] if total == target else None

    if bet_id.startswith("DOMINO_"):
        _, a, b = bet_id.split("_")
        a, b = int(a), int(b)
        return 5 if (a in dice and b in dice) else None

    if bet_id.startswith("SINGLE_"):
        n = int(bet_id.split("_")[1])
        count = dice.count(n)
        return count if count > 0 else None

    return None


def winning_bet_ids(dice: list[int]) -> set[str]:
    return {bet_id for bet_id in BET_DEFINITIONS if payout_multiplier(bet_id, dice) is not None}


def bet_stats(bet_id: str) -> dict[str, float | int | str]:
    info = BET_DEFINITIONS[bet_id]
    win_count = info["win_count"]
    probability = win_count / 216

    if bet_id.startswith("SINGLE_"):
        # 1개: 75가지, 2개: 15가지, 3개: 1가지
        expected_return_ratio = (75 * 2 + 15 * 3 + 1 * 4) / 216
        return_amount = "1개 20,000원 / 2개 30,000원 / 3개 40,000원"
        odds_text = "1 / 2 / 3 : 1"
    else:
        odds = int(info["odds"])
        expected_return_ratio = probability * (odds + 1)
        return_amount = fmt_money(10_000 * (odds + 1))
        odds_text = f"{odds}:1"

    expected_return = 10_000 * expected_return_ratio
    house_edge = max(0.0, 1 - expected_return_ratio)

    return {
        "probability": probability * 100,
        "odds_text": odds_text,
        "return_amount": return_amount,
        "expected_return": expected_return,
        "house_edge": house_edge * 100,
    }


def init_session_state() -> None:
    defaults = {
        "page": "main",
        "capital_input": DEFAULT_CAPITAL,
        "main_capital_widget": DEFAULT_CAPITAL,
        "initial_capital": DEFAULT_CAPITAL,
        "bankroll": DEFAULT_CAPITAL,
        "bets": {},              # {bet_id: amount}
        "repeat_bets": set(),    # bet_id set
        "dice": [1, 1, 1],
        "last_winners": set(),
        "last_round_profit": None,
        "game_no": 0,
        "logs": [],
        "notice": "",
        "bankrupt_pending": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def start_game(initial_capital: int) -> None:
    st.session_state.page = "game"
    st.session_state.initial_capital = int(initial_capital)
    st.session_state.bankroll = int(initial_capital)
    st.session_state.bets = {}
    st.session_state.repeat_bets = set()
    st.session_state.dice = [1, 1, 1]
    st.session_state.last_winners = set()
    st.session_state.last_round_profit = None
    st.session_state.game_no = 0
    st.session_state.logs = []
    st.session_state.notice = ""
    st.session_state.bankrupt_pending = False


def reset_current_game() -> None:
    start_game(st.session_state.initial_capital)


def total_current_bet() -> int:
    return int(sum(st.session_state.bets.values()))


def total_assets() -> int:
    return int(st.session_state.bankroll + total_current_bet())


def clear_bet(bet_id: str) -> None:
    old = int(st.session_state.bets.get(bet_id, 0))
    if old > 0:
        st.session_state.bankroll += old
    st.session_state.bets.pop(bet_id, None)
    st.session_state.repeat_bets.discard(bet_id)


def apply_bet(bet_id: str, new_amount: int, repeat: bool) -> tuple[bool, str]:
    old_amount = int(st.session_state.bets.get(bet_id, 0))
    other_total = total_current_bet() - old_amount

    if new_amount < MIN_MONEY_UNIT:
        return False, "베팅 금액은 최소 1,000원입니다."
    if new_amount % MIN_MONEY_UNIT != 0:
        return False, "베팅 금액은 1,000원 단위로 입력해주세요."
    if new_amount > MAX_TOTAL_BET:
        return False, "한 판 전체 베팅 상한은 100,000원입니다."
    if other_total + new_amount > MAX_TOTAL_BET:
        remain = MAX_TOTAL_BET - other_total
        return False, f"전체 베팅 합계가 100,000원을 초과합니다. 이 구역에는 최대 {remain:,}원까지 가능합니다."

    delta = new_amount - old_amount
    if delta > st.session_state.bankroll:
        return False, f"보유금액이 부족합니다. 추가로 사용할 수 있는 금액은 {st.session_state.bankroll:,}원입니다."

    st.session_state.bankroll -= delta
    st.session_state.bets[bet_id] = int(new_amount)
    if repeat:
        st.session_state.repeat_bets.add(bet_id)
    else:
        st.session_state.repeat_bets.discard(bet_id)
    return True, ""


def roll_dice_and_settle() -> None:
    dice = [secrets.randbelow(6) + 1 for _ in range(3)]
    st.session_state.dice = dice
    st.session_state.game_no += 1
    st.session_state.last_winners = winning_bet_ids(dice)
    st.session_state.notice = ""

    bets_snapshot = dict(st.session_state.bets)
    repeat_snapshot = set(st.session_state.repeat_bets)
    total_stake = sum(bets_snapshot.values())
    total_return = 0
    bet_results: list[dict] = []

    for bet_id, stake in bets_snapshot.items():
        mult = payout_multiplier(bet_id, dice)
        if mult is None:
            returned = 0
            won = False
        else:
            returned = int(math.floor(stake * (mult + 1)))
            won = True
            st.session_state.bankroll += returned
            total_return += returned

        bet_results.append({
            "bet_id": bet_id,
            "name": BET_DEFINITIONS[bet_id]["name"],
            "stake": int(stake),
            "won": won,
            "multiplier": mult,
            "returned": int(returned),
        })

    round_profit = int(total_return - total_stake)
    st.session_state.last_round_profit = round_profit

    # 현재 판 베팅은 모두 정산 완료. 반복 베팅만 다음 판에 다시 올립니다.
    st.session_state.bets = {}
    st.session_state.repeat_bets = set()

    repeat_total = sum(bets_snapshot[bid] for bid in repeat_snapshot if bid in bets_snapshot)
    repeat_success = True
    if repeat_total > 0:
        if repeat_total <= st.session_state.bankroll and repeat_total <= MAX_TOTAL_BET:
            for bid in repeat_snapshot:
                if bid in bets_snapshot:
                    st.session_state.bets[bid] = bets_snapshot[bid]
                    st.session_state.repeat_bets.add(bid)
            st.session_state.bankroll -= repeat_total
        else:
            repeat_success = False
            st.session_state.notice = "잔액 부족으로 계속 베팅이 해제되었습니다."

    st.session_state.logs.append({
        "game_no": st.session_state.game_no,
        "time": current_time().strftime("%Y-%m-%d %H:%M:%S"),
        "dice": tuple(dice),
        "total": sum(dice),
        "bets": bet_results,
        "stake": int(total_stake),
        "return": int(total_return),
        "profit": round_profit,
        "bankroll_after_settlement": int(st.session_state.bankroll + (repeat_total if repeat_success else 0)),
        "next_repeat_total": int(repeat_total if repeat_success else 0),
        "available_cash_after_repeat": int(st.session_state.bankroll),
    })

    # 정산 후 사용 가능한 현금과 테이블 베팅을 모두 합쳐도 0원이면 파산 처리합니다.
    # (베팅 중 보유금액이 0원인 상황은 파산이 아니므로 반드시 정산 후에만 검사)
    st.session_state.bankrupt_pending = total_assets() <= 0


def build_log_text() -> str:
    now = current_time()
    lines = [
        "강원랜드 다이사이 시뮬레이터 - 플레이 로그",
        "=" * 58,
        f"저장 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"초기 자본금: {st.session_state.initial_capital:,}원",
        f"현재 보유금액(사용 가능): {st.session_state.bankroll:,}원",
        f"현재 테이블 베팅금액: {total_current_bet():,}원",
        f"누적 게임 수: {st.session_state.game_no}회",
        "",
    ]

    if not st.session_state.logs:
        lines.append("플레이 기록이 없습니다.")
    else:
        for entry in st.session_state.logs:
            d1, d2, d3 = entry["dice"]
            lines.append(
                f"[게임 {entry['game_no']}] {entry['time']} | "
                f"주사위 {d1}/{d2}/{d3} | 합계 {entry['total']}"
            )
            if not entry["bets"]:
                lines.append("  베팅 없음")
            else:
                for result in entry["bets"]:
                    status = "WIN" if result["won"] else "LOSE"
                    if result["won"]:
                        odds = f"{result['multiplier']}:1"
                        lines.append(
                            f"  - {result['name']}: {result['stake']:,}원 | {status} | "
                            f"배당 {odds} | 반환 {result['returned']:,}원"
                        )
                    else:
                        lines.append(
                            f"  - {result['name']}: {result['stake']:,}원 | {status} | 반환 0원"
                        )
            lines.append(
                f"  총 베팅 {entry['stake']:,}원 | 총 반환 {entry['return']:,}원 | "
                f"이번 판 순손익 {entry['profit']:+,}원"
            )
            if entry["next_repeat_total"]:
                lines.append(f"  다음 판 반복 베팅 예약: {entry['next_repeat_total']:,}원")
            lines.append("")

    if st.session_state.bets:
        lines.append("[현재 다음 판에 올라가 있는 베팅]")
        for bid, amount in st.session_state.bets.items():
            repeat = " (계속 베팅 ON)" if bid in st.session_state.repeat_bets else ""
            lines.append(f"- {BET_DEFINITIONS[bid]['name']}: {amount:,}원{repeat}")

    return "\n".join(lines)


# ============================================================
# CSS
# ============================================================
def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        :root {{ color-scheme: light !important; }}
        html, body, [data-testid="stAppViewContainer"], .stApp {{
            background: {COLORS['page_bg']} !important;
        }}
        html, body {{
            touch-action: pan-x pan-y !important;
            -webkit-text-size-adjust: 100%;
            max-width:100% !important;
        }}
        .stApp {{
            touch-action: pan-x pan-y !important;
            color: #F8FAFC !important;
        }}
        [data-testid="stHeader"], [data-testid="stToolbar"], footer {{
            display: none !important;
        }}
        [data-testid="stAppViewContainer"] {{
            overscroll-behavior: contain !important;
        }}
        .block-container {{
            max-width: 1660px !important;
            padding: .35rem 1rem .45rem 1rem !important;
            transform-origin: 0 0 !important;
            will-change: transform !important;
        }}

        /* Streamlit/브라우저 테마와 무관하게 글자색을 고정 */
        h1, h2, h3, h4, p, label, .stMarkdown, .stCaption {{
            color: #F8FAFC !important;
        }}
        [data-testid="stNumberInput"] input,
        [data-baseweb="input"] input {{
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
            background: #FFFFFF !important;
        }}
        [data-testid="stNumberInput"] button {{
            color: #0F172A !important;
            background: #F8FAFC !important;
        }}
        [data-testid="stDialog"] {{ color-scheme: light !important; }}
        [data-testid="stDialog"] > div {{ background: #FFFFFF !important; }}
        /* 다크/라이트 테마와 무관하게 Dialog의 모든 본문 글자를 진한 색으로 고정 */
        [data-testid="stDialog"] p,
        [data-testid="stDialog"] label,
        [data-testid="stDialog"] span,
        [data-testid="stDialog"] li,
        [data-testid="stDialog"] strong,
        [data-testid="stDialog"] em,
        [data-testid="stDialog"] code,
        [data-testid="stDialog"] h1,
        [data-testid="stDialog"] h2,
        [data-testid="stDialog"] h3,
        [data-testid="stDialog"] h4,
        [data-testid="stDialog"] [data-testid="stMarkdownContainer"],
        [data-testid="stDialog"] [data-testid="stMarkdownContainer"] * {{
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
        }}
        [data-testid="stDialog"] input {{
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
            background: #FFFFFF !important;
        }}

        /* 상단 */
        .top-title {{
            color: #F8FAFC !important;
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.05;
            margin: .1rem 0 .25rem 0;
        }}
        .metric-card {{
            height: 58px;
            box-sizing: border-box;
            background: {COLORS['panel_bg']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 7px 11px;
            overflow: hidden;
        }}
        .metric-label {{
            color: #475569 !important;
            font-size: .72rem;
            font-weight: 700;
            line-height: 1.05;
            white-space: nowrap;
        }}
        .metric-value {{
            color: #0F172A !important;
            font-size: 1.22rem;
            font-weight: 850;
            line-height: 1.28;
            white-space: nowrap;
        }}
        .metric-sub {{
            color: #64748B !important;
            font-size: .62rem;
            line-height: 1;
        }}
        .dice-box {{
            background: {COLORS['panel_bg']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            text-align: center;
            height: 60px;
            box-sizing: border-box;
            padding: 1px 5px;
            box-shadow: 0 2px 7px rgba(0,0,0,.10);
        }}
        .dice-face {{
            color: #111827 !important;
            font-size: 47px;
            line-height: 1.12;
            user-select: none;
        }}
        .result-card {{
            background: {COLORS['panel_bg']};
            border: 1px solid {COLORS['border']};
            border-radius: 9px;
            padding: 5px 10px;
            color: {COLORS['text']} !important;
            margin: 3px 0 3px 0;
            font-size: .82rem;
            line-height: 1.15;
        }}
        .result-card, .result-card b, .result-card span {{ color: {COLORS['text']} !important; }}
        .compact-caption {{
            color: #94A3B8 !important;
            font-size: .68rem;
            margin: 2px 0 4px 0;
            line-height: 1.1;
        }}
        /* 자금 카드와 주사위 영역을 시각적으로 분리 */
        .st-key-dice_section {{
            margin-top: 10px !important;
            margin-bottom: 2px !important;
        }}

        /* 실제 다이사이 테이블 사진을 배치 도면으로 사용한 게임판.
           사진 자체를 배경으로 깔지 않고, 현장과 동일한 구역/비율/표기를 재현한다. */
        .st-key-game_board {{
            width: 100% !important;
            max-width: 1480px !important;
            min-width: 0 !important;
            box-sizing: border-box !important;
            margin: 4px auto 0 auto !important;
            background: #F8FAFC !important;
            border: clamp(2px, .54cqw, 8px) solid #17366D !important;
            border-radius: clamp(6px, 1.62cqw, 24px) !important;
            padding: 0 !important;
            overflow: hidden !important;
            touch-action: pan-x pan-y !important;
            container-type: inline-size !important;
        }}
        .st-key-game_board > div,
        .st-key-game_board [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
            row-gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .st-key-game_board [data-testid="stHorizontalBlock"] {{
            flex-wrap: nowrap !important;
            gap: 0 !important;
            column-gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .st-key-game_board [data-testid="column"] {{
            min-width: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        .st-key-game_board .stMarkdown,
        .st-key-game_board .stButton,
        .st-key-game_board [data-testid="stElementContainer"] {{
            margin: 0 !important;
            padding: 0 !important;
        }}

        /* 모든 베팅 셀 공통: 현장 테이블처럼 흰색 면 + 진한 경계선 */
        .st-key-game_board [class*="st-key-cell_"] {{
            position: relative !important;
            box-sizing: border-box !important;
            border: max(.35px, .095cqw) solid #475569 !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
            background: #F8FAFC !important;
        }}
        .st-key-game_board [class*="st-key-cell_"] p,
        .st-key-game_board [class*="st-key-cell_"] span {{
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
        }}

        /* 셀 상태: 일반 / 베팅 / 당첨 / 베팅+당첨 */
        .st-key-game_board [class*="st-key-cell_"][class*="_state_active"] {{
            background: #DBEAFE !important;
            border-color: #60A5FA !important;
        }}
        .st-key-game_board [class*="st-key-cell_"][class*="_state_win"] {{
            background: #DCFCE7 !important;
            border-color: #4ADE80 !important;
        }}
        .st-key-game_board [class*="st-key-cell_"][class*="_state_winactive"] {{
            background: #A7F3D0 !important;
            border-color: #059669 !important;
            box-shadow: inset 0 0 0 2px rgba(5,150,105,.26) !important;
        }}

        /* 실제 사진의 행 높이 비율에 가깝게 설정 */
        .st-key-game_board [class*="st-key-cell_top_"] {{ height: 4.60cqw !important; min-height: 4.60cqw !important; }}
        .st-key-game_board [class*="st-key-cell_bigsmall_"] {{ height: 8.38cqw !important; min-height: 8.38cqw !important; }}
        .st-key-game_board [class*="st-key-cell_total_"] {{ height: 8.65cqw !important; min-height: 8.65cqw !important; }}
        .st-key-game_board [class*="st-key-cell_domino_"] {{ height: 4.32cqw !important; min-height: 4.32cqw !important; }}
        .st-key-game_board [class*="st-key-cell_bottom_"] {{ height: 7.57cqw !important; min-height: 7.57cqw !important; }}

        /* v06: 베팅칸 표시는 HTML/SVG로 그려 폰트에 따라 주사위가 깨지는 문제를 제거 */
        .st-key-game_board [class*="st-key-visualwrap_"] {{
            position: absolute !important;
            inset: 0 !important;
            z-index: 2 !important;
            padding: 0 !important;
            margin: 0 !important;
            pointer-events: none !important;
        }}
        .st-key-game_board [class*="st-key-visualwrap_"] > div,
        .st-key-game_board [class*="st-key-visualwrap_"] [data-testid="stVerticalBlock"],
        .st-key-game_board [class*="st-key-visualwrap_"] [data-testid="stElementContainer"],
        .st-key-game_board [class*="st-key-visualwrap_"] .stMarkdown {{
            position: absolute !important;
            inset: 0 !important;
            width: 100% !important;
            height: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        .bet-visual {{
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            box-sizing: border-box;
            padding: 3px 5px;
            color: #0F172A !important;
            font-family: Arial, "Noto Sans KR", sans-serif;
            text-align: center;
            line-height: 1;
            pointer-events: none;
            overflow: hidden;
        }}
        .bet-visual * {{ color: #0F172A !important; -webkit-text-fill-color: #0F172A !important; }}

        /* 실제 주사위처럼 보이는 SVG */
        .dice-svg {{ display: inline-block; vertical-align: middle; flex: 0 0 auto; }}
        .dice-xs {{ width: 18px; height: 18px; }}
        .dice-sm {{ width: 25px; height: 25px; }}
        .dice-triple {{ width: 24px; height: 24px; }}
        .dice-any {{ width: 17px; height: 17px; }}
        .dice-md {{ width: 35px; height: 35px; }}
        .dice-lg {{ width: 58px; height: 58px; }}

        /* 게임판 내부의 모든 시각요소는 테이블 폭에 비례해 함께 축소/확대됩니다.
           세로 모바일에서도 1480px 현장판 전체가 화면 가로폭 안에 들어오고, 필요할 때 핀치 줌으로 확대합니다. */
        .st-key-game_board .dice-xs {{ width:1.22cqw; height:1.22cqw; }}
        .st-key-game_board .dice-sm {{ width:1.69cqw; height:1.69cqw; }}
        .st-key-game_board .dice-triple {{ width:1.62cqw; height:1.62cqw; }}
        .st-key-game_board .dice-any {{ width:1.15cqw; height:1.15cqw; }}
        .st-key-game_board .dice-md {{ width:2.36cqw; height:2.36cqw; }}
        .st-key-game_board .dice-lg {{ width:3.92cqw; height:3.92cqw; }}
        .dice-row {{ display:flex; align-items:center; justify-content:center; gap:4px; white-space:nowrap; }}
        .top-dice-row {{ gap:.20cqw; }}
        .triple-stack {{
            display:flex; flex-direction:column; align-items:center; justify-content:center;
            gap:.07cqw; line-height:0;
        }}
        .triple-stack-bottom {{ display:flex; align-items:center; justify-content:center; gap:.14cqw; line-height:0; }}
        .any-triple-stack {{
            display:flex; flex-direction:column; align-items:center; justify-content:center;
            gap:0; line-height:0;
        }}
        .any-triple-bottom {{ display:flex; align-items:center; justify-content:center; gap:.07cqw; line-height:0; }}
        .domino-dice-row {{ gap:.34cqw; }}

        /* BIG / SMALL / ANY TRIPLE */
        .bigsmall-symbol {{ font-family:"Noto Serif CJK KR", "Noto Serif KR", serif; font-size:3.30cqw; font-weight:900; line-height:.78; }}
        .bigsmall-range {{ font-size:1.04cqw; font-weight:850; margin-top:.34cqw; }}
        .bigsmall-en {{ font-size:.91cqw; font-weight:900; margin-top:.07cqw; }}
        .any-grid {{
            display:grid;
            grid-template-columns:repeat(3, 1fr);
            grid-template-rows:repeat(2, auto);
            gap:.14cqw 1.22cqw;
            width:74%;
            max-width:none;
            margin:0 auto .20cqw auto;
        }}
        .any-item {{ display:flex; align-items:center; justify-content:center; }}
        .any-pay {{ font-size:1.11cqw; font-weight:900; line-height:1; }}

        /* TOTAL: 현장판처럼 숫자 / 1 / WINS / 배당을 반드시 각각 줄바꿈 */
        .total-num {{ font-family:Georgia, "Times New Roman", serif; font-size:2.72cqw; font-weight:900; line-height:.90; }}
        .total-small {{ font-family:Georgia, "Times New Roman", serif; font-size:1.18cqw; font-weight:800; line-height:1.00; }}
        .total-wins {{ font-size:.92cqw; letter-spacing:.04em; line-height:1.05; }}

        /* EVEN / ODD 및 Single */
        .eo-text {{ font-family:Georgia, "Times New Roman", serif; font-size:2.76cqw; font-weight:700; line-height:1; }}
        .single-wrap {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.27cqw; }}

        /* 베팅액은 실제 표기를 방해하지 않도록 하단에 작은 칩 형태로 표시 */
        .bet-amount-chip {{
            position:absolute;
            left:50%; bottom:.20cqw; transform:translateX(-50%);
            padding:.14cqw .41cqw; border-radius:999px;
            background:#2563EB; color:#FFFFFF !important;
            -webkit-text-fill-color:#FFFFFF !important;
            font-size:.65cqw; font-weight:900; line-height:1;
            box-shadow:0 1px 2px rgba(0,0,0,.18);
            white-space:nowrap;
        }}

        /* 셀 전체를 투명한 베팅 버튼으로 덮고 시각표현은 위 HTML/SVG가 담당 */
        .st-key-game_board [class*="st-key-betwrap_"] {{
            position:absolute !important;
            inset:0 !important;
            z-index:8 !important;
            padding:0 !important;
            margin:0 !important;
        }}
        .st-key-game_board [class*="st-key-betwrap_"] > div,
        .st-key-game_board [class*="st-key-betwrap_"] [data-testid="stVerticalBlock"],
        .st-key-game_board [class*="st-key-betwrap_"] [data-testid="stElementContainer"],
        .st-key-game_board [class*="st-key-betwrap_"] .stButton {{
            position:absolute !important;
            inset:0 !important;
            width:100% !important;
            height:100% !important;
            min-height:0 !important;
            padding:0 !important;
            margin:0 !important;
        }}
        .st-key-game_board [class*="st-key-betwrap_"] button {{
            position:absolute !important;
            inset:0 !important;
            width:100% !important;
            height:100% !important;
            min-height:0 !important;
            padding:0 !important;
            margin:0 !important;
            border:0 !important;
            border-radius:0 !important;
            background:transparent !important;
            color:transparent !important;
            box-shadow:none !important;
        }}
        .st-key-game_board [class*="st-key-betwrap_"] button p,
        .st-key-game_board [class*="st-key-betwrap_"] button span {{
            color:transparent !important;
            -webkit-text-fill-color:transparent !important;
            font-size:0 !important;
        }}

        /* 도움말 ? 버튼: 우측 상단에 작게 겹쳐 표시 */
        .st-key-game_board [class*="st-key-helpwrap_"] {{
            position: absolute !important;
            top: .27cqw !important;
            right: .27cqw !important;
            z-index: 20 !important;
            width: 1.35cqw !important;
            height: 1.35cqw !important;
            min-height: 1.35cqw !important;
            padding: 0 !important;
            margin: 0 !important;
            gap: 0 !important;
        }}
        .st-key-game_board [class*="st-key-helpwrap_"] .stButton,
        .st-key-game_board [class*="st-key-helpwrap_"] [data-testid="stElementContainer"] {{
            width: 1.35cqw !important;
            height: 1.35cqw !important;
            min-height: 1.35cqw !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .st-key-game_board [class*="st-key-helpwrap_"] button {{
            min-height: 1.35cqw !important;
            height: 1.35cqw !important;
            width: 1.35cqw !important;
            padding: 0 !important;
            border-radius: 999px !important;
            font-size: .67cqw !important;
            font-weight: 900 !important;
            background: #111827 !important;
            color: #FFFFFF !important;
            border: 0 !important;
        }}
        .st-key-game_board [class*="st-key-helpwrap_"] button p,
        .st-key-game_board [class*="st-key-helpwrap_"] button span {{
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-size: .67cqw !important;
        }}

        /* 장식 셀 */
        .decor-cell {{
            box-sizing: border-box;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            margin: 0;
            padding: 2px;
            overflow: hidden;
            border: max(.35px, .095cqw) solid #475569;
            color: #0F172A !important;
            font-family: Arial, "Noto Sans KR", "Segoe UI Symbol", sans-serif;
            font-size: .96cqw;
            font-weight: 900;
            text-align: center;
            line-height: 1.00;
            white-space: pre-line;
        }}
        .decor-blue {{
            background: linear-gradient(90deg, #D6E5F7 0%, #EDF5FE 48%, #C9DCF3 100%);
            border-color: #475569;
        }}
        .decor-red {{ background: #FF1717; border-color: #475569; color: #FFFFFF !important; }}
        .decor-label {{ background: #F8FAFC; }}
        .decor-top {{ height: 4.60cqw; }}
        .decor-bigsmall {{ height: 8.38cqw; }}
        .decor-total {{ height: 8.65cqw; }}
        .decor-domino {{ height: 4.32cqw; }}
        .decor-bottom {{ height: 7.57cqw; }}

        /* 일반 버튼 - 브라우저/Streamlit 다크모드와 무관하게 항상 보이도록 고정 */
        button[kind="primary"] {{
            background: #FF4B4B !important;
            color: #FFFFFF !important;
            border: 1px solid #FF4B4B !important;
        }}
        button[kind="primary"] p,
        button[kind="primary"] span {{
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }}
        button[kind="secondary"] {{
            background: #F1F5F9 !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
        }}
        button[kind="secondary"]:hover {{
            background: #E2E8F0 !important;
            border-color: #94A3B8 !important;
        }}
        button[kind="secondary"] p,
        button[kind="secondary"] span {{
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
        }}
        [data-testid="stDialog"] button[aria-label="Close"] {{
            color: #0F172A !important;
            background: transparent !important;
        }}
        [data-testid="stDialog"] button[aria-label="Close"] svg {{
            fill: #0F172A !important;
            color: #0F172A !important;
        }}

        /* 메인화면 */
        .main-card {{
            max-width: 620px;
            margin: 5vh auto 0 auto;
            background: {COLORS['panel_bg']};
            border-radius: 20px;
            padding: 24px 28px;
            box-shadow: 0 14px 35px rgba(0,0,0,.28);
        }}
        .main-card h1, .main-card p, .main-card b {{ color: {COLORS['text']} !important; }}

        /* Streamlit의 모바일 기본 동작(열 세로 쌓기)을 필요한 구역에서만 무효화합니다. */
        .st-key-top_nav [data-testid="stHorizontalBlock"],
        .st-key-money_row [data-testid="stHorizontalBlock"],
        .st-key-dice_section [data-testid="stHorizontalBlock"],
        .st-key-game_board [class*="st-key-row_"] [data-testid="stHorizontalBlock"] {{
            display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
        }}
        .st-key-top_nav [data-testid="column"],
        .st-key-money_row [data-testid="column"],
        .st-key-dice_section [data-testid="column"],
        .st-key-game_board [class*="st-key-row_"] [data-testid="column"] {{
            min-width:0 !important; width:0 !important; flex-basis:0 !important; flex-shrink:1 !important;
            padding-left:0 !important; padding-right:0 !important;
        }}

        /* 상단 4열: 0.55 / 7.4 / 0.7 / 0.7 */
        .st-key-top_nav [data-testid="column"]:nth-child(1) {{ flex-grow:.55 !important; }}
        .st-key-top_nav [data-testid="column"]:nth-child(2) {{ flex-grow:7.4 !important; }}
        .st-key-top_nav [data-testid="column"]:nth-child(3),
        .st-key-top_nav [data-testid="column"]:nth-child(4) {{ flex-grow:.7 !important; }}
        /* 자금 3열 */
        .st-key-money_row [data-testid="column"] {{ flex-grow:1 !important; }}
        /* 주사위 3 + 굴리기 */
        .st-key-dice_section [data-testid="column"]:nth-child(1),
        .st-key-dice_section [data-testid="column"]:nth-child(2),
        .st-key-dice_section [data-testid="column"]:nth-child(3) {{ flex-grow:1 !important; }}
        .st-key-dice_section [data-testid="column"]:nth-child(4) {{ flex-grow:1.05 !important; }}

        /* 게임판 행 비율을 명시적으로 고정. 모바일에서도 1480px 표를 잘라 보여주는 대신 화면 폭 안에 전부 축소합니다. */
        .st-key-row_top [data-testid="column"] {{ flex-grow:.82 !important; }}
        .st-key-row_top [data-testid="column"]:nth-child(1),
        .st-key-row_top [data-testid="column"]:nth-child(9),
        .st-key-row_top [data-testid="column"]:nth-child(17) {{ flex-grow:1 !important; }}
        .st-key-row_top [data-testid="column"]:nth-child(5),
        .st-key-row_top [data-testid="column"]:nth-child(13) {{ flex-grow:.55 !important; }}

        .st-key-row_bigsmall [data-testid="column"]:nth-child(1),
        .st-key-row_bigsmall [data-testid="column"]:nth-child(2),
        .st-key-row_bigsmall [data-testid="column"]:nth-child(4),
        .st-key-row_bigsmall [data-testid="column"]:nth-child(5) {{ flex-grow:2.5 !important; }}
        .st-key-row_bigsmall [data-testid="column"]:nth-child(3) {{ flex-grow:4.6 !important; }}

        .st-key-row_total [data-testid="column"],
        .st-key-row_domino [data-testid="column"] {{ flex-grow:1 !important; }}

        .st-key-row_bottom [data-testid="column"] {{ flex-grow:1 !important; }}
        .st-key-row_bottom [data-testid="column"]:nth-child(4),
        .st-key-row_bottom [data-testid="column"]:nth-child(5) {{ flex-grow:3 !important; }}

        @media (max-width: 900px) {{
            .block-container {{
                width:100% !important; max-width:100% !important;
                padding:.28rem .28rem .38rem .28rem !important;
                overflow-x:hidden !important;
            }}
            html, body, .stApp, [data-testid="stAppViewContainer"] {{
                width:100% !important; max-width:100% !important; overflow-x:hidden !important;
            }}

            /* 모바일에서는 실제 화면의 짧은 변(vmin)을 기준으로 글자 크기를 정해
               가로모드에서도 금액 숫자가 카드 밖으로 잘리지 않게 합니다. */
            .top-title {{ font-size:clamp(15px, 4.1vmin, 24px) !important; white-space:nowrap; }}
            .metric-card {{
                height:56px !important; min-height:56px !important; max-height:56px !important;
                padding:6px 7px !important; border-radius:8px !important; overflow:hidden !important;
            }}
            .metric-label {{ font-size:clamp(9px, 2.25vmin, 12px) !important; line-height:1 !important; }}
            .metric-value {{ font-size:clamp(14px, 3.65vmin, 20px) !important; line-height:1.15 !important; letter-spacing:-.02em; }}
            .metric-sub {{ font-size:clamp(8px, 1.8vmin, 10px) !important; line-height:1 !important; }}

            .st-key-top_nav {{ margin-bottom:4px !important; }}
            .st-key-top_nav button {{ min-height:40px !important; height:40px !important; padding:.15rem !important; }}
            .st-key-top_nav [data-testid="column"]:nth-child(2) {{ padding-left:5px !important; padding-right:5px !important; }}

            .st-key-money_row [data-testid="stHorizontalBlock"],
            .st-key-dice_section [data-testid="stHorizontalBlock"] {{ gap:4px !important; column-gap:4px !important; }}
            .st-key-dice_section {{ margin-top:8px !important; margin-bottom:2px !important; }}
            .dice-box {{ height:56px !important; min-height:56px !important; max-height:56px !important; border-radius:8px !important; }}
            .st-key-dice_section .dice-lg {{ width:44px !important; height:44px !important; max-width:44px !important; max-height:44px !important; }}
            .st-key-dice_section button {{ min-height:56px !important; height:56px !important; max-height:56px !important; font-size:clamp(12px, 3vmin, 17px) !important; padding:.2rem !important; }}
            .result-card {{ font-size:clamp(10px, 2.5vmin, 14px) !important; padding:5px 7px !important; }}
            .compact-caption {{ font-size:clamp(8px, 1.9vmin, 11px) !important; }}

            .st-key-game_board {{
                min-width:0 !important; width:100% !important; max-width:100% !important;
                overflow:hidden !important; margin-top:4px !important;
            }}
            .st-key-game_board [class*="st-key-row_"] {{
                width:100% !important; max-width:100% !important; overflow:hidden !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )



# ============================================================
# Dialogs
# ============================================================
@st.dialog("게임 방법")
def game_help_dialog() -> None:
    st.markdown(
        """
        1. 원하는 베팅 구역을 눌러 금액을 설정합니다.  
        2. 여러 구역에 동시에 베팅할 수 있지만 **한 판 전체 베팅 합계는 100,000원**까지입니다.  
        3. **굴리기**를 누르면 주사위 3개가 굴러가고 자동으로 정산됩니다.  
        4. 당첨 구역은 민트색으로 표시됩니다. 내가 베팅한 구역까지 당첨되면 조금 더 진한 민트색으로 표시됩니다.  
        5. `이 금액 계속 베팅하기`를 켜면 정산 후 같은 금액이 다음 판에도 자동으로 올라갑니다.  
        6. 브라우저 새로고침이나 세션 종료 시 현재 플레이 정보가 초기화될 수 있으므로 필요한 경우 저장 버튼으로 로그를 내려받으세요.
        """
    )


@st.dialog("베팅 정보")
def bet_help_dialog(bet_id: str) -> None:
    info = BET_DEFINITIONS[bet_id]
    stats = bet_stats(bet_id)
    st.subheader(info["name"])
    st.write(info["detail"])
    st.markdown(
        f"""
        - **당첨확률:** {fmt_pct(stats['probability'])}
        - **배당:** {stats['odds_text']}
        - **1만원 당첨 시 총 반환:** {stats['return_amount']}
        - **1만원 기대 반환액:** {fmt_money(round(stats['expected_return']))}
        - **평균 손실률:** {fmt_pct(stats['house_edge'])}
        """
    )
    if info.get("help_note"):
        st.info(info["help_note"])


@st.dialog("베팅 설정")
def bet_dialog(bet_id: str) -> None:
    info = BET_DEFINITIONS[bet_id]
    amount_key = f"tmp_amount_{bet_id}"
    repeat_key = f"tmp_repeat_{bet_id}"

    st.subheader(info["name"])
    st.caption(info["detail"])

    st.number_input(
        "베팅 금액",
        min_value=MIN_MONEY_UNIT,
        max_value=MAX_TOTAL_BET,
        step=MIN_MONEY_UNIT,
        key=amount_key,
        format="%d",
    )

    def adjust(delta: int) -> None:
        now = int(st.session_state[amount_key])
        st.session_state[amount_key] = min(MAX_TOTAL_BET, max(MIN_MONEY_UNIT, now + delta))

    c1, c2, c3, c4 = st.columns(4)
    c1.button("-10,000", key=f"minus10_{bet_id}", use_container_width=True, on_click=adjust, args=(-10_000,))
    c2.button("-1,000", key=f"minus1_{bet_id}", use_container_width=True, on_click=adjust, args=(-1_000,))
    c3.button("+1,000", key=f"plus1_{bet_id}", use_container_width=True, on_click=adjust, args=(1_000,))
    c4.button("+10,000", key=f"plus10_{bet_id}", use_container_width=True, on_click=adjust, args=(10_000,))

    st.toggle("이 금액 계속 베팅하기", key=repeat_key)

    current_total_excluding = total_current_bet() - int(st.session_state.bets.get(bet_id, 0))
    max_by_table = MAX_TOTAL_BET - current_total_excluding
    max_by_cash = st.session_state.bankroll + int(st.session_state.bets.get(bet_id, 0))
    st.caption(
        f"현재 전체 베팅 {total_current_bet():,}원 / 100,000원 · "
        f"이 구역에서 설정 가능한 최대 약 {min(max_by_table, max_by_cash):,}원"
    )

    left, mid, right = st.columns([1, 1, 1])
    if left.button("베팅 취소", key=f"cancel_bet_{bet_id}", use_container_width=True):
        clear_bet(bet_id)
        st.session_state.pop(amount_key, None)
        st.session_state.pop(repeat_key, None)
        st.rerun()

    if right.button("확인", key=f"confirm_bet_{bet_id}", type="primary", use_container_width=True):
        amount = int(st.session_state[amount_key])
        repeat = bool(st.session_state[repeat_key])
        ok, message = apply_bet(bet_id, amount, repeat)
        if ok:
            st.session_state.pop(amount_key, None)
            st.session_state.pop(repeat_key, None)
            st.rerun()
        else:
            st.error(message)


@st.dialog("메인화면으로 돌아가기")
def back_dialog() -> None:
    st.warning("지금까지의 게임 정보는 저장되지 않습니다. 돌아가시겠습니까?")
    yes, no = st.columns(2)
    if yes.button("예", key="back_yes", type="primary", use_container_width=True):
        st.session_state.page = "main"
        st.session_state.bets = {}
        st.session_state.repeat_bets = set()
        st.session_state.logs = []
        st.session_state.last_winners = set()
        st.session_state.notice = ""
        st.rerun()
    if no.button("아니오", key="back_no", use_container_width=True):
        st.rerun()


@st.dialog("플레이 기록 저장")
def save_dialog() -> None:
    st.write("지금 까지 플레이 로그를 저장하시겠습니까?")
    filename = current_time().strftime("%Y.%m.%d.%H%M%S.txt")
    data = build_log_text().encode("utf-8-sig")
    yes, no = st.columns(2)
    yes.download_button(
        "예",
        data=data,
        file_name=filename,
        mime="text/plain",
        use_container_width=True,
        type="primary",
        key="save_yes_download",
        on_click="ignore",
    )
    if no.button("아니오", key="save_no", use_container_width=True):
        st.rerun()


@st.dialog("게임 초기화")
def reset_dialog() -> None:
    st.warning(
        f"현재 플레이 기록과 베팅을 모두 삭제하고 게임 시작 시 설정한 초기 자본금 "
        f"{st.session_state.initial_capital:,}원으로 초기화하시겠습니까?"
    )
    yes, no = st.columns(2)
    if yes.button("예", key="reset_yes", type="primary", use_container_width=True):
        reset_current_game()
        st.rerun()
    if no.button("아니오", key="reset_no", use_container_width=True):
        st.rerun()


@st.dialog("파산")
def bankruptcy_dialog() -> None:
    st.markdown("### 파산하였습니다")
    st.write(f"게임 시작 시 설정한 초기 자본금 **{st.session_state.initial_capital:,}원**으로 다시 시작합니다.")
    left, center, right = st.columns([1, 1.4, 1])
    with center:
        if st.button("OK", key="bankruptcy_ok", type="primary", use_container_width=True):
            reset_current_game()
            st.rerun()


# ============================================================
# UI helpers
# ============================================================
def open_bet_dialog(bet_id: str) -> None:
    amount_key = f"tmp_amount_{bet_id}"
    repeat_key = f"tmp_repeat_{bet_id}"
    st.session_state[amount_key] = int(st.session_state.bets.get(bet_id, DEFAULT_BET))
    st.session_state[repeat_key] = bet_id in st.session_state.repeat_bets
    bet_dialog(bet_id)


def dice_svg(value: int, size_class: str = "dice-sm") -> str:
    """Return a font-independent inline SVG die with fixed black pips for light/dark browser themes."""
    pip_positions = {
        1: [(50, 50)],
        2: [(28, 28), (72, 72)],
        3: [(28, 28), (50, 50), (72, 72)],
        4: [(28, 28), (72, 28), (28, 72), (72, 72)],
        5: [(28, 28), (72, 28), (50, 50), (28, 72), (72, 72)],
        6: [(28, 24), (72, 24), (28, 50), (72, 50), (28, 76), (72, 76)],
    }
    pip_color = "#000000"
    circles = "".join(
        f'<circle cx="{x}" cy="{y}" r="8.5" fill="{pip_color}" />'
        for x, y in pip_positions[value]
    )
    return (
        f'<svg class="dice-svg {size_class}" viewBox="0 0 100 100" aria-hidden="true">'
        '<rect x="4" y="4" width="92" height="92" rx="8" fill="#FFFFFF" stroke="#475569" stroke-width="5"/>'
        f'{circles}</svg>'
    )


def bet_visual_html(bet_id: str) -> str:
    """Build the visible table artwork. The actual click target is a transparent Streamlit button overlay."""
    amount = int(st.session_state.bets.get(bet_id, 0))
    amount_html = f'<div class="bet-amount-chip">{amount // 1000}K</div>' if amount else ""

    if bet_id == "BIG":
        body = '<div class="bigsmall-symbol">大</div><div class="bigsmall-range">11~17</div><div class="bigsmall-en">BIG</div>'
    elif bet_id == "SMALL":
        body = '<div class="bigsmall-symbol">小</div><div class="bigsmall-range">4~10</div><div class="bigsmall-en">SMALL</div>'
    elif bet_id == "EVEN":
        body = '<div class="eo-text">EVEN</div>'
    elif bet_id == "ODD":
        body = '<div class="eo-text">ODD</div>'
    elif bet_id == "ANY_TRIPLE":
        # 현장판처럼 1·2·3은 윗줄, 4·5·6은 아랫줄.
        # 각 숫자의 Triple도 위 1개 + 아래 2개 삼각 배치로 표현합니다.
        groups = []
        for n in range(1, 7):
            groups.append(
                '<div class="any-item"><div class="any-triple-stack">'
                f'{dice_svg(n, "dice-any")}'
                '<div class="any-triple-bottom">'
                f'{dice_svg(n, "dice-any")}{dice_svg(n, "dice-any")}'
                '</div></div></div>'
            )
        body = f'<div class="any-grid">{"".join(groups)}</div><div class="any-pay">1 WINS 24</div>'
    elif bet_id.startswith("PAIR_"):
        n = int(bet_id.split("_")[1])
        body = f'<div class="dice-row top-dice-row">{dice_svg(n, "dice-sm")}{dice_svg(n, "dice-sm")}</div>'
    elif bet_id.startswith("TRIPLE_"):
        n = int(bet_id.split("_")[1])
        body = (
            '<div class="triple-stack">'
            f'{dice_svg(n, "dice-triple")}'
            '<div class="triple-stack-bottom">'
            f'{dice_svg(n, "dice-triple")}{dice_svg(n, "dice-triple")}'
            '</div></div>'
        )
    elif bet_id.startswith("TOTAL_"):
        n = int(bet_id.split("_")[1])
        body = (
            f'<div class="total-num">{n}</div>'
            '<div class="total-small">1</div>'
            '<div class="total-small total-wins">WINS</div>'
            f'<div class="total-small">{TOTAL_ODDS[n]}</div>'
        )
    elif bet_id.startswith("DOMINO_"):
        _, a, b = bet_id.split("_")
        body = f'<div class="dice-row domino-dice-row">{dice_svg(int(a), "dice-sm")}{dice_svg(int(b), "dice-sm")}</div>'
    elif bet_id.startswith("SINGLE_"):
        n = int(bet_id.split("_")[1])
        body = f'<div class="single-wrap">{dice_svg(n, "dice-lg")}</div>'
    else:
        body = f'<div>{BET_DEFINITIONS[bet_id]["name"]}</div>'

    return f'<div class="bet-visual">{body}{amount_html}</div>'


def bet_cell_state(bet_id: str) -> str:
    active = bet_id in st.session_state.bets
    winner = bet_id in st.session_state.last_winners
    if active and winner:
        return "winactive"
    if winner:
        return "win"
    if active:
        return "active"
    return "normal"


def render_bet_cell(col, bet_id: str, instance: str, height: int = 50) -> None:
    """Render one clickable cell with SVG dice artwork and an independent ? help button."""
    state = bet_cell_state(bet_id)
    cell_key = f"cell_{instance}_state_{state}"

    with col:
        with st.container(key=cell_key):
            with st.container(key=f"visualwrap_{instance}"):
                st.markdown(bet_visual_html(bet_id), unsafe_allow_html=True)
            with st.container(key=f"betwrap_{instance}"):
                if st.button("베팅", key=f"bet_btn_{instance}", type="tertiary", use_container_width=True):
                    open_bet_dialog(bet_id)
            with st.container(key=f"helpwrap_{instance}"):
                if st.button("?", key=f"help_btn_{instance}", use_container_width=True):
                    bet_help_dialog(bet_id)


def render_decor_cell(col, text: str, instance: str, height: int = 50, kind: str = "label") -> None:
    """Render a non-interactive table cell directly inside its column."""
    row_name = instance.split("_", 1)[0]
    row_class = row_name if row_name in {"top", "bigsmall", "total", "domino", "bottom"} else "top"
    kind_class = kind if kind in {"red", "blue", "label"} else "label"
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_text = safe_text.replace("\n", "<br>")
    with col:
        st.markdown(
            f'<div class="decor-cell decor-{kind_class} decor-{row_class}">{safe_text}</div>',
            unsafe_allow_html=True,
        )


def render_table_row(items: list[dict], row_name: str, ratios: list[float] | None = None, height: int = 50) -> None:
    if ratios is None:
        ratios = [1] * len(items)
    # 행별 key를 부여해 모바일에서도 각 열의 flex 비율을 정확히 강제할 수 있게 합니다.
    with st.container(key=f"row_{row_name}"):
        cols = st.columns(ratios, gap=None)
        for idx, (col, item) in enumerate(zip(cols, items)):
            if item["type"] == "bet":
                render_bet_cell(col, item["id"], f"{row_name}_{idx}", height=height)
            else:
                render_decor_cell(
                    col, item.get("text", ""), f"{row_name}_{idx}",
                    height=height, kind=item.get("kind", "label")
                )


def B(bet_id: str) -> dict:
    return {"type": "bet", "id": bet_id}


def D(text: str = "", kind: str = "label") -> dict:
    return {"type": "decor", "text": text, "kind": kind}


def render_dice_card(value: int) -> None:
    # 상단 결과 주사위도 동일한 SVG를 사용해 PC/모바일 폰트 차이로 깨지지 않도록 한다.
    st.markdown(
        f"<div class='dice-box' style='display:flex;align-items:center;justify-content:center;'>{dice_svg(value, 'dice-lg')}</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# 페이지
# ============================================================
def adjust_main_capital(delta: int) -> None:
    current = int(st.session_state.get("main_capital_widget", st.session_state.capital_input))
    new_value = max(MIN_MONEY_UNIT, current + delta)
    new_value = (new_value // MIN_MONEY_UNIT) * MIN_MONEY_UNIT
    st.session_state.main_capital_widget = int(new_value)
    st.session_state.capital_input = int(new_value)


def render_main_page() -> None:
    spacer1, center, spacer2 = st.columns([1, 1.55, 1])
    with center:
        st.markdown(
            """
            <div class="main-card">
                <h1 style="margin:0 0 8px 0;">🎲 다이사이 시뮬레이터</h1>
                <p style="margin:0;">주사위 3개를 이용한 강원랜드 다이사이 규칙 기반 연습용 시뮬레이터입니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if "main_capital_widget" not in st.session_state:
            st.session_state.main_capital_widget = int(st.session_state.capital_input)

        capital = st.number_input(
            "초기 자본금",
            min_value=MIN_MONEY_UNIT,
            step=MIN_MONEY_UNIT,
            format="%d",
            key="main_capital_widget",
        )
        st.session_state.capital_input = int(capital)

        b1, b2, b3, b4 = st.columns(4, gap="small")
        b1.button("-100,000", use_container_width=True, on_click=adjust_main_capital, args=(-100_000,))
        b2.button("-10,000", use_container_width=True, on_click=adjust_main_capital, args=(-10_000,))
        b3.button("+10,000", use_container_width=True, on_click=adjust_main_capital, args=(10_000,))
        b4.button("+100,000", use_container_width=True, on_click=adjust_main_capital, args=(100_000,))

        c1, c2 = st.columns([3, 1])
        if c1.button("시작하기", type="primary", use_container_width=True):
            capital = int(st.session_state.main_capital_widget)
            if capital % MIN_MONEY_UNIT != 0:
                st.error("초기 자본금은 1,000원 단위로 입력해주세요.")
            else:
                start_game(capital)
                st.rerun()
        if c2.button("게임 방법", use_container_width=True):
            game_help_dialog()

        st.caption("※ 실제 금전이 사용되지 않는 연습용 시뮬레이터입니다.")


def render_metric_card(label: str, value: str, sub: str = "") -> None:
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def render_game_page() -> None:
    # 상단 네비게이션 - 모바일에서도 한 줄 비율을 유지
    with st.container(key="top_nav"):
        left, title_col, save_col, reset_col = st.columns([0.55, 7.4, 0.7, 0.7], vertical_alignment="center")
        if left.button("←", key="back_button", help="메인화면으로 돌아가기", use_container_width=True):
            back_dialog()
        title_col.markdown("<div class='top-title'>🎲 다이사이</div>", unsafe_allow_html=True)
        if save_col.button("💾", key="save_button", help="플레이 기록 저장", use_container_width=True):
            save_dialog()
        if reset_col.button("↻", key="reset_button", help="자본금/게임 기록 초기화", use_container_width=True):
            reset_dialog()

    # 정산 결과 총자산이 0원이면 즉시 파산 안내를 띄웁니다.
    if st.session_state.get("bankrupt_pending", False):
        bankruptcy_dialog()

    # 자금 상태 - 모바일에서도 3칸을 한 줄에 유지하되 글자가 잘리지 않도록 고정
    with st.container(key="money_row"):
        m1, m2, m3 = st.columns(3, gap="small")
        with m1:
            render_metric_card("초기 자본금", fmt_money(st.session_state.initial_capital))
        with m2:
            render_metric_card("보유금액", fmt_money(st.session_state.bankroll))
        with m3:
            render_metric_card("현재 베팅", fmt_money(total_current_bet()), f"상한 {MAX_TOTAL_BET:,}원")

    # 주사위 + 굴리기 : 자금 카드와 10px 간격을 두어 별도 영역처럼 보이게 함
    with st.container(key="dice_section"):
        d1, d2, d3, roll_col = st.columns([1, 1, 1, 1.05], gap="small", vertical_alignment="center")
        with d1:
            render_dice_card(st.session_state.dice[0])
        with d2:
            render_dice_card(st.session_state.dice[1])
        with d3:
            render_dice_card(st.session_state.dice[2])
        with roll_col:
            if st.button("🎲 굴리기", key="roll_button", type="primary", use_container_width=True):
                roll_dice_and_settle()
                st.rerun()

    if st.session_state.game_no > 0:
        total = sum(st.session_state.dice)
        profit = st.session_state.last_round_profit or 0
        profit_text = f"{profit:+,}원" if st.session_state.last_round_profit is not None else "-"
        st.markdown(
            f"""
            <div class="result-card">
              <b>게임 {st.session_state.game_no}</b> ·
              결과 <b>{st.session_state.dice[0]} · {st.session_state.dice[1]} · {st.session_state.dice[2]}</b> ·
              합계 <b>{total}</b> · 이번 판 순손익 <b>{profit_text}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="result-card">베팅 구역을 선택하거나, 베팅 없이 바로 <b>굴리기</b>를 눌러도 됩니다.</div>', unsafe_allow_html=True)

    if st.session_state.notice:
        st.warning(st.session_state.notice)

    st.markdown(
        '<div class="compact-caption">브라우저 새로고침 또는 세션 종료 시 플레이 정보가 초기화될 수 있습니다. 필요한 경우 💾 버튼으로 로그를 저장하세요.</div>',
        unsafe_allow_html=True,
    )

    # 실제 현장 테이블 사진을 배치 도면으로 사용한 5단 구조
    with st.container(key="game_board"):
        # 1단: PAIR 6/5/4 | 구분 | TRIPLE 6/5/4 | 150배 | TRIPLE 3/2/1 | 구분 | PAIR 3/2/1
        render_table_row(
            [
                D("1\nWINS\n8", "blue"), B("PAIR_6"), B("PAIR_5"), B("PAIR_4"), D("", "red"),
                B("TRIPLE_6"), B("TRIPLE_5"), B("TRIPLE_4"), D("1\nWINS\n150", "blue"),
                B("TRIPLE_3"), B("TRIPLE_2"), B("TRIPLE_1"), D("", "red"),
                B("PAIR_3"), B("PAIR_2"), B("PAIR_1"), D("1\nWINS\n8", "blue"),
            ],
            "top",
            ratios=[1.0, .82, .82, .82, .55, .82, .82, .82, 1.0, .82, .82, .82, .55, .82, .82, .82, 1.0],
            height=68,
        )

        # 2단: BIG / SMALL / ANY TRIPLE / BIG / SMALL (실제 판 비율)
        render_table_row(
            [B("BIG"), B("SMALL"), B("ANY_TRIPLE"), B("BIG"), B("SMALL")],
            "bigsmall",
            ratios=[2.5, 2.5, 4.6, 2.5, 2.5],
            height=124,
        )

        # 3단: TOTAL 17 → 4
        render_table_row(
            [B(f"TOTAL_{n}") for n in range(17, 3, -1)],
            "total",
            ratios=[1] * 14,
            height=128,
        )

        # 4단: DOMINO - 실제 판처럼 양 끝에 5:1 안내 칸을 두고 15조합 배치
        domino_ids = [
            "DOMINO_5_6", "DOMINO_4_6", "DOMINO_3_6", "DOMINO_2_6", "DOMINO_1_6",
            "DOMINO_4_5", "DOMINO_3_5", "DOMINO_2_5", "DOMINO_1_5",
            "DOMINO_3_4", "DOMINO_2_4", "DOMINO_1_4",
            "DOMINO_2_3", "DOMINO_1_3", "DOMINO_1_2",
        ]
        render_table_row(
            [D("1\nWINS\n5", "blue")] + [B(x) for x in domino_ids] + [D("1\nWINS\n5", "blue")],
            "domino",
            ratios=[1] * 17,
            height=64,
        )

        # 5단: SINGLE 6/5/4 / EVEN / ODD / SINGLE 3/2/1
        render_table_row(
            [B("SINGLE_6"), B("SINGLE_5"), B("SINGLE_4"), B("EVEN"), B("ODD"), B("SINGLE_3"), B("SINGLE_2"), B("SINGLE_1")],
            "bottom",
            ratios=[1, 1, 1, 3.0, 3.0, 1, 1, 1],
            height=112,
        )


# ============================================================
# 실행 (v11 Animation-style full-stage pinch zoom / black pips)
# ============================================================
init_session_state()
inject_css()

if st.session_state.page == "main":
    render_main_page()
else:
    render_game_page()

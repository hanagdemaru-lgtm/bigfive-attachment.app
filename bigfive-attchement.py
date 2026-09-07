import os
import streamlit as st
from supabase import Client, create_client

# --- Supabase 接続設定 ---
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None


supabase = init_supabase()

# ファイルパス設定
BIG5_FILE = r"C:\Python\bigfive\bigfive_shitumon.txt"
AITYAKU_FILE = r"C:\Python\bigfive\aityaku_shitsumon.txt"

# --- 逆転項目の指定 (1から始まる設問番号) ---
BIG5_REVERSE = [1, 6, 7, 8, 9, 11, 20, 24, 25, 28]
AITYAKU_REVERSE = [4, 9, 14, 17, 18, 22, 23, 24, 26]

# --- Big5 因子マッピング (29問用) ---
BIG5_FACTORS = {
    "factor_e": [1, 2, 3, 4, 5],             # 外向性
    "factor_c": [6, 7, 8, 9, 10, 11, 12],    # 勤勉性
    "factor_n": [13, 14, 15, 16, 17],        # 神経質傾向
    "factor_o": [18, 19, 20, 21, 22, 23],    # 開放性
    "factor_a": [24, 25, 26, 27, 28, 29],    # 調和性
}

# 7件法の定義
OPTIONS = [1, 2, 3, 4, 5, 6, 7]
OPTION_LABELS = {
    1: "1: 全く当てはまらない",
    2: "2: 当てはまらない",
    3: "3: どちらかといえば当てはまらない",
    4: "4: どちらともいえない",
    5: "5: どちらかといえば当てはまる",
    6: "6: 当てはまる",
    7: "7: 非常に当てはまる",
}


def load_questions(file_path):
    """テキストファイルから設問リストを取得"""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                return lines
    return []


def calculate_scores(answers):
    """Big5および愛着スタイルの得点計算 (逆転項目処理含む)"""
    processed = {}

    # 1. Big5 逆転項目処理
    for i in range(1, 30):
        val = answers.get(f"b5_q{i}", 4)
        processed[f"b5_q{i}"] = (8 - val) if i in BIG5_REVERSE else val

    # 2. 愛着スタイル 逆転項目処理
    for i in range(1, 28):
        val = answers.get(f"att_q{i}", 4)
        processed[f"att_q{i}"] = (8 - val) if i in AITYAKU_REVERSE else val

    # 3. Big5 5因子スコア算出 (平均値)
    factor_scores = {}
    for factor_key, q_list in BIG5_FACTORS.items():
        vals = [processed[f"b5_q{q}"] for q in q_list if f"b5_q{q}" in processed]
        factor_scores[factor_key] = sum(vals) / len(vals) if vals else 4.0

    # 4. 愛着スタイル (見捨てられ不安・親密性回避) スコア算出
    anxiety_qs = [1, 2, 3, 5, 6, 7, 8, 10, 11, 12, 13]
    avoidance_qs = [
        4, 9, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 23, 24, 25, 26, 27
    ]

    anx_vals = [processed[f"att_q{q}"] for q in anxiety_qs]
    avo_vals = [processed[f"att_q{q}"] for q in avoidance_qs]

    att_anxiety = sum(anx_vals) / len(anx_vals) if anx_vals else 4.0
    att_avoidance = sum(avo_vals) / len(avo_vals) if avo_vals else 4.0

    # 5. 類型判定 (カットオフ値: 4.0)
    if att_anxiety < 4.0 and att_avoidance < 4.0:
        att_type = "安定型"
    elif att_anxiety >= 4.0 and att_avoidance < 4.0:
        att_type = "囚われ型（不安型）"
    elif att_anxiety < 4.0 and att_avoidance >= 4.0:
        att_type = "拒絶・回避型"
    else:
        att_type = "恐れ・回避型"

    # 保存用データの構築
    calculated_data = {}
    calculated_data.update(factor_scores)
    calculated_data.update({
        "att_anxiety": att_anxiety,
        "att_avoidance": att_avoidance,
        "att_type": att_type
    })

    return calculated_data


def save_to_supabase(raw_answers, calculated_data):
    """Supabaseに生の回答データと因子スコアを合わせて保存"""
    if supabase is None:
        return False

    payload = {}
    payload.update(raw_answers)
    payload.update(calculated_data)

    try:
        supabase.table("results").insert(payload).execute()
        return True
    except Exception as e:
        st.error(f"DB保存エラー: {e}")
        return False


def main():
    st.title("パーソナリティ＆愛着スタイル アンケート")
    st.write(
        "以下の質問項目について、あなたに最もあてはまるボタンをそれぞれ選んで回答してください。"
    )

    big5_qs = load_questions(BIG5_FILE)
    aityaku_qs = load_questions(AITYAKU_FILE)

    answers = {}

    with st.form("survey_form"):
        # --- PART 1: Big5 (29問) ---
        st.subheader("PART 1: Big5 性格特性 (全29問)")
        if big5_qs:
            for i, q_text in enumerate(big5_qs, 1):
                answers[f"b5_q{i}"] = st.radio(
                    label=f"Q{i}. {q_text}",
                    options=OPTIONS,
                    format_func=lambda x: OPTION_LABELS[x],
                    index=3,  # 初期値: 4（どちらともいえない）
                    horizontal=True,
                    key=f"b5_{i}",
                )
        else:
            st.warning(f"Big5の質問ファイルが見つかりません: {BIG5_FILE}")

        st.write("---")

        # --- PART 2: 愛着スタイル (27問) ---
        st.subheader("PART 2: 対人関係・愛着スタイル (全27問)")
        if aityaku_qs:
            for i, q_text in enumerate(aityaku_qs, 1):
                answers[f"att_q{i}"] = st.radio(
                    label=f"Q{i}. {q_text}",
                    options=OPTIONS,
                    format_func=lambda x: OPTION_LABELS[x],
                    index=3,  # 初期値: 4（どちらともいえない）
                    horizontal=True,
                    key=f"att_{i}",
                )
        else:
            st.warning(
                f"愛着スタイルの質問ファイルが見つかりません: {AITYAKU_FILE}"
            )

        st.write("---")
        submit_btn = st.form_submit_button(
            "回答を送信する", type="primary", use_container_width=True
        )

    # 送信後の処理
    if submit_btn:
        calculated_data = calculate_scores(answers)
        saved = save_to_supabase(answers, calculated_data)
        if saved:
            st.success("回答が正常に提出・保存されました。ご協力ありがとうございました。")
        else:
            st.info("回答が送信されました。（DB未接続またはローカル実行）")


if __name__ == "__main__":
    main()

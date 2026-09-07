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


def save_to_supabase(raw_answers):
    """Supabaseに生の回答データのみを保存"""
    if supabase is None:
        return False

    try:
        supabase.table("results").insert(raw_answers).execute()
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

    # 送信後のデータ保存とメッセージ表示
    if submit_btn:
        saved = save_to_supabase(answers)
        if saved:
            st.success("回答が正常に提出・保存されました。ご協力ありがとうございました。")
        else:
            st.info("回答が送信されました。（DB未接続またはローカル実行）")


if __name__ == "__main__":
    main()
# app.py

import streamlit as st
import spacy
import random

# --- アプリの基本設定 ---
# @st.cache_resource は、時間のかかる処理を一度だけ実行するための「おまじない」です。
@st.cache_resource
def load_spacy_model():
    """spaCyの英語モデルをロードします。"""
    return spacy.load("en_core_web_sm")

# --- クイズを作るための関数（プログラムの部品） ---
def create_interactive_quiz(text: str, num_to_extract: int):
    """入力されたテキストから、クイズの問題を作成します。"""
    nlp = load_spacy_model()
    doc = nlp(text)
    
    candidates = []
    for token in doc:
        if token.is_punct or token.is_space:
            continue
        
        if (token.tag_ in ["WDT", "WP", "WP$"] or
            (token.text.lower() == 'that' and token.dep_ in ['nsubj', 'dobj', 'mark']) or
            token.pos_ == "ADP" or
            token.tag_ == "VBG" or
            (token.pos_ in ["VERB", "ADJ", "ADV"] and len(token.text) > 5)):
            candidates.append(token)

    if len(candidates) < num_to_extract:
        st.warning(f"抜き出し可能な単語が {len(candidates)} 個しかなかったため、問題数を調整しました。")
        num_to_extract = len(candidates)
        if num_to_extract == 0:
            return None, None
    
    extracted_tokens = {t.i: t for t in random.sample(candidates, num_to_extract)}

    problem_parts = []
    last_idx = 0
    for token_index in sorted(extracted_tokens.keys()):
        problem_parts.append(doc[last_idx:token_index].text_with_ws)
        problem_parts.append(token_index)
        last_idx = token_index + 1
    problem_parts.append(doc[last_idx:].text_with_ws)

    return problem_parts, extracted_tokens

# --- ボタンが押されたときの処理 ---
def select_word(word_id: int):
    st.session_state.selected_word = word_id

def place_word(placeholder_id: int):
    if st.session_state.selected_word is not None:
        st.session_state.user_answers[placeholder_id] = st.session_state.selected_word
        st.session_state.word_bank.pop(st.session_state.selected_word)
        st.session_state.selected_word = None

def unplace_word(placeholder_id: int):
    word_id_to_return = st.session_state.user_answers.pop(placeholder_id)
    st.session_state.word_bank[word_id_to_return] = st.session_state.correct_tokens[word_id_to_return]

# --- ここからがアプリの見た目を作る部分 ---
def main():
    st.set_page_config(page_title="英文単語配置テスト", layout="wide")
    st.title("📝 英文単語配置テスト")

    with st.expander("📘 このアプリの使い方", expanded=True):
        st.info("""
            1. 英文と単語数を指定して「テストを生成する」をタップします。
            2. 「単語バンク」から単語を1つタップして選びます。（選んだ単語は青色に変わります）
            3. 文中の正しい場所 `[ ___ ]` をタップすると、単語が配置されます。
            4. 間違えた単語は、もう一度タップすると単語バンクに戻せます。
            5. 全部配置したら「採点する」で答え合わせ！
        """)
    
    st.header("1. テストを作成")
    text_input = st.text_area("ここに英文を入力してください:", "The book which I bought yesterday is very interesting.", height=100)
    num_to_extract = st.number_input("抜き出す単語の数:", min_value=1, max_value=20, value=3)

    if st.button("テストを生成する", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        problem_parts, correct_tokens = create_interactive_quiz(text_input, num_to_extract)
        if problem_parts and correct_tokens:
            st.session_state.quiz_started = True
            st.session_state.problem_parts = problem_parts
            st.session_state.correct_tokens = correct_tokens
            st.session_state.word_bank = correct_tokens.copy()
            st.session_state.user_answers = {}
            st.session_state.selected_word = None
            st.session_state.show_results = False

    if st.session_state.get('quiz_started', False):
        st.divider()
        st.header("2. 問題に挑戦！")
        
        if st.session_state.word_bank:
            st.subheader("単語バンク")
            cols = st.columns(len(st.session_state.word_bank) or 1)
            for i, (word_id, token) in enumerate(st.session_state.word_bank.items()):
                btn_type = "primary" if st.session_state.selected_word == word_id else "secondary"
                cols[i].button(token.text, key=f"word_{word_id}", on_click=select_word, args=(word_id,), type=btn_type, use_container_width=True)
        else:
            st.success("すべての単語を配置しました！下の「採点する」ボタンを押してください。")

        st.subheader("問題文")
        # st.columnsを使って、テキストとボタンを横並びにする
        cols = st.columns(len(st.session_state.problem_parts))
        for i, part in enumerate(st.session_state.problem_parts):
            with cols[i]:
                if isinstance(part, str):
                    st.markdown(f"<div style='margin-top: 0.5rem;'>{part}</div>", unsafe_allow_html=True)
                else:
                    placeholder_id = part
                    if placeholder_id in st.session_state.user_answers:
                        word_id = st.session_state.user_answers[placeholder_id]
                        st.button(f"**{st.session_state.correct_tokens[word_id].text}**", key=f"placed_{placeholder_id}", on_click=unplace_word, args=(placeholder_id,))
                    else:
                        st.button("[&nbsp;&nbsp;]", key=f"placeholder_{placeholder_id}", on_click=place_word, args=(placeholder_id,), disabled=(st.session_state.selected_word is None))

        st.divider()
        if not st.session_state.word_bank:
            if st.button("採点する", type="primary", use_container_width=True):
                st.session_state.show_results = True

        if st.session_state.get('show_results', False):
            st.header("3. 採点結果")
            correct_count = 0
            total = len(st.session_state.correct_tokens)
            
            for placeholder_id, correct_token in st.session_state.correct_tokens.items():
                if st.session_state.user_answers.get(placeholder_id) == placeholder_id:
                    correct_count += 1
            
            st.subheader(f"正解率: {correct_count} / {total}")
            if correct_count == total:
                st.balloons()
                st.success("🎉 パーフェクト！おめでとうございます！")
            else:
                st.warning("間違えたところを確認してみましょう！")

if __name__ == "__main__":
    main()
import streamlit as st
import random
import re
from google import genai
import ast # Geminiのレスポンス（リスト形式の文字列）をPythonリストに変換するために必要

st.set_page_config(page_title="高校生向け 英語 文法/語彙テスト", layout="wide")
st.title("🎓 英語の文法・語彙復習テスト (Gemini AI利用)")
st.subheader("抜粋された文法的に重要な語句を正しい位置に戻すテストです。")

# --- 初期化 ---
if 'test_started' not in st.session_state:
    st.session_state.test_started = False
if 'score' not in st.session_state:
    st.session_state.score = None
    
# --- Gemini APIとの連携関数 ---

def get_word_info_from_gemini(text, num_words):
    """
    Gemini APIを使用して、文章から重要な単語を抽出し、シャッフルされたリストと元の単語の位置を生成する。
    """
    
    # 1. APIキーの取得とクライアント初期化
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Gemini APIキーが設定されていません。サイドバーの設定手順を確認してください。")
        return [], []
        
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Geminiクライアントの初期化に失敗しました: {e}")
        return [], []

    # 2. プロンプト作成
    # Geminiに対し、Pythonのリスト形式で単語を返すように明確に指示します。
    prompt = (
        f"以下の英文から、高校生レベルで文法的に重要な語（関係代名詞、分詞、高難度語彙など）を正確に{num_words}個、"
        f"**他の文字を含めずに**Pythonのリスト形式（例: ['word1', 'word2', 'word3']）で抜き出して提供してください。\n\n"
        f"英文: '{text}'"
    )

    # 3. APIの呼び出し
    try:
        with st.spinner("Gemini AIが重要な単語を選定中です..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt
            )
        response_text = response.text.strip()
        
    except Exception as e:
        st.error(f"Gemini APIの呼び出し中にエラーが発生しました: {e}")
        return [], []
    
    # 4. レスポンスの解析
    try:
        # APIのレスポンス（['word1', 'word2']という文字列）をPythonのリストに変換
        extracted_words_from_api = ast.literal_eval(response_text)
        if not isinstance(extracted_words_from_api, list):
            raise ValueError("APIレスポンスが有効なリスト形式ではありません。")
    except Exception as e:
        st.warning(f"AIの回答解析に失敗しました。AIの回答: {response_text[:50]}...")
        # フォールバックとして、レスポンス内の単語っぽいものを抽出する処理を入れることも可能
        return [], []

    # 5. 抽出された単語を元の文章の順番に並べ替える
    all_words = re.findall(r'\b\w+\b', text)
    final_extracted_words_original_order = []
    
    # 大文字・小文字を区別しないセットを作成
    api_words_lower = {w.lower() for w in extracted_words_from_api}
    
    for word in all_words:
        if word.lower() in api_words_lower:
             # 一度採用した単語はセットから除外し、重複を避ける（文法語抽出のため）
            if word not in final_extracted_words_original_order:
                final_extracted_words_original_order.append(word)

    # 6. シャッフルされたリストの生成
    shuffled_words = final_extracted_words_original_order[:]
    random.shuffle(shuffled_words)
    
    return final_extracted_words_original_order, shuffled_words

# --- UIとテストロジック（前回のコードとほぼ同じ） ---

def create_gap_text(text, words_to_hide):
    # 穴埋めテキスト生成ロジックは省略（前回のコードと同じ）
    gap_markers = {}
    correct_positions = []
    
    parts = re.split(r'(\b\w+\b)', text)
    gap_count = 0
    new_parts = []
    
    # words_to_hideのコピーを作成し、大文字・小文字を区別せず処理するためのセットを用意
    hide_set = {w.lower() for w in words_to_hide}
    words_hidden_in_order = []
    
    for part in parts:
        is_word = re.match(r'\b\w+\b', part)
        if is_word and part.lower() in hide_set and part not in words_hidden_in_order:
            marker = f'[GAP_{gap_count}]'
            new_parts.append(marker)
            correct_positions.append(part)
            words_hidden_in_order.append(part) 
            gap_count += 1
        else:
            new_parts.append(part)
    
    final_gap_text = "".join(new_parts)
    return final_gap_text, correct_positions

# サイドバーでの設定とテスト開始ボタン
with st.sidebar:
    st.header("設定")
    if "GEMINI_API_KEY" not in st.secrets:
         st.error("🔑 必須: Streamlit SecretsにGEMINI_API_KEYを設定してください。")
         st.markdown("ローカル (`.streamlit/secrets.toml`) または Streamlit Cloud で設定が必要です。")
         
    num_words_to_extract = st.slider("抜き出す単語の数", min_value=1, max_value=5, value=3)
    
    default_text = (
        "Despite the heavy rain, the students continued their research, "
        "consequently having sophisticated data which was necessary for their report."
    )
    user_input = st.text_area(
        "テスト用の英文を入力してください:", 
        value=default_text, 
        height=150
    )
    
    if st.button("テスト開始 / リセット", type="primary"):
        if "GEMINI_API_KEY" in st.secrets:
            # テストの初期化
            st.session_state.test_started = True
            st.session_state.score = None
            st.session_state.user_answers = {}
            
            # --- Gemini API呼び出し ---
            original_words, st.session_state.shuffled_words = get_word_info_from_gemini(user_input, num_words_to_extract)
            
            if original_words:
                st.session_state.gap_text_display, st.session_state.correct_answers = create_gap_text(
                    user_input, 
                    original_words
                )
                # 穴の数だけ回答用辞書を初期化
                st.session_state.user_answers = {f'main_select_{i}': "" for i in range(len(st.session_state.correct_answers))}
            else:
                st.session_state.test_started = False
                st.warning("単語を抽出できませんでした。英文を見直すか、API設定を確認してください。")

            st.experimental_rerun()


# --- メイン画面でのテスト表示と採点ロジック（省略。前回のコードを流用） ---
if st.session_state.test_started and st.session_state.correct_answers:
    # ... (前回のコードの「メイン画面でのテスト表示」部分をここに挿入) ...
    st.markdown("---")
    st.markdown("### 1. 抜き出された単語")
    st.info(f"使用できる単語: {' / '.join(st.session_state.shuffled_words)}")

    st.markdown("### 2. 穴埋め文章")
    
    num_gaps = len(st.session_state.correct_answers)
    selection_options = [""] + st.session_state.shuffled_words
    displayed_text = st.session_state.gap_text_display
    
    for i in range(num_gaps):
        gap_marker = f'[GAP_{i}]'
        
        parts_before_gap = displayed_text.split(gap_marker, 1)
        
        st.markdown(parts_before_gap[0], unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 10])
        with col1:
             st.markdown(f"**[{i+1}]**")
        with col2:
             # 初期値の設定
             initial_index = 0
             current_answer = st.session_state.user_answers.get(f'main_select_{i}', "")
             try:
                 initial_index = selection_options.index(current_answer)
             except ValueError:
                 initial_index = 0

             selected_word = st.selectbox(
                 "選択", 
                 options=selection_options,
                 key=f'main_select_{i}',
                 index=initial_index,
                 label_visibility='collapsed'
             )
             st.session_state.user_answers[f'main_select_{i}'] = selected_word
             
        if len(parts_before_gap) > 1:
            displayed_text = parts_before_gap[1]

    st.markdown(displayed_text)
    
    st.markdown("---")

    if st.button("採点する", key='score_button'):
        score = 0
        feedback = []
        is_complete = True
        
        for i, correct_word in enumerate(st.session_state.correct_answers):
            user_word = st.session_state.user_answers.get(f'main_select_{i}')
            
            if not user_word:
                feedback.append(f"穴 {i+1} : **未回答**")
                is_complete = False
                continue
                
            if user_word == correct_word:
                score += 1
                feedback.append(f"穴 {i+1} ({correct_word}) : **正解** ✅")
            else:
                feedback.append(f"穴 {i+1} ({user_word}) : **不正解** ❌ (正解: {correct_word})")
        
        st.session_state.score = score
        st.session_state.feedback = feedback
        st.session_state.is_complete = is_complete
        st.experimental_rerun()
        
    if st.session_state.score is not None:
        st.markdown("### 採点結果")
        
        if st.session_state.is_complete:
            st.success(f"あなたのスコア: {st.session_state.score} / {num_gaps} 問正解！")
        else:
            st.warning("未回答の穴があります。")
        
        st.markdown("\n".join(st.session_state.feedback))
        
else:
    st.info("サイドバーに英文を入力し、「テスト開始」ボタンを押してください。")
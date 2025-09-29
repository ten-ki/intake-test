import streamlit as st
import random
import re
from google import genai
import ast

# --- Streamlit UI設定 ---
st.set_page_config(page_title="模擬Intakeテスト", layout="wide")
# タイトルをご要望の「模擬Intakeテスト」に変更
st.title("📄 模擬Intakeテスト (英語 文法・語彙)")
st.subheader("抜粋された語句を正しい位置に戻すテストです。")

# --- 初期化 ---
# アプリ実行時にセッションステートのキーを必ず初期化
if 'test_started' not in st.session_state:
    st.session_state.test_started = False
if 'score' not in st.session_state:
    st.session_state.score = None
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'correct_answers' not in st.session_state:
    st.session_state.correct_answers = []
if 'shuffled_words' not in st.session_state:
    st.session_state.shuffled_words = []


# --- Gemini APIとの連携関数 ---
# ... (get_word_info_from_gemini 関数は前回のコードから変更なし) ...
def get_word_info_from_gemini(text, num_words):
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Gemini APIキーが設定されていません。Streamlit CloudのSecretsを確認してください。")
        return [], []
    
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"❌ Geminiクライアントの初期化に失敗しました: {e}")
        return [], []

    prompt = (
        f"以下の英文から、高校生レベルで文法的に重要な語（関係代名詞、分詞、接続詞、高難度語彙など）を正確に{num_words}個、"
        f"**他の文字を含めずに**Pythonのリスト形式（例: ['word1', 'word2', 'word3']）で抜き出して提供してください。\n\n"
        f"英文: '{text}'"
    )

    try:
        with st.spinner("Gemini AIが重要な単語を選定中です..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt
            )
        response_text = response.text.strip()
        
    except Exception as e:
        st.error(f"❌ Gemini APIの呼び出し中にエラーが発生しました: {e}")
        return [], []
    
    try:
        # バッククォート（`）などが付いていたら除去して解析
        if response_text.startswith('```'):
            response_text = response_text.replace('```python', '').replace('```json', '').replace('```', '').strip()
            
        extracted_words_from_api = ast.literal_eval(response_text)
        if not isinstance(extracted_words_from_api, list):
            raise ValueError("APIレスポンスが有効なリスト形式ではありません。")
    except Exception as e:
        st.warning(f"⚠️ AIの回答解析に失敗しました。AIの回答: {response_text[:50]}... エラー詳細: {e}")
        return [], []

    all_words = re.findall(r'\b\w+\b', text)
    final_extracted_words_original_order = []
    api_words_lower = {w.lower() for w in extracted_words_from_api}
    
    for word in all_words:
        if word.lower() in api_words_lower and word not in final_extracted_words_original_order:
            final_extracted_words_original_order.append(word)

    shuffled_words = final_extracted_words_original_order[:]
    random.shuffle(shuffled_words)
    
    return final_extracted_words_original_order, shuffled_words


# --- 穴埋めテキスト生成ロジック ---
# ... (create_gap_text 関数は前回のコードから変更なし) ...
def create_gap_text(text, words_to_hide):
    correct_positions = []
    parts = re.split(r'(\b\w+\b)', text)
    gap_count = 0
    new_parts = []
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

# --- UIとテストの実行 ---
with st.sidebar:
    st.header("設定")
    if "GEMINI_API_KEY" not in st.secrets:
         st.error("🔑 Streamlit CloudでSecretsを設定してください。")
         
    # デフォルト値を15に変更
    num_words_to_extract = st.slider("抜き出す単語の数 (難易度調整)", min_value=1, max_value=25, value=15)
    
    # 例文を空欄に変更
    user_input = st.text_area(
        "テスト用の英文を入力してください:", 
        value="", # 例文を削除
        height=150
    )
    
    # テスト開始ボタン
    if st.button("テスト開始 / リセット", type="primary"):
        if not user_input.strip():
            st.warning("英文を入力してください。")
        elif "GEMINI_API_KEY" in st.secrets:
            # 1. 状態をリセット
            st.session_state.test_started = False
            st.session_state.score = None
            st.session_state.user_answers = {}
            st.session_state.correct_answers = []
            st.session_state.shuffled_words = []
            
            # 2. Gemini API呼び出し
            original_words, shuffled_words = get_word_info_from_gemini(user_input, num_words_to_extract)
            
            # 3. 成功した場合のみ状態を更新し、rerunする
            if original_words:
                st.session_state.test_started = True
                st.session_state.shuffled_words = shuffled_words
                st.session_state.gap_text_display, st.session_state.correct_answers = create_gap_text(
                    user_input, 
                    original_words
                )
                num_gaps = len(st.session_state.correct_answers)
                st.session_state.user_answers = {f'main_select_{i}': "" for i in range(num_gaps)}
                
                # 成功した時のみrerunを呼ぶ
                st.experimental_rerun()
            else:
                 # 失敗した場合は、エラーメッセージを表示し、rerunは呼ばない
                 pass


# --- メイン画面でのテスト表示と採点 ---
# st.session_state.test_started と st.session_state.correct_answers が確実に存在する場合のみ実行
if st.session_state.test_started and st.session_state.correct_answers:
    
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
             current_answer = st.session_state.user_answers.get(f'main_select_{i}', "")
             initial_index = selection_options.index(current_answer) if current_answer in selection_options else 0
             
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
        st.experimental_rerun() # 採点結果表示のためにrerun
        
    if st.session_state.score is not None:
        st.markdown("### 採点結果")
        
        if st.session_state.is_complete:
            st.success(f"あなたのスコア: {st.session_state.score} / {num_gaps} 問正解！")
        else:
            st.warning("未回答の穴があります。")
        
        st.markdown("\n".join(st.session_state.feedback))
        
elif st.session_state.test_started == False and st.session_state.correct_answers == []:
     st.info("サイドバーに英文を入力し、「テスト開始」ボタンを押してください。")
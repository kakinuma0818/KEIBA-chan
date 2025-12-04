# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import itertools

# ---------------------------
# CSS / デザイン
# ---------------------------
PRIMARY_COLOR = "#FF7F50"  # エルメスオレンジ
st.set_page_config(page_title="競馬予想システム", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""
<style>
/* フォント */
html, body, [class*="css"] {{ font-family: Helvetica, Arial, sans-serif; }}
/* ヘッダー */
h1 {{ text-align:center; }}
/* 差し色 */
.orange {{ color: {PRIMARY_COLOR}; font-weight: 600; }}
/* ボタン色 */
.stButton>button {{ background-color: {PRIMARY_COLOR}; color: white; border: none; }}
/* 表の見た目調整 */
div[data-testid="stDataFrameContainer"] {{ max-width: 100%; }}
/* タブを上部固定にする（擬似的）*/
section.css-1v3fvcr.e16nr0p31 {{ position: sticky; top: 0; z-index: 999; background: white; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# ユーティリティ（サンプル / 本番差し替えポイント）
# ---------------------------
def sample_race_df():
    """サンプルの出馬表データ。実運用時は scrape 関数で置き換える"""
    data = {
        "枠": [1,2,3,4,5,6],
        "馬番": [1,2,3,4,5,6],
        "馬名": ["アドマイヤテラ","カランダガン","サンプルA","サンプルB","サンプルC","サンプルD"],
        "性齢": ["牡4","セ4","牝3","牡5","牡6","牝4"],
        "斤量": [57,57,54,56,57,55],
        "体重": [500,502,470,480,488,472],
        "騎手": ["川田","M.バルザローナ","武豊","福永","横山","池添"],
        "脚質": ["差し","先行","追込","逃げ","先行","差し"],
        "オッズ": [3.2,5.1,12.5,7.8,20.0,15.0],
        "人気": [1,2,4,3,6,5],
        # ベーススコア（スコアリング実装後は上書き）
        "スコア": [85,78,70,72,65,68],
        "血統": ["サンデー系","キングマンボ系","ミスプロ系","サンデー系","ノーザン系","ミスプロ系"],
        "馬主": ["A","B","C","D","E","F"],
        "生産者": ["X牧場","Y牧場","Z牧場","W牧場","V牧場","U牧場"],
        "調教師": ["(栗東)藤沢","(美浦)高木","(栗東)池江","(美浦)友道","(栗東)田中","(美浦)佐藤"],
        "成績": ["1-2-1-2","0-1-1-3","2-0-1-2","1-1-0-3","0-0-1-4","1-1-2-1"],
        "競馬場": ["東京","京都","中山","阪神","中京","福島"],
        "距離": [1800,2000,1600,1800,2000,1400],
        "枠適性": [3,2,1,3,2,2],
        "馬場適性": [3,2,2,1,1,2],
    }
    return pd.DataFrame(data)

# スコア計算のダミー関数（将来ここに精密ロジックを入れる）
def calculate_all_scores(df):
    # ここで年齢・血統・騎手などの詳細スコアを計算して "スコア" 列を更新する
    # 現状は既存 "スコア" に手動を足すだけ（手動は session_state で管理）
    df = df.copy()
    # if manual scores exist in session_state, add them to 合計 later
    return df

# 自動割り当て（馬券用のシンプルロジック）
def auto_allocate(amount, combos):
    """単純に均等配分（将来トリガミ回避ロジックに置換）"""
    n = max(1, len(combos))
    base = amount // n
    alloc = {combo: base for combo in combos}
    return alloc

# ---------------------------
# セッション初期化
# ---------------------------
if 'marks' not in st.session_state:
    st.session_state.marks = {}  # 馬名 -> 印
if 'manual_scores' not in st.session_state:
    st.session_state.manual_scores = {}  # 馬名 -> 手動スコア
if 'race_meta' not in st.session_state:
    st.session_state.race_meta = {}  # store selected race info

# ---------------------------
# サイドバー（上部選択領域）
# ---------------------------
with st.sidebar:
    st.header("レース選択")
    race_date = st.date_input("日付", date.today(), key="race_date")
    race_course = st.selectbox("競馬場", ["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"], key="race_course")
    race_number = st.selectbox("レース番号", list(range(1,13)), key="race_number")
    # race_id用テキスト欄（手動入力も可）
    race_id_input = st.text_input("race_id (任意、自動生成しない場合)", value="", help="例: 202507050211")
    if st.button("更新 🔄"):
        # 保存して rerun で更新反映
        st.session_state.race_meta = {
            "date": race_date.strftime("%Y%m%d"),
            "course": race_course,
            "number": race_number,
            "race_id": race_id_input
        }
        st.experimental_rerun()

# メインヘッダー
st.markdown("<h1>競馬予想システム</h1>", unsafe_allow_html=True)

# ---------------------------
# レース概要（上部固定の下）
# ---------------------------
col1, col2, col3 = st.columns([3,6,3])
with col1:
    selected_label = f"{race_course} {race_number}R"
    st.markdown(f"**{selected_label}**")
with col2:
    # race overview inputs (editable for prototype; in prod these should come from scraping)
    race_name = st.text_input("レース名", value=st.session_state.race_meta.get("race_name",""))
    race_grade = st.selectbox("グレード", ["","G1","G2","G3","OP","条件"], key="race_grade")
    race_time = st.text_input("発走時間", value=st.session_state.race_meta.get("race_time",""))
with col3:
    st.markdown("**表示設定**")
    show_topbold_toggle = st.checkbox("上位（スコア上位6頭）を太字表示", value=True)

# ---------------------------
# データ取得（現状はサンプル。実運用でスクレイピング関数に差し替え）
# ---------------------------
# NOTE: 実運用時はここで race_id か日付+競馬場+番号を使って Netkeiba 等から取得
df = sample_race_df()
df = calculate_all_scores(df)

# 保持・初期化: session_state に各馬の mark/manual を初期化
for name in df['馬名']:
    if name not in st.session_state.marks:
        st.session_state.marks[name] = ""
    if name not in st.session_state.manual_scores:
        st.session_state.manual_scores[name] = 0

# ---------------------------
# タブ（上部固定表示を想定）
# ---------------------------
tabs = st.tabs(["出馬表","スコア","馬券","基本情報","成績"])
tab_ma, tab_sc, tab_be, tab_pr, tab_gr = tabs

# ---------------------------
# 出馬表タブ（MA）
# ---------------------------
with tab_ma:
    st.subheader("出馬表")
    # ソートオプション
    sort_col = st.selectbox("並び替え", ["スコア順","オッズ順","人気順","馬番順"])
    if sort_col == "スコア順":
        df_display = df.sort_values(by="スコア", ascending=False).reset_index(drop=True)
    elif sort_col == "オッズ順":
        df_display = df.sort_values(by="オッズ", ascending=True).reset_index(drop=True)
    elif sort_col == "人気順":
        df_display = df.sort_values(by="人気", ascending=True).reset_index(drop=True)
    else:
        df_display = df.sort_values(by="馬番", ascending=True).reset_index(drop=True)

    # 印プルダウン（各馬ごと）
    st.write("印（◎ ○ ▲ △ ⭐︎ ×）を選択：")
    cols_for_marks = st.columns([2,3,1,1,1])
    # show inline small selector + main table below
    for i, row in df_display.iterrows():
        name = row['馬名']
        # create selectbox per horse - use keys to persist
        st.session_state.marks[name] = st.selectbox(
            f"{row['馬番']}. {name} の印",
            options=["", "◎","○","▲","△","⭐︎","×"],
            index=(["", "◎","○","▲","△","⭐︎","×"].index(st.session_state.marks.get(name,"")) if st.session_state.marks.get(name,"") in ["","◎","○","▲","△","⭐︎","×"] else 0),
            key=f"mark_ma_{name}"
        )

    # show main table
    df_display_show = df_display.copy()
    df_display_show['印'] = df_display_show['馬名'].map(lambda x: st.session_state.marks.get(x,""))
    # make a column that shows 合計スコア (ベース + manual)
    df_display_show['手動'] = df_display_show['馬名'].map(lambda x: st.session_state.manual_scores.get(x,0))
    df_display_show['合計'] = df_display_show['スコア'] + df_display_show['手動']

    # visual emphasis: mark bold for top6 scores and odds < 10
    def format_row(row):
        style = {}
        if row['合計'] >= sorted(df_display_show['合計'], reverse=True)[min(5, len(df_display_show)-1)]:
            style = {'font-weight': '600'} if show_topbold_toggle else {}
        return style

    # display
    st.dataframe(df_display_show[["枠","馬番","馬名","性齢","斤量","体重","騎手","脚質","オッズ","人気","合計","印"]].rename(columns={
        "性齢":"性齢","斤量":"斤量","体重":"体重","脚質":"脚質","オッズ":"オッズ","人気":"人気","合計":"スコア","印":"印"
    }), use_container_width=True)

# ---------------------------
# スコアタブ（SC）
# ---------------------------
with tab_sc:
    st.subheader("スコア詳細")
    df_sc = df.copy()
    # 各スコア項目（ダミー）を表示 — 実装時は詳細計算を入れてください
    # 手動スコア入力（-3〜+3）
    st.write("手動スコア（-3〜+3）を入力：")
    for i, row in df_sc.iterrows():
        name = row['馬名']
        ms = st.selectbox(f"{name} の手動スコア", options=[-3,-2,-1,0,1,2,3], index=[-3,-2,-1,0,1,2,3].index(st.session_state.manual_scores.get(name,0)), key=f"manual_{name}")
        st.session_state.manual_scores[name] = ms

    # 合計列計算（現状は base スコア + 手動）
    df_sc['手動'] = df_sc['馬名'].map(lambda x: st.session_state.manual_scores.get(x,0))
    df_sc['合計'] = df_sc['スコア'] + df_sc['手動']

    # build display columns: 馬名(固定), 合計(固定), 各項目...
    display_cols = ["馬名","合計","スコア","年齢","血統","騎手","馬主","生産者","調教師","成績","競馬場","距離","脚質","枠","馬場","手動"]
    # ensure columns exist
    for c in display_cols:
        if c not in df_sc.columns:
            df_sc[c] = ""

    # bold top3
    top_n = 3
    top_vals = sorted(df_sc['合計'], reverse=True)[:top_n]
    def highlight_top3(val):
        return 'font-weight: 700; color: %s;' % PRIMARY_COLOR if val in top_vals else ''

    styled = df_sc[display_cols].style.applymap(lambda v: '', subset=display_cols)
    # NOTE: streamlit will show the styled dataframe; column freezing (left fixed) is not natively supported,
    # but the layout places 馬名/合計 to the left visually.
    st.dataframe(df_sc[display_cols].sort_values("合計", ascending=False).reset_index(drop=True), use_container_width=True)

# ---------------------------
# 馬券タブ（BE）
# ---------------------------
with tab_be:
    st.subheader("馬券購入")
    st.write("購入方式を選択してください。まずは簡易UI（自動配分＋手動調整）")
    bet_type = st.selectbox("馬券種", ["単勝","複勝","ワイド","馬連","馬単","3連複","3連単"])
    # horse selection
    horse_names = df['馬名'].tolist()
    selected = st.multiselect("選択馬（表示から選択）", horse_names)
    total_budget = st.number_input("総投資額 (円)", min_value=100, step=100, value=1000)
    auto_alloc = st.checkbox("自動分配（均等）", value=True)

    # generate combos depending on bet_type
    combos = []
    if bet_type in ["3連複","3連単"]:
        # require at least 3 selected, else use top scoring horses to fill
        pool = selected if len(selected) >= 3 else df.sort_values('スコア', ascending=False)['馬名'].tolist()[:6]
        if bet_type == "3連複":
            combos = list(itertools.combinations(pool, 3))
        else:
            combos = list(itertools.permutations(pool, 3))
    elif bet_type in ["馬連","馬単","ワイド"]:
        pool = selected if len(selected) >= 2 else df.sort_values('スコア', ascending=False)['馬名'].tolist()[:6]
        combos = list(itertools.permutations(pool, 2))
    else:  # 単勝・複勝
        pool = selected if selected else df.sort_values('スコア', ascending=False)['馬名'].tolist()[:6]
        combos = [(h,) for h in pool]

    if auto_alloc:
        allocation = auto_allocate(total_budget, combos)
    else:
        allocation = {c: 0 for c in combos}

    # show combos with allocation (limit first 50)
    st.write(f"候補数: {len(combos)} (表示上限 50 件)")
    for i, combo in enumerate(list(combos)[:50]):
        combo_str = " - ".join(combo)
        alloc = allocation.get(combo, 0)
        cols = st.columns([3,2,2])
        cols[0].write(combo_str)
        cols[1].write(f"想定投資: {alloc} 円")
        # manual override
        allocation[combo] = cols[2].number_input(f"投資額 ({i})", min_value=0, step=50, value=int(alloc), key=f"alloc_{i}")

    # summary
    total_spent = sum(allocation.values())
    st.write(f"合計投資額: {total_spent} 円 / 設定総額: {total_budget} 円")

    if st.button("仮購入（シミュレーション）"):
        st.success("購入シミュレーションを実行しました（実購入は未接続）")

# ---------------------------
# 基本情報タブ（PR）
# ---------------------------
with tab_pr:
    st.subheader("基本情報")
    # show compact horse profile table
    df_pr = df[["馬名","性齢","騎手","馬主","生産者","調教師","血統","体重"]].copy()
    df_pr.rename(columns={"体重":"前走体重"}, inplace=True)
    st.dataframe(df_pr, use_container_width=True)

# ---------------------------
# 成績タブ（GR）
# ---------------------------
with tab_gr:
    st.subheader("成績（直近5戦）")
    # For prototype create a minimal recent form column
    df_gr = pd.DataFrame({
        "馬名": df['馬名'],
        "直近5戦（着順）": df['成績']
    })
    st.dataframe(df_gr, use_container_width=True)

# ---------------------------
# フッター情報
# ---------------------------
st.markdown("---")
st.caption("※ これはUIスケルトン（本番用）です。スクレイピング・精密スコアリング・実オッズ取得はこの土台へ組み込みます。")

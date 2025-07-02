import streamlit as st
import pandas as pd
import io
import quantum

# セッションステートの初期化
for key in ("download_template", "editor", "download_edit"):
    st.session_state.setdefault(key, False)

# 表示ボタンと閉じるボタンの設定
def set_state(key: str, value: bool):
    st.session_state[key] = value

def main():
    st.title("上司と部下のマッチング")
    st.write("---")
    token = st.secrets["FIXSTARS_API_KEY"]

    # ── 共通パラメータ入力 ──
    st.markdown("## 詳細設定")
    well_suited_leader = st.radio(
        "リーダー/メンバー相性", ["多様性重視","同一性重視"],
        horizontal=True, key="leader"
    )
    well_suited_member = st.radio(
        "メンバー/メンバー相性", ["多様性重視","同一性重視"],
        horizontal=True, key="member"
    )
    weight_char  = st.slider("性格",  0,100,50, key="char")
    weight_skill = st.slider("スキル", 0,100,50, key="skill")
    weight_pref  = st.slider("社員の希望",  0,100,50, key="pref")

    # タブで画面切り替え
    tab1, tab2 = st.tabs(["ファイルで実行", "サンプルで実行"])

    # ── Tab1: 通常アップロード or サンプル実行 ──
    with tab1:
        # CSVのフォーマットをダウンロード
        col1, col2 = st.columns(2)
        with col1:
            st.button("CSV のフォーマットをダウンロード",
                      on_click=set_state,
                      args=("download_template", True),
                      key="show_template")
        with col2:
            st.button("閉じる", on_click=set_state,
                      args=("download_template", False),
                      key="hide_template")
        
        if st.session_state.download_template:
            # 部署テンプレート
            dept_cols = [
                "部署ID", "部署", "スキル１", "スキル２", "スキル３", "定員人数"
            ]
            df_dept = pd.DataFrame(columns=dept_cols)
            csv_dept = df_dept.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="部署データのテンプレートをダウンロード",
                data=csv_dept,
                file_name="department_template.csv",
                mime="text/csv"
            )

            # 既存社員テンプレート
            mem_cols = [
                "社員番号", "名前", "部署", "リーダー",
                "開放性", "誠実性", "外向性", "協調性", "神経症傾向", 
                "スキル１", "スキル２", "スキル３"
            ]
            df_mem = pd.DataFrame(columns=mem_cols)
            csv_mem = df_mem.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="既存社員データのテンプレートをダウンロード",
                data=csv_mem,
                file_name="member_template.csv",
                mime="text/csv"
            )

            # 新卒社員テンプレート
            emp_cols = [
                "社員番号", "名前", "開放性", "誠実性", "外向性", "協調性",
                "神経症傾向", "スキル１", "スキル２", "スキル３",
                "第一希望", "第二希望", "第三希望"
            ]
            df_emp = pd.DataFrame(columns=emp_cols)
            csv_emp = df_emp.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="新卒社員データのテンプレートをダウンロード",
                data=csv_emp,
                file_name="employee_template.csv",
                mime="text/csv"
            )

        st.write("---")

        # CSVアップロード
        st.info("""
        ⚠ アップロードするCSVファイルの **ファイル名に日本語を使用しないでください**。  
        半角英数字のみを使った名前に変更してください。
        """)
        group_file = st.file_uploader("部署データのCSVをアップロード", type=["csv"])
        member_file = st.file_uploader("既存社員のCSVをアップロード", type=["csv"])
        employee_file = st.file_uploader("新卒社員データのCSVをアップロード", type=["csv"])
        st.write("---")

        # 実行ボタン
        if st.button("最適化を実行"):
            # ファイル未アップロード時の警告
            if group_file is None or member_file is None or employee_file is None:
                st.warning("全てのCSVファイルをアップロードしてください。")
            else:
                run_opt(
                    token,
                    group_file, member_file, employee_file,
                    st.session_state.leader,
                    st.session_state.member,
                    st.session_state.char,
                    st.session_state.skill,
                    st.session_state.pref
                )
        st.write("---")

    # ── Tab2: サンプル編集＆実行 ──
    # セッションに保存領域を用意
    for key in ("saved_dept","saved_mem","saved_emp"):
        if key not in st.session_state:
            st.session_state[key] = None

    with tab2:
        # オリジナル or セッション保存版
        if st.session_state.saved_dept is not None:
            df_dept = st.session_state.saved_dept
        else:
            df_dept = pd.read_csv("sample/部署テンプレート.csv")

        if st.session_state.saved_mem is not None:
            df_mem = st.session_state.saved_mem
        else:
            df_mem = pd.read_csv("sample/既存社員テンプレート.csv")

        if st.session_state.saved_emp is not None:
            df_emp = st.session_state.saved_emp
        else:
            df_emp = pd.read_csv("sample/新卒社員テンプレート.csv")

        edited_dept = df_dept.copy()
        edited_mem  = df_mem.copy()
        edited_emp  = df_emp.copy()

        # 編集を行う
        col1, col2 = st.columns(2)
        with col1:
            st.button("サンプルを編集する", on_click=set_state,
                      args=("editor", True),
                      key="show_editor")
        with col2:
            st.button("閉じる", on_click=set_state,
                      args=("editor", False),
                      key="close_editor")
        if st.session_state.editor:
            st.markdown("#### 部署サンプル")
            edited_dept = st.data_editor(df_dept, num_rows="dynamic", key="edt_dept")
            st.markdown("#### 既存社員サンプル")
            edited_mem  = st.data_editor(df_mem,  num_rows="dynamic", key="edt_mem")
            st.markdown("#### 新卒社員サンプル")
            edited_emp  = st.data_editor(df_emp,  num_rows="dynamic", key="edt_emp")

            # 保存ボタン
            if st.button("保存する", key="save_edited"):
                # session_state から取り出して sample フォルダへ上書き
                st.session_state.saved_dept = edited_dept.copy()
                st.session_state.saved_mem  = edited_mem.copy()
                st.session_state.saved_emp  = edited_emp.copy()
                st.success("変更が完了しました")
        st.write("---")

        # 編集結果をダウンロード
        col3, col4 = st.columns(2)
        with col3:
            st.button("編集したサンプルをダウンロード", on_click=set_state,
                      args=("download_edit", True),
                      key="show_edit")
        with col4:
            st.button("閉じる", on_click=set_state,
                      args=("download_edit", False),
                      key="close_edit")
        if st.session_state.download_edit:
            csv1 = edited_dept.to_csv(index=False).encode("utf-8-sig")
            st.download_button("部署CSVダウンロード", data=csv1, file_name="edited_department_data.csv")
            csv2 = edited_mem.to_csv(index=False).encode("utf-8-sig")
            st.download_button("既存社員CSVダウンロード", data=csv2, file_name="edited_member_data.csv")
            csv3 = edited_emp.to_csv(index=False).encode("utf-8-sig")
            st.download_button("新卒CSVダウンロード", data=csv3, file_name="edited_employee_data.csv")
        st.write("---")


        # サンプルの実行
        if st.button("最適化を実行", key="run_edt"):
            # DataFrame → CSV text → StringIO
            def to_buf(df):
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                buf.seek(0)
                return buf
            buf_dept = to_buf(st.session_state.saved_dept if st.session_state.saved_dept is not None else df_dept)
            buf_mem  = to_buf(st.session_state.saved_mem  if st.session_state.saved_mem  is not None else df_mem)
            buf_emp  = to_buf(st.session_state.saved_emp  if st.session_state.saved_emp  is not None else df_emp)
            run_opt(
                token,
                buf_dept, buf_mem, buf_emp,
                st.session_state.leader,
                st.session_state.member,
                st.session_state.char,
                st.session_state.skill,
                st.session_state.pref
            )
        st.write("---")

def run_opt(token, group_file, member_file, employee_file,
            well_suited_leader, well_suited_member,
            weight_char, weight_skill, weight_pref):
    """quantum.optimize を呼び出して結果表示"""
    try:
        assign_df, dept_comp_all, dept_skill, ratio_fig = quantum.optimize(
            token,
            group_file, member_file, employee_file,
            well_suited_leader, well_suited_member,
            weight_char, weight_skill, weight_pref
        )
        st.success("最適化完了")
        st.dataframe(assign_df)

        st.markdown("### 希望達成率")
        st.plotly_chart(ratio_fig, use_container_width=True)

        st.markdown("### 部署別 相性")
        for grp, mat in dept_comp_all.items():
            st.markdown(f"**{grp}**")
            styled_mat = mat.style.applymap(color_map)  # ここでスタイル付与
            st.dataframe(styled_mat)

        st.markdown("### 部署別 スキル要件と配属新卒スキル")
        for grp, df in dept_skill.items():
            st.markdown(f"{grp}")
            st.dataframe(df)
    except Exception as e:
        st.error(f"量子アニーリング実行中にエラーが発生しました: {e}")

# カラーマッピング用の関数
def color_map(val):
    try:
        val = int(val)  # 文字列でも数値化
        if val == 0 or val == 1:
            return 'background-color: #FFCCCC'
        elif 2 <= val <= 5:
            # 緑色濃淡計算（2〜5の範囲でグラデーション）
            scale = (val - 2) / (5 - 2)  # 0.0 ～ 1.0
            base = 230  # 最も薄い緑
            range_ = 80  # 濃さの変化幅
            green_value = int(base - scale * range_)  # 230 → 150
            color_code = f'background-color: rgb({green_value}, 255, {green_value})'
            return color_code
        else:
            return ''
    except:
        return ''  # 数値変換できなければ無色

if __name__ == '__main__':
    main()

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
    st.title("グループ分け")
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
                file_name="部署テンプレート.csv",
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
                file_name="既存社員テンプレート.csv",
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
                file_name="新卒社員テンプレート.csv",
                mime="text/csv"
            )

        st.write("---")

        # CSVアップロード
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
                try:
                    assign_df, dept_comp_all = quantum.optimize(
                        token,
                        group_file,
                        member_file,
                        employee_file,
                        st.session_state.leader,
                        st.session_state.member,
                        st.session_state.char,
                        st.session_state.skill,
                        st.session_state.pref
                    )
                    st.dataframe(assign_df)
                    
                    for grp in dept_comp_all:
                        st.markdown(f"## {grp} 全体の相性")
                        st.dataframe(dept_comp_all[grp])
                except Exception as e:
                    st.error(f"量子アニーリング実行中にエラーが発生しました: {e}")
        st.write("---")


    with tab2:
        st.markdown("### サンプル CSV を編集")
        # sample フォルダの CSV を読み込み
        edited_dept  = pd.read_csv("sample/部署テンプレート.csv")
        edited_mem   = pd.read_csv("sample/既存社員テンプレート.csv")
        edited_emp   = pd.read_csv("sample/新卒社員テンプレート.csv")

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
            st.markdown("#### 部署テンプレート")
            edited_dept = st.data_editor(edited_dept, num_rows="dynamic", key="edt_dept")
            st.markdown("#### 既存社員テンプレート")
            edited_mem  = st.data_editor(edited_mem,  num_rows="dynamic", key="edt_mem")
            st.markdown("#### 新卒社員テンプレート")
            edited_emp  = st.data_editor(edited_emp,  num_rows="dynamic", key="edt_emp")

            # 保存ボタン
            if st.button("保存する", key="save_edited"):
                # session_state から取り出して sample フォルダへ上書き
                edited_dept.to_csv("sample/部署テンプレート.csv",
                                                index=False, encoding="utf-8-sig")
                edited_mem.to_csv("sample/既存社員テンプレート.csv",
                                                index=False, encoding="utf-8-sig")
                edited_emp.to_csv("sample/新卒社員テンプレート.csv",
                                                index=False, encoding="utf-8-sig")
                st.success("sample フォルダ内の CSV を保存しました。")
        st.write("---")

        # 編集結果をダウンロード
        col3, col4 = st.columns(2)
        with col3:
            st.button("編集したCSVをダウンロード", on_click=set_state,
                      args=("download_edit", True),
                      key="show_edit")
        with col4:
            st.button("閉じる", on_click=set_state,
                      args=("download_edit", False),
                      key="close_edit")
        if st.session_state.download_edit:
            csv1 = edited_dept.to_csv(index=False).encode("utf-8-sig")
            st.download_button("部署CSVダウンロード", data=csv1, file_name="編集済み部署.csv")
            csv2 = edited_mem.to_csv(index=False).encode("utf-8-sig")
            st.download_button("既存社員CSVダウンロード", data=csv2, file_name="編集済み既存社員.csv")
            csv3 = edited_emp.to_csv(index=False).encode("utf-8-sig")
            st.download_button("新卒CSVダウンロード", data=csv3, file_name="編集済み新卒社員.csv")
        st.write("---")


        # サンプルの実行
        if st.button("サンプルを実行", key="run_edt"):
            try:
                assign_df, dept_comp_all = quantum.optimize(
                    token,
                    "sample/部署テンプレート.csv",
                    "sample/既存社員テンプレート.csv",
                    "sample/新卒社員テンプレート.csv",
                    st.session_state.leader,
                    st.session_state.member,
                    st.session_state.char,
                    st.session_state.skill,
                    st.session_state.pref
                )
                st.dataframe(assign_df)
                    
                for grp in dept_comp_all:
                    st.markdown(f"## {grp} 全体の相性")
                    st.dataframe(dept_comp_all[grp])
            except Exception as e:
                st.error(f"量子アニーリング実行中にエラーが発生しました: {e}")

if __name__ == '__main__':
    main()

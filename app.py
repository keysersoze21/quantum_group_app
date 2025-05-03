import streamlit as st
import pandas as pd
import quantum

# セッションステートの初期化
if 'download_template' not in st.session_state:
    st.session_state.download_template = False

# 表示ボタンのコールバック
def show_download_template():
    st.session_state.download_template = True

# 閉じるボタンのコールバック
def hide_download_template():
    st.session_state.download_template = False

def main():
    st.title("グループ分け")
    st.write("---")
    token = st.secrets["FIXSTARS_API_KEY"]

    # CSVのフォーマットをダウンロード
    col1, col2 = st.columns(2)
    with col1:
        st.button("CSV のフォーマットをダウンロード", on_click=show_download_template)
    with col2:
        st.button("閉じる", on_click=hide_download_template)
    
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

    # 詳細設定
    st.markdown("### 詳細設定")
    well_suited_leader = st.radio("リーダー/メンバー相性", ("多様性重視", "同一性重視",), horizontal=True)
    well_suited_member = st.radio("メンバー/メンバー相性", ("多様性重視", "同一性重視",), horizontal=True)
    st.write("---")
    st.markdown("### コスト関数重み")
    weight_char = st.slider("性格", 0, 100, 50)
    weight_skill = st.slider("スキル", 0, 100, 50)
    weight_pref = st.slider("社員の希望", 0, 100, 50)
    st.write("---")

    # 実行ボタン
    if st.button("最適化を実行"):
        # ファイル未アップロード時の警告
        if group_file is None or member_file is None or employee_file is None:
            st.warning("全てのCSVファイルをアップロードしてください。")
        else:
            try:
                result_df = quantum.optimize(
                    token,
                    group_file,
                    member_file,
                    employee_file,
                    well_suited_leader,
                    well_suited_member,
                    weight_char,
                    weight_skill,
                    weight_pref,
                )
                st.success("最適化が完了しました。")
                st.dataframe(result_df)
            except Exception as e:
                st.error("量子アニーリングによる最適化の実行に失敗しました。エラーログを確認してください。")

if __name__ == '__main__':
    main()

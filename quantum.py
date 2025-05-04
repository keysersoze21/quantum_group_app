# quantum.py

import pandas as pd
import numpy as np
from amplify import (
    VariableGenerator,
    Poly,
    Model,
    ConstraintList,
    equal_to,
    less_equal,
    sum as amplify_sum,
    solve
)
from amplify.client import FixstarsClient

def optimize(
    token,
    group_file,
    member_file,
    employee_file,
    well_suited_leader,   # "多様性重視" or "同一性重視"
    well_suited_member,   # "多様性重視" or "同一性重視"
    weight_char,          # 性格スコア重み (0–100)
    weight_skill,         # スキルスコア重み (0–100)
    weight_pref,          # 希望スコア重み (0–100)
):
    # 1. データ読み込み
    group_df    = pd.read_csv(group_file)
    member_df   = pd.read_csv(member_file)
    employee_df = pd.read_csv(employee_file)

    # 2. 列抽出（順番固定）
    # 部署CSV: 0:部署ID, 1:部署名, 2-4:スキル１-3, 5:定員人数
    group_ids   = group_df.iloc[:, 0].to_numpy(int)
    group_names = group_df.iloc[:, 1].tolist()
    group_skill = group_df.iloc[:, 2:5].to_numpy(int)
    capacity    = group_df.iloc[:, 5].to_numpy(int)

    # 既存社員CSV: 0:社員番号,1:名前,2:部署名,3:リーダーフラグ,4-8:開放性-神経症傾向,9-11:スキル１-3
    member_dept  = member_df.iloc[:, 2].tolist()
    leader_flag  = member_df.iloc[:, 3].to_numpy(int)
    member_pers  = member_df.iloc[:, 4:9].to_numpy(int)

    # 新卒社員CSV: 0:社員番号,1:名前,2-6:開放性-神経症傾向,7-9:スキル１-3,10-12:第一-第三希望ID
    new_ids      = employee_df.iloc[:, 0].to_numpy(int)
    new_names    = employee_df.iloc[:, 1].tolist()
    new_pers     = employee_df.iloc[:, 2:7].to_numpy(int)
    new_skill    = employee_df.iloc[:, 7:10].to_numpy(int)
    prefs_raw    = employee_df.iloc[:, 10:13].to_numpy(int).tolist()

    n_new    = len(new_ids)
    n_groups = len(group_ids)

    # 既存社員の性格ベクトルを部署ごとにまとめる
    leaders = {
        grp: member_pers[(np.array(member_dept) == grp) & (leader_flag == 1)]
        for grp in group_names
    }
    members = {
        grp: member_pers[(np.array(member_dept) == grp) & (leader_flag == 0)]
        for grp in group_names
    }

    # 3. 変数生成
    gen = VariableGenerator()
    x = gen.array("Binary", shape=(n_new, n_groups))

    # 4. スコア計算
    PREF = {1: 3, 2: 2, 3: 1}
    base_score = np.zeros((n_new, n_groups))
    for i in range(n_new):
        pi = new_pers[i]
        si = new_skill[i]
        prefs = prefs_raw[i]
        for g, (gid, grp) in enumerate(zip(group_ids, group_names)):
            # 性格・スキルスコア (重みが 0 のときはスキップ)
            if weight_char > 0 or weight_skill > 0:
                # リーダー⇔新卒
                L = leaders[grp]
                if L.size:
                    ls = int((L * pi).sum()) if well_suited_leader == "同一性重視" else int(np.logical_xor(L, pi).sum())
                else:
                    ls = 0
                # メンバー⇔新卒
                M = members[grp]
                if M.size:
                    ms = int((M * pi).sum()) if well_suited_member == "同一性重視" else int(np.logical_xor(M, pi).sum())
                else:
                    ms = 0
                personality = ls + ms
                # スキル
                skill_match = int((group_skill[g] * si).sum())
            else:
                personality = 0
                skill_match = 0

            # 希望スコア
            if gid == prefs[0]:
                pf = PREF[1]
            elif gid == prefs[1]:
                pf = PREF[2]
            elif gid == prefs[2]:
                pf = PREF[3]
            else:
                pf = 0

            base_score[i, g] = (
                weight_char  * personality
                + weight_skill * skill_match
                + weight_pref   * pf
            )

    # 5. QUBO モデル構築：Poly を使い定数 0.0 からスタート
    obj = Poly(0.0)
    for i in range(n_new):
        for g in range(n_groups):
            w = base_score[i, g]
            if w:
                obj -= w * x[i][g]   # 最大化 → QUBO では負号をつけ最小化

    # 制約ペナルティ
    P = (weight_char + weight_skill + weight_pref) * 10 + 1
    cons = []
    # 各新卒は必ず 1 部署
    for i in range(n_new):
        cons.append(equal_to(amplify_sum(x[i, :]), 1) * P)
    # 定員超過禁止
    for g in range(n_groups):
        cons.append(less_equal(amplify_sum(x[:, g]), capacity[g]) * P)

    model = Model(obj, ConstraintList(cons))

    # 6. Solve
    client = FixstarsClient()
    client.token = token
    client.parameters.timeout = 1000
    results = solve(model, client)
    sol = results[0]

    # 7. 割当結果出力
    assignment = []
    assigned_idx = []
    for i in range(n_new):
        for g in range(n_groups):
            if sol.values[x[i][g]] == 1:
                assignment.append({"名前": new_names[i], "割り当て部署": group_names[g]})
                assigned_idx.append((i, g))
                break
    assign_df = pd.DataFrame(assignment)

    # 8. 全社員の性格ベクトル辞書
    pers_dict = {}
    # 既存社員を追加
    for _, row in member_df.iterrows():
        name = row.iloc[1]
        pers_dict[name] = row.iloc[4:9].to_numpy(int)
    # 新卒社員を追加
    for i, _ in assigned_idx:
        pers_dict[new_names[i]] = new_pers[i]

    # 9. 全社員の相性行列（comp_all）
    all_names = list(pers_dict.keys())
    Pmat_all = np.stack([pers_dict[n] for n in all_names])
    comp_all = pd.DataFrame(
        Pmat_all.dot(Pmat_all.T),
        index=all_names,
        columns=all_names
    )

    # 10. 各部署ごとに comp_all を切り出す
    dept_comp_all = {}
    for (gid, grp) in zip(group_ids, group_names):
        # その部署の既存社員名
        exist_names = member_df.loc[member_df.iloc[:,2] == gid, member_df.columns[1]].tolist()
        # その部署に配属された新卒社員名
        new_names_in_grp = assign_df.loc[assign_df["割り当て部署"] == grp, "名前"].tolist()
        # 両方を結合
        names_grp = exist_names + new_names_in_grp

        # 切り出し
        if names_grp:
            dept_comp_all[grp] = comp_all.loc[names_grp, names_grp]
        else:
            dept_comp_all[grp] = pd.DataFrame()

    return assign_df, dept_comp_all

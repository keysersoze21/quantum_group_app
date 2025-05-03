import pandas as pd
import numpy as np
from amplify import VariableGenerator, Model, ConstraintList, equal_to, less_equal, sum as amplify_sum, solve
from amplify.client import FixstarsClient

def optimize(
    token,
    group_file,
    member_file,
    employee_file,
    well_suited_leader,  # "多様性重視" or "同一性重視"
    well_suited_member,  # "多様性重視" or "同一性重視"
    weight_char,         # 性格スコア重み (0–100)
    weight_skill,        # スキルスコア重み (0–100)
    weight_pref,         # 希望スコア重み (0–100)
):
    """
    量子アニーリングで新卒社員を各部署に割り当てる。

    部署CSV: 部署ID, 部署名, スキル１, スキル２, スキル３, 定員人数  (6列)
    既存社員CSV: 社員番号, 名前, 部署名, リーダーフラグ, 開放性*5, スキル*3  (12列)
    新卒社員CSV: 社員番号, 名前, 開放性*5, スキル*3, 第一希望ID, 第二希望ID, 第三希望ID  (13列)

    戻り値: pandas.DataFrame(columns=["名前","割り当て部署"])
    """
    # 1. データ読み込み
    group_df    = pd.read_csv(group_file)
    member_df   = pd.read_csv(member_file)
    employee_df = pd.read_csv(employee_file)

    # 2. 列位置による抽出（順番固定）
    # 部署CSV: 0:部署ID, 1:部署名, 2-4:スキル１-3, 5:定員人数
    group_ids   = group_df.iloc[:, 0].to_numpy(dtype=int)
    group_names = group_df.iloc[:, 1].tolist()
    group_skill = group_df.iloc[:, 2:5].to_numpy(dtype=int)
    capacity    = group_df.iloc[:, 5].to_numpy(dtype=int)

    # 既存社員CSV: 0:社員番号, 1:名前, 2:部署名, 3:リーダーフラグ, 4-8:開放性-神経症傾向, 9-11:スキル１-3
    member_dept  = member_df.iloc[:, 2].tolist()
    leader_flag  = member_df.iloc[:, 3].to_numpy(dtype=int)
    member_pers  = member_df.iloc[:, 4:9].to_numpy(dtype=int)

    # 新卒社員CSV: 0:社員番号, 1:名前, 2-6:開放性-神経症傾向, 7-9:スキル１-3, 10-12:第一-第三希望ID
    new_ids      = employee_df.iloc[:, 0].to_numpy(dtype=int)
    new_names    = employee_df.iloc[:, 1].tolist()
    new_pers     = employee_df.iloc[:, 2:7].to_numpy(dtype=int)
    new_skill    = employee_df.iloc[:, 7:10].to_numpy(dtype=int)
    prefs_raw    = employee_df.iloc[:, 10:13].to_numpy(dtype=int).tolist()

    n_new    = len(new_ids)
    n_groups = len(group_ids)

    # 部署ごとの既存リーダー/メンバー性格ベクトル
    leaders = {grp: member_pers[(np.array(member_dept)==grp)&(leader_flag==1)] for grp in group_names}
    members = {grp: member_pers[(np.array(member_dept)==grp)&(leader_flag==0)] for grp in group_names}

    # 3. 変数生成
    gen = VariableGenerator()
    x = gen.array("Binary", shape=(n_new, n_groups))

    # 4. ベーススコア計算
    PREF = {1:3, 2:2, 3:1}
    base_score = np.zeros((n_new, n_groups))
    for i in range(n_new):
        pi = new_pers[i]
        si = new_skill[i]
        prefs = prefs_raw[i]
        for g, (gid, grp) in enumerate(zip(group_ids, group_names)):
            # 性格相性
            L = leaders[grp]; M = members[grp]
            ls = int((L*pi).sum()) if (well_suited_leader=="同一性重視" and L.size) else (int(np.logical_xor(L,pi).sum()) if L.size else 0)
            ms = int((M*pi).sum()) if (well_suited_member=="同一性重視" and M.size) else (int(np.logical_xor(M,pi).sum()) if M.size else 0)
            # スキルスコア
            sscore = int((group_skill[g] * si).sum())
            # 希望スコア (部署ID で比較)
            if gid == prefs[0]:
                pf = PREF[1]
            elif gid == prefs[1]:
                pf = PREF[2]
            elif gid == prefs[2]:
                pf = PREF[3]
            else:
                pf = 0
            base_score[i, g] = weight_char*(ls+ms) + weight_skill*sscore + weight_pref*pf

    # 5. モデル構築
    obj = 0.0
    for i in range(n_new):
        for g in range(n_groups):
            w = float(base_score[i, g])
            if w:
                obj += w * x[i][g]
    # 制約
    P = (weight_char + weight_skill + weight_pref) * 10 + 1
    cons = []
    for i in range(n_new):
        cons.append(equal_to(amplify_sum(x[i, :]), 1) * P)
    for g in range(n_groups):
        cons.append(less_equal(amplify_sum(x[:, g]), int(capacity[g])) * P)
    model = Model(obj, ConstraintList(cons))

    # 6. Solve
    client = FixstarsClient()
    client.token = token
    client.parameters.timeout = 1000
    results = solve(model, client)
    sol = results[0]

    # 7. 結果整形（名前で出力）
    assignment = []
    for i in range(n_new):
        for g in range(n_groups):
            if sol.values[x[i][g]] == 1:
                assignment.append({
                    "名前": new_names[i],
                    "割り当て部署": group_names[g]
                })
                break
    return pd.DataFrame(assignment)

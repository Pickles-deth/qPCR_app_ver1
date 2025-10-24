import streamlit as st
import itertools
import numpy as np
import pandas as pd
from openpyxl import Workbook
from io import BytesIO

# ==============================
# ページ設定
# ==============================
st.set_page_config(page_title="qPCR ΔΔCt最適化ツール", page_icon="🧬", layout="wide")
st.title("🧬 qPCR ΔΔCt 最適化ツール")

st.sidebar.header("⚙️ 設定パネル")
st.markdown("""
### 🧾 使い方
1️⃣ コントロール群（Control）のラベルと ΔCt 値を入力  
2️⃣ 条件群のラベルと ΔCt 値を入力  
3️⃣ 「解析スタート！」ボタンを押すと、SDが最小になるペアリングを探索します。
""")

# ==============================
# コントロール入力
# ==============================
st.sidebar.subheader("① コントロール入力（ΔCt値）")
label_input = st.sidebar.text_input("コントロールのラベル（例：A,B,C,D）", "A,B,C,D")
control_labels = [x.strip() for x in label_input.split(",") if x.strip()]

control_input = st.sidebar.text_area("コントロール ΔCt 値（例：1.0,0.9,1.1,1.0）", "1.0,0.9,1.1,1.0")
controls = [float(x.strip()) for x in control_input.split(",") if x.strip()]

if len(control_labels) != len(controls):
    st.sidebar.error("⚠️ ラベルと値の数が一致していません。")
else:
    st.sidebar.success(f"✅ コントロール数：{len(controls)} サンプル")

# ==============================
# 条件入力
# ==============================
st.subheader("② 条件群の入力（ΔCt値）")
num_conditions = st.sidebar.number_input("条件の数を選択", min_value=1, max_value=10, value=2)
condition_data = {}

cols = st.columns(2)
for i in range(1, num_conditions + 1):
    with cols[(i - 1) % 2]:
        label_txt = st.text_input(f"条件{i} のラベル（例：Cond{i}_A,Cond{i}_B,...）", f"Cond{i}_A,Cond{i}_B,Cond{i}_C,Cond{i}_D", key=f"lab{i}")
        cond_labels = [x.strip() for x in label_txt.split(",") if x.strip()]
        txt = st.text_area(f"条件{i} の ΔCt 値（例：1.2,0.8,1.0,1.1）", key=f"cond{i}")
        if txt:
            vals = [float(x.strip()) for x in txt.split(",") if x.strip()]
            condition_data[f"条件{i}"] = (cond_labels, vals)

# ==============================
# ΔΔCt 最適化関数
# ==============================
def optimize_ddct(controls, cond_vals, cond_labels, control_labels):
    n = len(controls)
    results = []

    for perm in itertools.permutations(range(n)):
        ddcts = [cond_vals[i] - controls[perm[i]] for i in range(n)]
        rel_exp = [(2 ** -x) * 100 for x in ddcts]

        sd_val = np.std(rel_exp, ddof=1)
        mean_val = np.mean(rel_exp)

        mapping = ", ".join([f"{cond_labels[i]}→{control_labels[perm[i]]}" for i in range(n)])

        results.append({
            "mapping": mapping,
            "mean(%)": mean_val,
            "SD(%)": sd_val,
            "ΔΔCt": ";".join([f"{x:.4f}" for x in ddcts]),
            "2^-ΔΔCt×100": ";".join([f"{r:.4f}" for r in rel_exp])
        })

    results.sort(key=lambda x: x["SD(%)"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results

# ==============================
# 解析実行
# ==============================
if st.button("🚀 解析スタート！"):
    if len(control_labels) != len(controls):
        st.error("⚠️ コントロールのラベル数と値の数が一致していません。")
        st.stop()

    n = len(controls)
    wb = Workbook()
    ws = wb.active
    ws.title = "結果"
    ws.append(["条件名", "Rank", "Mapping", "Mean(%)", "SD(%)", "ΔΔCt", "2^-ΔΔCt×100"])

    all_rows_for_display = []

    for cond_name, (cond_labels, cond_vals) in condition_data.items():
        if len(cond_labels) != n or len(cond_vals) != n:
            st.error(f"⚠️ {cond_name} のサンプル数がコントロールと一致していません。")
            st.stop()

        results = optimize_ddct(controls, cond_vals, cond_labels, control_labels)
        for r in results[:10]:
            row = [
                cond_name,
                r["rank"],
                r["mapping"],
                r["mean(%)"],
                r["SD(%)"],
                r["ΔΔCt"],
                r["2^-ΔΔCt×100"]
            ]
            ws.append(row)
            all_rows_for_display.append(row)

    # Excel出力
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # 表示
    df_display = pd.DataFrame(
        all_rows_for_display,
        columns=["条件名", "Rank", "Mapping", "Mean(%)", "SD(%)", "ΔΔCt", "2^-ΔΔCt×100"]
    )

    st.subheader("📋 解析結果（上位10位）")
    st.dataframe(df_display)

    st.success("🎯 解析完了！最適なΔΔCtペアリングをExcelで確認できます👇")
    st.download_button(
        label="📊 Excelファイルをダウンロード",
        data=output,
        file_name="qPCR_ΔΔCt_optimization.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.markdown("<h2 style='text-align:center;'>🎉 解析完了！おつかれさまです 🧬✨</h2>", unsafe_allow_html=True)

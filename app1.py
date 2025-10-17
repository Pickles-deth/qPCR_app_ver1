import streamlit as st
import itertools
import numpy as np
from openpyxl import Workbook
from io import BytesIO
import pandas as pd  # ← 画面表示用に追加

# ==============================
# ページ設定
# ==============================
st.set_page_config(page_title="qPCR最適化ツール", page_icon="🧬", layout="wide")
st.title("🧬 qPCR 最適化ツール")

st.sidebar.header("⚙️ 設定パネル")
st.markdown("""
### 🧾 使い方
1️⃣ コントロール群のラベル（A, B, C, Dなど）と値を入力  
2️⃣ 条件ごとのラベルと値を入力  
3️⃣ 「解析スタート！」ボタンを押すだけ！
""")

# ==============================
# コントロール入力
# ==============================
st.sidebar.subheader("① コントロール入力")
label_input = st.sidebar.text_input("コントロールのラベルをカンマ区切りで入力（例：A,B,C,D）", "A,B,C,D")
control_labels = [x.strip() for x in label_input.split(",") if x.strip()]

control_input = st.sidebar.text_area("コントロール値をカンマ区切りで入力（例：1.0, 0.9, 1.1, 1.0）", "1.0, 0.9, 1.1, 1.0")
controls = [float(x.strip()) for x in control_input.split(",") if x.strip()]

if control_labels and controls:
    if len(control_labels) != len(controls):
        st.sidebar.error("⚠️ ラベルと値の数が一致していません。")
    else:
        st.sidebar.success(f"✅ コントロール数：{len(controls)} サンプル")
else:
    st.sidebar.warning("⚠️ コントロールラベルと値を入力してください")

# ==============================
# 条件入力
# ==============================
st.subheader("② 条件群を入力")
num_conditions = st.sidebar.number_input("条件の数を選択", min_value=1, max_value=10, value=2)
condition_data = {}

cols = st.columns(2)
for i in range(1, num_conditions + 1):
    with cols[(i - 1) % 2]:
        label_txt = st.text_input(f"条件{i} のラベル名（例：Cond{i}_A,Cond{i}_B,...）", f"Cond{i}_A,Cond{i}_B,Cond{i}_C,Cond{i}_D", key=f"lab{i}")
        cond_labels = [x.strip() for x in label_txt.split(",") if x.strip()]
        txt = st.text_area(f"条件{i} の値を入力", placeholder="例: 1.2, 0.8, 1.0, 1.1", key=f"cond{i}")
        if txt:
            vals = [float(x.strip()) for x in txt.split(",") if x.strip()]
            condition_data[f"条件{i}"] = (cond_labels, vals)

# ==============================
# 解析処理
# ==============================
if st.button("🚀 解析スタート！"):
    if not controls or not condition_data:
        st.error("⚠️ コントロールと条件の両方を入力してください。")
    elif len(control_labels) != len(controls):
        st.error("⚠️ コントロールラベルと値の数が一致していません。")
    else:
        n = len(controls)
        results = []

        for cond_name, (cond_labels, cond_vals) in condition_data.items():
            if len(cond_vals) != n or len(cond_labels) != n:
                st.error(f"⚠️ {cond_name} のサンプル数またはラベル数がコントロールと一致していません。")
                st.stop()

            all_results = []
            for perm in itertools.permutations(range(n)):
                diffs = [cond_vals[i] - controls[perm[i]] for i in range(n)]
                transformed = [(2 ** -d) * 100 for d in diffs]
                mean_val = np.mean(transformed)
                sd_val = np.std(transformed, ddof=1)

                mapping = ", ".join([f"{cond_labels[i]}→{control_labels[perm[i]]}" for i in range(n)])
                diffs_str = ";".join([f"{d:.4f}" for d in diffs])
                trans_str = ";".join([f"{t:.6f}" for t in transformed])

                all_results.append({
                    "rank": None,
                    "mapping": mapping,
                    "mean": mean_val,
                    "sd": sd_val,
                    "transformed": trans_str,
                    "diffs": diffs_str
                })

            # SDでソート
            all_results.sort(key=lambda x: x["sd"])
            for idx, r in enumerate(all_results):
                r["rank"] = idx + 1
            results.append((cond_name, all_results))

        # ==============================
        # Excel出力と画面表示
        # ==============================
        wb = Workbook()
        ws = wb.active
        ws.title = "結果"
        ws.append(["条件名", "Rank", "Mapping", "Mean(2^-diff×100)", "SD(2^-diff×100)", "Transformed", "Diffs"])

        all_rows_for_display = []

        for cond_name, all_results in results:
            for r in all_results[:10]:  # 上位10位まで
                row = [
                    cond_name,
                    r["rank"],
                    r["mapping"],
                    r["mean"],
                    r["sd"],
                    r["transformed"],
                    r["diffs"]
                ]
                ws.append(row)
                all_rows_for_display.append(row)

        # Excel保存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Streamlit画面に表示
        df_display = pd.DataFrame(
            all_rows_for_display,
            columns=["条件名", "Rank", "Mapping", "Mean(2^-diff×100)", "SD(2^-diff×100)", "Transformed", "Diffs"]
        )
        st.subheader("📋 解析結果（上位10位）")
        st.dataframe(df_display)

        # Excelダウンロード
        st.success("🎯 解析完了！Excelをダウンロードできます👇")
        st.download_button(
            label="📊 Excelファイルをダウンロード",
            data=output,
            file_name="qPCR_results_detailed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 🎉 完了メッセージ
        st.markdown("---")
        st.markdown("<h2 style='text-align:center;'>🎉 ひゃっほい！解析おつかれんこん 🍠✨</h2>", unsafe_allow_html=True)

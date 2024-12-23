import streamlit as st
import pandas as pd
import os

# -----------------------
# 常量配置
# -----------------------
TASKS_FILE = "merge_jian_fan_freq_lt100_20241223_anno.csv"       # 原始数据，只读，不回写
PROGRESS_FILE = "progress.csv"  # 标注进度写入这里

# -----------------------
# 辅助函数
# -----------------------
def load_tasks():
    """
    读取 tasks.csv（只读），要求包含列: [原形, 校对前, 校对后, 候选项]
    """
    if not os.path.exists(TASKS_FILE):
        st.error(f"未找到原始任务文件：{TASKS_FILE}")
        st.stop()
    df = pd.read_csv(TASKS_FILE)
    for col in ["原形", "校对前", "校对后", "候选项"]:
        if col not in df.columns:
            st.error(f"{TASKS_FILE} 缺少必要列：{col}")
            st.stop()
    return df

def load_progress():
    """
    如果 progress.csv 存在，则读取并返回；
    否则用 tasks.csv 的结构创建一份 progress.csv，并将「校对后」置空。
    """
    if os.path.exists(PROGRESS_FILE):
        df_progress = pd.read_csv(PROGRESS_FILE)
        # 若缺少必需列，则补齐
        for col in ["原形", "校对前", "校对后", "候选项"]:
            if col not in df_progress.columns:
                df_progress[col] = ""
        return df_progress
    else:
        df_tasks = load_tasks()
        # 复制后将“校对后”清空，以防万一
        df_tasks["校对后"] = ""
        df_tasks.to_csv(PROGRESS_FILE, index=False, encoding="utf-8")
        return df_tasks

def save_progress(df):
    """
    将标注进度写回 progress.csv
    """
    df.to_csv(PROGRESS_FILE, index=False, encoding="utf-8")

def parse_candidates(candidate_str):
    """
    将候选项字符串解析为 [(candidate, freq), ...]
    例如 'example1_1:10;example1_2:5'
    """
    if not candidate_str or pd.isna(candidate_str):
        return []
    candidate_str = candidate_str.replace(", ", ",")
    parts = candidate_str.split(" ")
    result = []
    for p in parts:
        p = p.strip()[1:-1]
        if "," in p:
            c, f = p.split(",", 1)
            c, f = c.strip(), f.strip()
            result.append((c, f))
    return result

def load_current_selection():
    """
    根据 current_index，从 st.session_state['df_progress'] 中取出该行的「校对后」，
    用分号分隔还原为列表，赋给 st.session_state["selected_list"]。
    """
    df_progress = st.session_state["df_progress"]
    idx = st.session_state["current_index"]
    row = df_progress.loc[idx]
    corrected_str = row["校对后"] if not pd.isna(row["校对后"]) else ""
    selected_list = [w.strip() for w in corrected_str.split(" ") if w.strip()]
    st.session_state["selected_list"] = selected_list

def save_current_selection():
    """
    将 st.session_state["selected_list"] 写回「校对后」列，然后写入 progress.csv。
    """
    df_progress = st.session_state["df_progress"]
    idx = st.session_state["current_index"]
    new_corrected_str = " ".join(st.session_state["selected_list"])
    df_progress.at[idx, "校对后"] = new_corrected_str
    save_progress(df_progress)

# -----------------------
# 主应用
# -----------------------
def main():
    st.set_page_config(page_title="繁简转换校对平台")
    st.title("繁简转换校对平台")


    # 1. 读取/初始化 progress 数据
    if "df_progress" not in st.session_state:
        df_progress = load_progress()
        st.session_state["df_progress"] = df_progress.copy()

        df_unannotated = st.session_state["df_progress"][
        st.session_state["df_progress"]["校对后"].isna() |
        (st.session_state["df_progress"]["校对后"] == "")
        ]
        if not df_unannotated.empty:
            st.session_state["current_index"] = df_unannotated.index[0]
        else:
            st.session_state["current_index"] = 0

    df_progress = st.session_state["df_progress"]

    # 2. 侧边栏展示已标注列表
    st.sidebar.subheader("已标注任务列表（最近500条）")
    df_annotated = df_progress[df_progress["校对后"].notna() & (df_progress["校对后"] != "")]
    df_annotated = df_annotated.iloc[::-1].iloc[:500].reset_index(drop=True)
    if df_annotated.empty:
        st.sidebar.write("目前还没有已校对的任务。")
    else:
        for i, row in df_annotated.iterrows():
            origin_word = row["原形"]
            corrected = row["校对后"]
            if st.sidebar.button(f"{origin_word} ({corrected})", key=f"sidebar_{i}"):
                # 翻页前先保存当前记录
                save_current_selection()
                st.session_state["current_index"] = i
                load_current_selection()
                st.rerun()

    # 进度统计
    total_count = len(df_progress)
    annotated_count = len(df_annotated)
    st.sidebar.write("---")
    st.sidebar.write(f"**进度**: 已校对 {annotated_count}/{total_count} 条")

    # 3. 初始化 current_index
    if "current_index" not in st.session_state:
        st.session_state["current_index"] = 0

    # 防越界
    if not (0 <= st.session_state["current_index"] < total_count):
        st.session_state["current_index"] = 0

    # 4. 初始化 selected_list
    if "selected_list" not in st.session_state:
        load_current_selection()

    # 5. 当前记录
    idx = st.session_state["current_index"]
    current_row = df_progress.loc[idx]
    origin_word = current_row["原形"]
    pre_word = current_row["校对前"]
    candidate_str = current_row["候选项"]
    candidates = parse_candidates(candidate_str)
    selected_list = st.session_state["selected_list"]

    st.subheader("任务详情")
    st.markdown(f"**{idx + 1} / {total_count}**")
    col_name, col_value = st.columns([1, 4])
    with col_name:
        st.write("**原形**")
        st.write("**校对前**")
        st.write("**校对后**")
    with col_value:
        st.write(origin_word)
        st.write(pre_word)
        if selected_list:
            st.write(" ".join(selected_list))
        else:
            st.write("暂无")

    st.write("---")
    st.write("**候选项**:")
    for (c, freq) in candidates:
        col_op, col_info = st.columns([1, 4])
        with col_op:
            if c in selected_list:
                if st.button("取消", key=f"cancel_{c}"):
                    selected_list.remove(c)
                    st.rerun()
            else:
                if st.button("选择", key=f"select_{c}"):
                    selected_list.append(c)
                    st.rerun()
        with col_info:
            st.write(f"{c} : {freq}")

    # 6. 导航、暂存、完成
    st.write("---")
    col1, col2, col3, col4 = st.columns([1,1,1,1])

    # 上一条
    with col1:
        if st.button("上一条"):
            save_current_selection()
            st.session_state["current_index"] = max(0, idx - 1)
            load_current_selection()
            st.rerun()

    # 下一条
    with col2:
        if st.button("下一条"):
            save_current_selection()
            st.session_state["current_index"] = min(total_count - 1, idx + 1)
            load_current_selection()
            st.rerun()

    # 暂存：只保存进度到 progress.csv
    with col3:
        if st.button("暂存"):
            save_current_selection()
            st.success("已暂存当前标注结果。")

    with col4:
        csv_data = st.session_state["df_progress"].to_csv(index=False, encoding="utf-8")
        st.download_button(
            label="下载",
            data=csv_data,
            file_name="标注结果.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
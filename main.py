import streamlit as st
from pathlib import Path
import unicodedata
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import io

st.set_page_config(page_title="극지식물 최적 EC 농도 연구", layout="wide")

# 한글 폰트 적용
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =====================
# 데이터 로딩 함수
# =====================
@st.cache_data
def load_csv_files(folder_path):
    folder = Path(folder_path)
    csv_files = {}
    if not folder.exists():
        st.error(f"폴더가 존재하지 않습니다: {folder_path}")
        return csv_files

    for file in folder.iterdir():
        file_name = unicodedata.normalize("NFC", file.name)
        if file_name.endswith(".csv"):
            school_name = file_name.replace("_환경데이터.csv", "")
            try:
                df = pd.read_csv(file, encoding="utf-8")
                csv_files[school_name] = df
            except Exception as e:
                st.error(f"CSV 로딩 실패: {file_name} ({e})")
    return csv_files

@st.cache_data
def load_excel_file(file_path):
    file = Path(file_path)
    if not file.exists():
        st.error(f"파일이 존재하지 않습니다: {file_path}")
        return {}
    try:
        xls = pd.ExcelFile(file, engine="openpyxl")
        sheets = {}
        for sheet_name in xls.sheet_names:
            normalized_name = unicodedata.normalize("NFC", sheet_name)
            sheets[normalized_name] = pd.read_excel(xls, sheet_name=sheet_name, engine="openpyxl")
        return sheets
    except Exception as e:
        st.error(f"Excel 로딩 실패: {file_path} ({e})")
        return {}

# =====================
# 데이터 로드
# =====================
with st.spinner("데이터 로딩 중..."):
    env_data_dict = load_csv_files("data")
    growth_data_dict = load_excel_file("data/4개교_생육결과데이터.xlsx")

schools = ["전체"] + list(env_data_dict.keys())

# =====================
# 사이드바
# =====================
selected_school = st.sidebar.selectbox("학교 선택", schools)

# =====================
# Tab 1: 실험 개요
# =====================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

with tab1:
    st.header("🌱 극지식물 최적 EC 농도 연구")
    st.markdown("""
    **연구 배경 및 목적:**  
    극지식물의 생육은 EC 조건에 민감하며, 학교별 환경 조건에 따라 생육 성능이 달라집니다.  
    본 연구는 4개 학교에서 측정한 환경 데이터와 생육 데이터를 분석하여 **최적 EC 농도**를 도출하고자 합니다.
    """)
    # 학교별 EC 조건 테이블
    school_info = []
    ec_dict = {"송도고":1.0, "하늘고":2.0, "아라고":4.0, "동산고":8.0}
    for school, df in growth_data_dict.items():
        school_info.append({
            "학교명": school,
            "EC 목표": ec_dict.get(school, None),
            "개체수": len(df),
            "색상": px.colors.qualitative.Plotly[list(growth_data_dict.keys()).index(school)]
        })
    st.table(pd.DataFrame(school_info))

    # 주요 지표 카드
    total_count = sum([len(df) for df in growth_data_dict.values()])
    avg_temp = round(sum([df_env["temperature"].mean() for df_env in env_data_dict.values()])/len(env_data_dict), 2)
    avg_humidity = round(sum([df_env["humidity"].mean() for df_env in env_data_dict.values()])/len(env_data_dict), 2)
    optimal_ec = 2.0  # 하늘고
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", total_count)
    col2.metric("평균 온도 (℃)", avg_temp)
    col3.metric("평균 습도 (%)", avg_humidity)
    col4.metric("최적 EC", optimal_ec)

# =====================
# Tab 2: 환경 데이터
# =====================
with tab2:
    st.header("🌡️ 환경 데이터 비교")
    
    # 학교별 평균 비교
    summary_df = pd.DataFrame()
    for school, df in env_data_dict.items():
        summary_df = pd.concat([summary_df,
                                pd.DataFrame({
                                    "학교": school,
                                    "평균 온도": [df["temperature"].mean()],
                                    "평균 습도": [df["humidity"].mean()],
                                    "평균 pH": [df["ph"].mean()],
                                    "목표 EC": [ec_dict.get(school)],
                                    "실측 EC": [df["ec"].mean()]
                                })])
    fig = make_subplots(rows=2, cols=2, subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"))
    
    # 좌상: 평균 온도
    fig.add_trace(go.Bar(x=summary_df["학교"], y=summary_df["평균 온도"], name="평균 온도"), row=1, col=1)
    # 우상: 평균 습도
    fig.add_trace(go.Bar(x=summary_df["학교"], y=summary_df["평균 습도"], name="평균 습도"), row=1, col=2)
    # 좌하: 평균 pH
    fig.add_trace(go.Bar(x=summary_df["학교"], y=summary_df["평균 pH"], name="평균 pH"), row=2, col=1)
    # 우하: 목표 vs 실측 EC
    fig.add_trace(go.Bar(x=summary_df["학교"], y=summary_df["목표 EC"], name="목표 EC"), row=2, col=2)
    fig.add_trace(go.Bar(x=summary_df["학교"], y=summary_df["실측 EC"], name="실측 EC"), row=2, col=2)
    
    fig.update_layout(height=600, width=1000, showlegend=True,
                      font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig, use_container_width=True)
    
    # 선택한 학교 시계열
    if selected_school != "전체":
        df_env = env_data_dict[selected_school]
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=df_env["time"], y=df_env["temperature"], mode="lines", name="온도"))
        fig_ts.add_trace(go.Scatter(x=df_env["time"], y=df_env["humidity"], mode="lines", name="습도"))
        fig_ts.add_trace(go.Scatter(x=df_env["time"], y=df_env["ec"], mode="lines", name="EC"))
        fig_ts.add_hline(y=ec_dict[selected_school], line_dash="dash", line_color="red", annotation_text="목표 EC")
        fig_ts.update_layout(height=400, width=900,
                             font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig_ts, use_container_width=True)

    # 원본 데이터 expander
    for school, df in env_data_dict.items():
        with st.expander(f"{school} 환경 데이터 보기"):
            st.dataframe(df)
            csv_buffer = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="CSV 다운로드", data=csv_buffer,
                               file_name=f"{school}_환경데이터.csv", mime="text/csv")

# =====================
# Tab 3: 생육 결과
# =====================
with tab3:
    st.header("📊 생육 결과 분석")

    # EC별 평균 생중량 계산
    ec_summary = pd.DataFrame()
    for school, df in growth_data_dict.items():
        # 숫자형 변환
        df_weight = pd.to_numeric(df["생중량(g)"], errors="coerce")
        df_leaf = pd.to_numeric(df["잎 수(장)"], errors="coerce")
        df_shoot = pd.to_numeric(df["지상부 길이(mm)"], errors="coerce")

        ec_summary = pd.concat([ec_summary,
                                pd.DataFrame({
                                    "학교": school,
                                    "EC": [ec_dict.get(school)],
                                    "평균 생중량": [df_weight.mean(skipna=True)],
                                    "평균 잎 수": [df_leaf.mean(skipna=True)],
                                    "평균 지상부 길이": [df_shoot.mean(skipna=True)],
                                    "개체수": [len(df)]
                                })], ignore_index=True)

    # 최적 EC 생중량 안전하게 표시
    if not ec_summary.empty and ec_summary["평균 생중량"].notna().any():
        max_weight = ec_summary.loc[ec_summary["평균 생중량"].idxmax(), "평균 생중량"]
        st.metric("⭐ 최적 EC 생중량", round(float(max_weight), 2))
    else:
        st.metric("⭐ 최적 EC 생중량", "데이터 없음")

    # EC별 생육 비교 2x2 막대
    fig_growth = make_subplots(rows=2, cols=2, subplot_titles=("평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"))
    fig_growth.add_trace(go.Bar(x=ec_summary["학교"], y=ec_summary["평균 생중량"], name="평균 생중량"), row=1, col=1)
    fig_growth.add_trace(go.Bar(x=ec_summary["학교"], y=ec_summary["평균 잎 수"], name="평균 잎 수"), row=1, col=2)
    fig_growth.add_trace(go.Bar(x=ec_summary["학교"], y=ec_summary["평균 지상부 길이"], name="평균 지상부 길이"), row=2, col=1)
    fig_growth.add_trace(go.Bar(x=ec_summary["학교"], y=ec_summary["개체수"], name="개체수"), row=2, col=2)
    fig_growth.update_layout(height=600, width=1000, font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
    st.plotly_chart(fig_growth, use_container_width=True)

    # 학교별 생중량 분포 박스플롯
    for school, df in growth_data_dict.items():
        fig_box = px.box(df, y="생중량(g)", points="all", title=f"{school} 생중량 분포")
        fig_box.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig_box, use_container_width=True)

    # 상관관계 분석
    for school, df in growth_data_dict.items():
        fig_scatter = make_subplots(rows=1, cols=2, subplot_titles=("잎 수 vs 생중량", "지상부 길이 vs 생중량"))
        fig_scatter.add_trace(go.Scatter(x=df["잎 수(장)"], y=df["생중량(g)"], mode="markers", name="잎 수"), row=1, col=1)
        fig_scatter.add_trace(go.Scatter(x=df["지상부 길이(mm)"], y=df["생중량(g)"], mode="markers", name="지상부 길이"), row=1, col=2)
        fig_scatter.update_layout(height=400, width=900, font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig_scatter, use_container_width=True)

    # 원본 데이터 다운로드
    for school, df in growth_data_dict.items():
        with st.expander(f"{school} 생육 데이터 보기"):
            st.dataframe(df)
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)
            st.download_button(
                data=buffer,
                file_name=f"{school}_생육결과.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

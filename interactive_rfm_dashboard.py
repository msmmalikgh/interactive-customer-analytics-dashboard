# interactive_rfm_dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import io

# -------------------------------
# Page setup
# -------------------------------
st.set_page_config(page_title="Interactive Customer Analytics Dashboard", layout="wide")
st.title("🛒 Interactive Customer Analytics Dashboard")

# -------------------------------
# 1️⃣ Upload raw data
# -------------------------------
st.sidebar.subheader("Upload your dataset")
uploaded_file = st.sidebar.file_uploader("Choose Excel file", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("Raw Data Preview")
    st.dataframe(df.head())

    # -------------------------------
    # 2️⃣ Data Cleaning
    # -------------------------------
    df.drop_duplicates(inplace=True)
    df = df[df['Customer ID'].notna()]
    df = df[(df['Quantity'] > 0) & (df['Price'] > 0)]
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['TotalPrice'] = df['Quantity'] * df['Price']

    st.subheader("Cleaned Data Summary")
    st.write(df.describe())
    st.write(f"Total Customers: {df['Customer ID'].nunique()}")

    # -------------------------------
    # 3️⃣ RFM Calculation
    # -------------------------------
    analysis_date = df['InvoiceDate'].max() + pd.Timedelta(days=1)
    rfm = df.groupby('Customer ID').agg({
        'InvoiceDate': lambda x: (analysis_date - x.max()).days,
        'Invoice': 'nunique',
        'TotalPrice': 'sum'
    }).reset_index()
    rfm.columns = ['CustomerID','Recency','Frequency','Monetary']

    # RFM scoring (1-5)
    rfm['R_Score'] = pd.qcut(rfm['Recency'], 5, labels=[5,4,3,2,1]).astype(int)
    rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), 5, labels=[1,2,3,4,5]).astype(int)
    rfm['M_Score'] = pd.qcut(rfm['Monetary'], 5, labels=[1,2,3,4,5]).astype(int)
    rfm['RFM_Score'] = rfm['R_Score']*100 + rfm['F_Score']*10 + rfm['M_Score']

    # Segment mapping
    def segment_mapping(row):
        if row['RFM_Score']>=555:
            return 'Champion'
        elif row['F_Score']>=4 and row['M_Score']>=4:
            return 'Loyal'
        elif row['R_Score']>=4 and row['F_Score']>=3:
            return 'Potential'
        elif row['R_Score']<=2 and row['F_Score']<=2:
            return 'At Risk'
        else:
            return 'Hibernating'

    rfm['Segment'] = rfm.apply(segment_mapping, axis=1)

    # -------------------------------
    # 4️⃣ CLTV Estimation
    # -------------------------------
    # Simple CLTV = Monetary * Frequency
    rfm['CLTV'] = rfm['Monetary'] * rfm['Frequency']

    # -------------------------------
    # 5️⃣ Sidebar filters
    # -------------------------------
    st.sidebar.subheader("Filter by Segment")
    segments = st.sidebar.multiselect(
        "Select Segment",
        rfm['Segment'].unique(),
        default=rfm['Segment'].unique()
    )
    filtered_rfm = rfm[rfm['Segment'].isin(segments)]

    # -------------------------------
    # 6️⃣ KPI Metrics
    # -------------------------------
    st.subheader("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Customers", len(filtered_rfm))
    col2.metric("Avg Recency", round(filtered_rfm['Recency'].mean(),1))
    col3.metric("Avg Frequency", round(filtered_rfm['Frequency'].mean(),1))
    col4.metric("Avg CLTV", round(filtered_rfm['CLTV'].mean(),1))

    # -------------------------------
    # 7️⃣ Visualizations
    # -------------------------------
    st.subheader("RFM Heatmap")
    rfm_avg = filtered_rfm.groupby('Segment')[['Recency','Frequency','Monetary']].mean()
    fig, ax = plt.subplots()
    sns.heatmap(rfm_avg, annot=True, fmt=".1f", cmap='YlGnBu', ax=ax)
    st.pyplot(fig)

    st.subheader("CLTV Distribution")
    fig2, ax2 = plt.subplots()
    sns.histplot(filtered_rfm['CLTV'], bins=50, kde=True, ax=ax2, color='skyblue')
    st.pyplot(fig2)

    st.subheader("Recency vs Monetary by Segment")
    fig3, ax3 = plt.subplots()
    sns.scatterplot(
        data=filtered_rfm,
        x='Recency',
        y='Monetary',
        hue='Segment',
        palette='Set2',
        s=50,
        alpha=0.7,
        ax=ax3
    )
    ax3.set_title("Recency vs Monetary by Segment")
    st.pyplot(fig3)

    # -------------------------------
    # 8️⃣ Top 10 Customers by CLTV
    # -------------------------------
    st.subheader("Top 10 Customers by CLTV")
    top10 = filtered_rfm.sort_values('CLTV', ascending=False).head(10)
    st.dataframe(top10)

    # -------------------------------
    # 9️⃣ Download Filtered Data (Excel)
    # -------------------------------
    st.subheader("Download Filtered Data (.xlsx)")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_rfm.to_excel(writer, index=False, sheet_name='FilteredData')
    processed_data = output.getvalue()
    st.download_button(
        label="Download Filtered Data (.xlsx)",
        data=processed_data,
        file_name="filtered_customers.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("📌 Please upload an Excel file to start the analysis.")

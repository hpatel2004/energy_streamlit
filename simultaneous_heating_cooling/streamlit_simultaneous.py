import pandas as pd
import matplotlib.pyplot as plt
import re
import streamlit as st

import os

# =========================================
# CONFIG
# =========================================
BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "data.xlsm")
CHW_SHEET = "CHW hourly"
MTHW_SHEET = "MTHW hourly"

st.title("Simultaneous Heating + Cooling Analyzer")

# =========================================
# LOAD SHEETS
# =========================================
@st.cache_data
def load_data():
    chw_df = pd.read_excel(DATA_FILE, sheet_name=CHW_SHEET)
    mthw_df = pd.read_excel(DATA_FILE, sheet_name=MTHW_SHEET)

    # Fix timestamp
    for df in [chw_df, mthw_df]:
        df["datetime"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df.dropna(subset=["datetime"], inplace=True)
        df.sort_values("datetime", inplace=True)

    return chw_df, mthw_df

chw_df, mthw_df = load_data()

# =========================================
# EXTRACT BUILDING NAMES FROM COLUMNS
# =========================================

def extract_building_names(columns, suffix):
    pattern = fr"(.+?) {suffix} \(kbtuh\)"
    buildings = []
    for col in columns:
        m = re.match(pattern, col)
        if m:
            buildings.append(m.group(1))
    return buildings

chw_buildings = extract_building_names(chw_df.columns, "CHW")
mthw_buildings = extract_building_names(mthw_df.columns, "MTHW")

# Only buildings that exist in both datasets
common_buildings = sorted(list(set(chw_buildings) & set(mthw_buildings)))

st.subheader("Select Building")
building = st.selectbox("Choose a building:", options=common_buildings)

if not building:
    st.stop()

st.success(f"Selected Building: **{building}**")

# =========================================
# ADD THRESHOLD EDITOR
# =========================================
st.subheader("Threshold Adjustment")

threshold = st.number_input(
    "Enter the kBTU/h threshold for determining system 'on' status:",
    min_value=0,
    max_value=5000,
    value=700,
    step=50
)

st.info(f"Using threshold: **{threshold} kBTU/h**")

# =========================================
# IDENTIFY COLUMN NAMES
# =========================================
chw_col = f"{building} CHW (kbtuh)"
mthw_col = f"{building} MTHW (kbtuh)"

# =========================================
# MERGE AND ANALYZE
# =========================================
df = pd.merge(
    chw_df[["datetime", chw_col]],
    mthw_df[["datetime", mthw_col]],
    on="datetime",
    how="inner"
)

df.rename(columns={chw_col: "CHW", mthw_col: "MTHW"}, inplace=True)

df["CHW_on"] = df["CHW"] > threshold
df["MTHW_on"] = df["MTHW"] > threshold
df["simul"] = df["CHW_on"] & df["MTHW_on"]

simul_df = df[df["simul"]]

# =========================================
# DISPLAY RESULTS
# =========================================
st.subheader("Simultaneous Heating + Cooling Summary")

st.write(f"**Total hours detected:** {len(simul_df)}")

st.dataframe(simul_df[["datetime", "CHW", "MTHW"]])

# =========================================
# PLOTTING
# =========================================

# CHW Plot
plt.figure(figsize=(14, 5))
plt.plot(df["datetime"], df["CHW"], label="CHW Load")
plt.axhline(threshold, linestyle="--", label="Threshold", color = "red")
plt.title(f"{building} — CHW Load")
plt.xlabel("Date")
plt.ylabel("kbtuh")
plt.legend()
st.pyplot(plt)
plt.clf()

# MTHW Plot
plt.figure(figsize=(14, 5))
plt.plot(df["datetime"], df["MTHW"], label="MTHW Load")
plt.axhline(threshold, linestyle="--", label="Threshold", color="red")
plt.title(f"{building} — MTHW Load")
plt.xlabel("Date")
plt.ylabel("kbtuh")
plt.legend()
st.pyplot(plt)
plt.clf()

# Joint Plot
plt.figure(figsize=(16, 6))
plt.plot(df["datetime"], df["CHW"], label="CHW", alpha=0.7)
plt.plot(df["datetime"], df["MTHW"], label="MTHW", alpha=0.7)
plt.axhline(threshold, linestyle="--", label="Threshold", color="red")

plt.scatter(simul_df["datetime"], simul_df["CHW"], label="Simultaneous H+C", color="red", s=30)


plt.title(f"{building} — Simultaneous Heating + Cooling")
plt.xlabel("Date")
plt.ylabel("kbtuh")
plt.legend()
st.pyplot(plt)
plt.clf()

# =========================================
# SAVE FILE
# =========================================
out_file = f"simultaneous_{building.replace(' ', '_')}.csv"
st.success(f"Saved output file: **{out_file}**")

st.download_button("Download CSV", data=simul_df.to_csv(index=False), file_name=out_file)

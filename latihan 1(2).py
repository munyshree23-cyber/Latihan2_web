import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
from PIL import Image

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="PUO Kadaster Digital", layout="wide")

# 2. LOGIK PENCARIAN LOGO
def cari_fail_logo():
    try:
        for fail in os.listdir('.'):
            nama_low = fail.lower()
            if ('puo' in nama_low or 'logo' in nama_low) and nama_low.endswith(('.png', '.jpg', '.jpeg')):
                return fail
    except:
        return None
    return None

fail_logo = cari_fail_logo()

# 3. HEADER
col1, col2 = st.columns([1, 8])
with col1:
    if fail_logo:
        try:
            st.image(Image.open(fail_logo), width=120)
        except:
            st.markdown("### 🏛️ PUO")
    else:
        st.markdown("### 🏛️")

with col2:
    st.title("POLITEKNIK UNGKU OMAR")
    st.subheader("Sistem Pemplotan Lot Kadaster Digital")

st.markdown("---")

# 4. FUNGSI PENGIRAAN
def hitung_dan_label_straight(df):
    # Pastikan data adalah nombor
    df['E'] = pd.to_numeric(df['E'])
    df['N'] = pd.to_numeric(df['N'])
    
    n = len(df)
    features = []
    for i in range(n):
        p1 = df.iloc[i]
        p2 = df.iloc[(i + 1) % n]
        de, dn = p2['E'] - p1['E'], p2['N'] - p1['N']
        dist = np.sqrt(de**2 + dn**2)
        
        # Kira Bering
        brg_deg = np.degrees(np.arctan2(de, dn)) % 360
        d = int(brg_deg)
        m = int((brg_deg-d)*60)
        s = round(((brg_deg-d)*60-m)*60)
        if s == 60: m += 1; s = 0
        if m == 60: d += 1; m = 0
        
        # Kira sudut teks (supaya selari dengan garisan)
        line_angle = np.degrees(np.arctan2(dn, de))
        if line_angle > 90: line_angle -= 180
        if line_angle < -90: line_angle += 180
        
        features.append({
            'mid_e': (p1['E'] + p2['E']) / 2, 
            'mid_n': (p1['N'] + p2['N']) / 2,
            'brg_txt': f"{d}°{m}'{s:02d}\"", 
            'dist_txt': f"{dist:.2f}m",
            'angle': line_angle, 'de': de, 'dn': dn
        })
    
    # Kira Luas (Metod Shoelace)
    area = 0.5 * np.abs(np.dot(df['E'], np.roll(df['N'], 1)) - np.dot(df['N'], np.roll(df['E'], 1)))
    return features, area

# 5. UI & PROSES
uploaded_file = st.file_uploader("1️⃣ Muat naik fail CSV (Mesti ada kolum STN, E, N)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Semak jika kolum wujud
    if all(col in df.columns for col in ['STN', 'E', 'N']):
        
        # Butang untuk proses
        if st.button("2️⃣ KIRA LUAS & PLOT"):
            st.session_state.ready = True

        if st.session_state.get('ready'):
            # --- BAHAGIAN PLOT ---
            fig = go.Figure()
            
            # Sambungkan titik terakhir ke pertama untuk poligon
            df_poly = pd.concat([df, df.iloc[[0]]], ignore_index=True)
            
            # Lukis Poligon
            fig.add_trace(go.Scatter(
                x=df_poly['E'], y=df_poly['N'], 
                mode='lines', 
                fill="toself", 
                fillcolor='rgba(255, 242, 0, 0.1)', 
                line=dict(color='black', width=3),
                name="Sempadan Lot"
            ))
            
            # Lukis Marker Stesen
            fig.add_trace(go.Scatter(
                x=df['E'], y=df['N'], 
                mode='markers+text',
                marker=dict(size=12, color='white', line=dict(color='red', width=2)),
                text=df['STN'], 
                textposition="top right",
                name="Stesen"
            ))

            # Tambah Label Bering & Jarak
            feats, area = hitung_dan_label_straight(df)
            for f in feats:
                L = np.sqrt(f['de']**2 + f['dn']**2)
                nx, ny = -f['dn']/L, f['de']/L # Vektor normal untuk offset teks
                
                # Jarak (di luar/atas garisan)
                fig.add_annotation(x=f['mid_e']+nx*0.8, y=f['mid_n']+ny*0.8, text=f"<b>{f['dist_txt']}</b>",
                                   showarrow=False, textangle=-f['angle'], font=dict(size=10))
                # Bering (di dalam/bawah garisan)
                fig.add_annotation(x=f['mid_e']-nx*0.8, y=f['mid_n']-ny*0.8, text=f"<b>{f['brg_txt']}</b>",
                                   showarrow=False, textangle=-f['angle'], font=dict(color="blue", size=10))

            # Label Luas di tengah
            fig.add_annotation(x=df['E'].mean(), y=df['N'].mean(), 
                               text=f"<b>LUAS: {area:,.2f} m²</b><br>({(area*0.000247105):.4f} ekar)",
                               showarrow=False, bgcolor="white", bordercolor="black", borderpad=10)
            
            fig.update_yaxes(scaleanchor="x", scaleratio=1)
            fig.update_layout(xaxis_title="Easting (E)", yaxis_title="Northing (N)", margin=dict(l=20, r=20, t=20, b=20))
            
            st.plotly_chart(fig, use_container_width=True)

            # --- 3️⃣ BAHAGIAN EKSPORT ---
            st.success(f"✅ Analisis Selesai! Luas Lot: {area:,.2f} m²")
            
            with st.expander("📥 SIMPAN DATA UNTUK QGIS / AUTOCAD", expanded=True):
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 DOWNLOAD CSV UNTUK QGIS",
                    data=csv_data,
                    file_name='lot_kadaster_puo.csv',
                    mime='text/csv',
                    use_container_width=True
                )
                st.info("💡 **Nota QGIS:** Buka QGIS > Layer > Add Layer > Add Delimited Text Layer. Pilih fail ini dan set X=E, Y=N.")
    else:
        st.error("Ralat: Fail CSV mesti ada header 'STN', 'E', dan 'N'.")
else:
    st.session_state.ready = False
    st.info("Sila muat naik fail CSV koordinat untuk bermula.")
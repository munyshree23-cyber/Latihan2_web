import streamlit as st
import pandas as pd
import geopandas as gpd
import leafmap.foliumap as leafmap
from shapely.geometry import Polygon, Point, mapping
import numpy as np
from pyproj import Transformer
import folium
import os
import base64
import json

# --- CONFIGURATION & MAPPING ---
# User mapping for the 3 allowed IDs
USER_DATABASE = {
    "1": "MUNISSHREE",
    "2": "CHAN BOON YEAH",
    "3": "YUENYI"
}

# --- FUNGSI HELPER ---
def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

def hitung_ukur(p1, p2):
    de, dn = p2[0]-p1[0], p2[1]-p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn)) % 360
    d, m = int(brg), int((brg - int(brg)) * 60)
    s = int((((brg - d) * 60) - m) * 60)
    return f"{d}°{m}'{s}\"", f"{dist:.3f}m"

# --- 1. LOGIN & AUTH ---
if "db_password" not in st.session_state: st.session_state.db_password = "admin123"
if "auth" not in st.session_state: st.session_state.auth = False
if "current_user_name" not in st.session_state: st.session_state.current_user_name = ""

if not st.session_state.auth:
    st.set_page_config(page_title="Login - Sistem Survey Lot", layout="centered")
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
        .login-box { background-color: white; padding: 40px; border-radius: 15px; box-shadow: 0px 10px 25px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }
        h1 { color: #1e3a8a; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        logo_b64 = get_base64_of_bin_file("LOGO PUO.png")
        if logo_b64:
            st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{logo_b64}" width="250"></div>', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; margin-top: 20px;'>SISTEM SURVEY LOT</h1>", unsafe_allow_html=True)
        
        uid = st.text_input("👤 ID Pengguna", placeholder="Masukkan ID (1, 2, atau 3)")
        pwd = st.text_input("🔑 Kata Laluan", type="password", placeholder="Masukkan kata laluan")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 Log Masuk", use_container_width=True):
                # Check if ID exists and password matches
                if uid in USER_DATABASE and pwd == st.session_state.db_password:
                    st.session_state.auth = True
                    st.session_state.current_user_name = USER_DATABASE[uid]
                    st.rerun()
                else: 
                    st.error("ID atau Kata Laluan Salah!")
        with c2:
            if st.button("❓ Lupa Kata Laluan", use_container_width=True):
                st.info(f"Sila hubungi Admin PUO. Hint: '{st.session_state.db_password}'")
        
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 2. SISTEM UTAMA ---
st.set_page_config(page_title=f"SISTEM SURVEY LOT - {st.session_state.current_user_name}", layout="wide")

if 'df_current' not in st.session_state: 
    st.session_state.df_current = None
if 'geojson_str' not in st.session_state:
    st.session_state.geojson_str = None

# --- SIDEBAR: KAWALAN & DOWNLOAD ---
with st.sidebar:
    st.markdown(f"""<div style='background: linear-gradient(to bottom, #00bfff, #0073e6); padding: 20px; border-radius: 15px; text-align: center; color: white; box-shadow: 0px 4px 10px rgba(0,0,0,0.2);'>
        <div style='font-size: 50px;'>🐼</div>
        <b style='font-size:18px;'>Hai, {st.session_state.current_user_name}!</b><br><small>PUO - JKA</small></div>""", unsafe_allow_html=True)
    
    st.write("---")
    st.header("⚙️ Kawalan Paparan")
    show_sat = st.toggle("🛰️ Google Maps (Satelit)", value=True)
    show_labels = st.toggle("📏 Bering & Jarak", value=True)
    show_points = st.toggle("📍 Nombor Stesen", value=True)
    
    st.write("---")
    zoom_level = st.slider("🔍 Tahap Zoom Peta", 5, 22, 19)
    sz_marker = st.slider("Saiz Marker Stesen", 10, 60, 24)
    sz_font = st.slider("Saiz Tulisan", 6, 25, 10)
    warna_poly = st.color_picker("Warna Poligon Lot", "#FFFF00") 
    
    st.write("---")
    with st.expander("🔑 Tukar Kata Laluan"):
        new_pwd = st.text_input("Kata Laluan Baru", type="password")
        if st.button("Simpan Kata Laluan"):
            if new_pwd:
                st.session_state.db_password = new_pwd
                st.success("Kata laluan dikemaskini!")
            else:
                st.warning("Sila masukkan kata laluan.")

    st.write("---")
    st.markdown("### 💾 Eksport Data QGIS")
    
    if st.session_state.geojson_str is not None:
        st.download_button(
            label="🚀 Download GeoJSON",
            data=st.session_state.geojson_str,
            file_name=f"survey_lot_{st.session_state.current_user_name}.geojson",
            mime="application/geo+json",
            use_container_width=True
        )
    else:
        st.button("🚀 Download GeoJSON (No Data)", disabled=True, use_container_width=True)

    st.write("---")
    if st.button("🚪 Log Keluar", use_container_width=True): 
        st.session_state.auth = False
        st.rerun()

# --- HEADER UTAMA ---
col_logo, col_header = st.columns([1, 4])
with col_logo:
    logo_b64_header = get_base64_of_bin_file("LOGO PUO.png")
    if logo_b64_header: st.markdown(f'<img src="data:image/png;base64,{logo_b64_header}" width="160">', unsafe_allow_html=True)

with col_header:
    st.markdown(f"<div style='background-color:white; padding:15px; border-radius:10px; color:black; border: 2px solid #1e3a8a;'><h1 style='margin:0; color:#1e3a8a;'>SISTEM SURVEY LOT</h1><p style='margin:0; font-weight:bold;'>Politeknik Ungku Omar | Jabatan Kejuruteraan Awam</p></div>", unsafe_allow_html=True)

st.write("---")
col_a, col_b = st.columns(2)
with col_a: epsg_code = st.text_input("🌍 Kod EPSG:", value="4390") 
with col_b: u_file = st.file_uploader("📂 Muat naik fail CSV", type=['csv'])

# --- PROSES & PAPAR PETA ---
if u_file:
    df = pd.read_csv(u_file)
    transformer = Transformer.from_crs(f"EPSG:{epsg_code}", "EPSG:4326", always_xy=True)
    df['lon'], df['lat'] = transformer.transform(df['E'].values, df['N'].values)
    st.session_state.df_current = df
    
    pts_meter = list(zip(df['E'], df['N']))
    poly_meter = Polygon(pts_meter)
    luas_lot = abs(poly_meter.area)
    perimeter_lot = poly_meter.length

    # --- BINA GEOJSON UNTUK MUAT TURUN ---
    features = []
    for _, row in df.iterrows():
        features.append({
            "type": "Feature",
            "geometry": mapping(Point(row.lon, row.lat)),
            "properties": {"STN": int(row.STN), "E": row.E, "N": row.N, "Type": "Station"}
        })
    
    coords_wgs = list(zip(df.lon, df.lat))
    if coords_wgs[0] != coords_wgs[-1]: coords_wgs.append(coords_wgs[0])
    features.append({
        "type": "Feature",
        "geometry": mapping(Polygon(coords_wgs)),
        "properties": {
            "Name": "Boundary Lot", 
            "Owner": st.session_state.current_user_name, 
            "Area_m2": round(luas_lot, 3), 
            "Perimeter_m": round(perimeter_lot, 3)
        }
    })
    st.session_state.geojson_str = json.dumps({"type": "FeatureCollection", "features": features})

    # --- PAPARAN PETA ---
    m = leafmap.Map(center=[df['lat'].mean(), df['lon'].mean()], zoom=zoom_level)
    
    if show_sat:
        m.add_tile_layer(url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", name="Satelit", attribution="Google")
    
    html_popup = f"""
    <div style="font-family: Arial; width: 200px;">
        <h4 style="margin-bottom:10px; color:#1e3a8a;">Maklumat Lot</h4>
        <hr>
        <b>Nama Pemilik:</b> {st.session_state.current_user_name}<br>
        <b>Luas:</b> {luas_lot:.3f} m²<br>
        <b>Perimeter:</b> {perimeter_lot:.3f} m
    </div>
    """
    
    folium.Polygon(
        locations=[(p[1], p[0]) for p in coords_wgs], 
        color=warna_poly, 
        weight=3, 
        fill=True, 
        fill_opacity=0.3,
        popup=folium.Popup(html_popup, max_width=300)
    ).add_to(m)

    poly_geom_wgs = Polygon(coords_wgs)
    c_lat, c_lon = poly_geom_wgs.centroid.y, poly_geom_wgs.centroid.x

    for i in range(len(df)):
        p1 = df.iloc[i]
        p2 = df.iloc[(i+1)%len(df)]
        
        if show_labels:
            mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
            angle = np.degrees(np.arctan2(p2['lat'] - p1['lat'], p2['lon'] - p1['lon']))
            if angle > 90: angle -= 180
            if angle < -90: angle += 180
            brg_txt, dist_txt = hitung_ukur((p1['E'], p1['N']), (p2['E'], p2['N']))
            v_lat, v_lon = c_lat - mid_lat, c_lon - mid_lon
            norm = np.sqrt(v_lat**2 + v_lon**2)
            out_lat, out_lon = mid_lat - (v_lat/norm) * 0.000008, mid_lon - (v_lon/norm) * 0.000008
            
            folium.Marker(
                [out_lat, out_lon], 
                icon=folium.DivIcon(html=f'<div style="transform: rotate({-angle}deg); color: yellow; font-weight: bold; font-size: {sz_font}pt; text-shadow: 1px 1px black; white-space: nowrap;">{brg_txt}<br>{dist_txt}</div>')
            ).add_to(m)

        if show_points:
            stn_info = f"<b>Stesen {int(p1['STN'])}</b><br>E: {p1['E']:.3f}<br>N: {p1['N']:.3f}"
            folium.CircleMarker(
                location=[p1['lat'], p1['lon']], radius=sz_marker/2, color='white', weight=1, fill=True, fill_color='red', fill_opacity=1,
                popup=folium.Popup(stn_info, max_width=200)
            ).add_to(m)
            folium.Marker(
                [p1['lat'], p1['lon']], 
                icon=folium.DivIcon(html=f'<div style="color: white; font-weight: bold; font-size: {sz_font}pt; width: {sz_marker}px; height: {sz_marker}px; display: flex; align-items: center; justify-content: center; pointer-events: none;">{int(p1["STN"])}</div>')
            ).add_to(m)

    m.to_streamlit(height=650)
    st.success(f"✅ Analisis Selesai: Luas {luas_lot:.3f} m² | Perimeter {perimeter_lot:.3f} m")
    
    if st.session_state.geojson_str and 'rerun_done' not in st.session_state:
        st.session_state.rerun_done = True
        st.rerun()
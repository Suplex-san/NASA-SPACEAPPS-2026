import os
import streamlit as st
import numpy as np
import rasterio as rio
from rasterio.transform import from_origin
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape, LineString, Point
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from scipy.ndimage import gaussian_filter

# =====================================================================
# 1. CONFIGURACIÓN E INTERFAZ TÁCTICA MATRIX (NEGRO / VERDE TERMINAL)
# =====================================================================
st.set_page_config(
    page_title="OCEANGUARDIAN_AI // MULTI-SCENE SAR TELEMETRY",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;700&display=swap');

    .stApp {
        background-color: #050505;
        color: #E0E6ED;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #080C08;
        border-right: 1px solid #00FF6644;
    }
    .terminal-header {
        background-color: #090E09;
        border: 1px solid #00FF6666;
        border-left: 6px solid #00FF66;
        padding: 26px 32px;
        border-radius: 4px;
        margin-bottom: 20px;
        box-shadow: 0 0 30px rgba(0, 255, 102, 0.08);
    }
    .sys-badge {
        font-family: 'JetBrains Mono', monospace;
        background-color: #00FF6618;
        color: #00FF66;
        border: 1px solid #00FF66;
        padding: 3px 10px;
        border-radius: 2px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 1.5px;
    }
    .sys-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.2rem;
        font-weight: 800;
        color: #FFFFFF !important;
        margin-top: 10px;
        margin-bottom: 6px;
    }
    .sys-subtitle {
        font-size: 0.98rem;
        color: #94A3B8;
        max-width: 950px;
    }
    .panel-section {
        background-color: #090D09;
        border: 1px solid #1A291E;
        border-radius: 4px;
        padding: 22px;
        margin-bottom: 18px;
    }
    .panel-title {
        font-family: 'JetBrains Mono', monospace;
        color: #00FF66 !important;
        font-size: 1.1rem;
        font-weight: 600;
        border-bottom: 1px solid #1A291E;
        padding-bottom: 8px;
        margin-bottom: 14px;
        text-transform: uppercase;
    }
    .kpi-card {
        background-color: #090E09;
        border: 1px solid #00FF6633;
        border-top: 3px solid #00FF66;
        padding: 14px;
        border-radius: 4px;
    }
    .kpi-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.7rem;
        font-weight: 800;
        color: #00FF66;
        margin: 4px 0;
    }
    .kpi-lbl {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #8B949E;
        text-transform: uppercase;
    }
    .matrix-alert {
        background-color: #07120A;
        border: 1px solid #00FF66;
        border-left: 6px solid #00FF66;
        padding: 18px;
        border-radius: 4px;
        margin-top: 14px;
        color: #D1FAE5;
    }
    .tech-note {
        font-family: 'JetBrains Mono', monospace;
        background-color: #0C140E;
        border-left: 3px solid #00FF66;
        padding: 10px 14px;
        font-size: 0.82rem;
        color: #A7F3D0;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. GENERADOR MULTIESCENA DE ARCHIVOS .TIF FÍSICOS (3 CASOS DISTINTOS)
# =====================================================================
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))

CATALOGO_ESCENAS = {
    "ESCENA 01 // Estrecho de Gibraltar (Aguas de Sentina)": {
        "archivo": "escena_01_sentina.tif",
        "lon_origen": -5.60, "lat_origen": 36.15,
        "semilla": 42, "tipo_morfologia": "serpentina",
        "descripcion": "Estela lineal alargada típica de descarga ilegal de sentina con el buque en movimiento.",
        "barcos": [
            {"mmsi": "MMSI-224891000", "nombre": "MT IBERIAN STAR", "tipo": "Oil Tanker", "vel": 14.2, "offset": (0.00, 0.00)},
            {"mmsi": "MMSI-351772000", "nombre": "MV MEDITERRANEAN EXPRESS", "tipo": "Container Ship", "vel": 18.5, "offset": (0.18, -0.12)},
            {"mmsi": "MMSI-224009911", "nombre": "FV ALBORÁN UNO", "tipo": "Fishing Vessel", "vel": 6.4, "offset": (-0.25, 0.20)}
        ]
    },
    "ESCENA 02 // Golfo de México (Lavado de Tanques Pesado)": {
        "archivo": "escena_02_tanques.tif",
        "lon_origen": -90.50, "lat_origen": 27.80,
        "semilla": 108, "tipo_morfologia": "doble_lobulo",
        "descripcion": "Vertido masivo bifurcado en dos grandes lóbulos de emulsión pesada (E60/E80) por purga de tanques.",
        "barcos": [
            {"mmsi": "MMSI-538004112", "nombre": "MT GULF PIONEER", "tipo": "Crude Oil Tanker", "vel": 11.0, "offset": (0.01, -0.01)},
            {"mmsi": "MMSI-367119840", "nombre": "OSV DEEPWATER SUPPORT", "tipo": "Offshore Supply", "vel": 9.5, "offset": (-0.15, -0.18)},
            {"mmsi": "MMSI-311002300", "nombre": "MV CARIBBEAN TRADER", "tipo": "Bulk Carrier", "vel": 13.1, "offset": (0.28, 0.15)}
        ]
    },
    "ESCENA 03 // Mar del Norte (Fuga Fragmentada por Vórtices)": {
        "archivo": "escena_03_fuga_plataforma.tif",
        "lon_origen": 2.10, "lat_origen": 58.40,
        "semilla": 777, "tipo_morfologia": "vortice",
        "descripcion": "Pluma en espiral altamente fragmentada en múltiples manchas satélite por corrientes de marea.",
        "barcos": [
            {"mmsi": "MMSI-257991400", "nombre": "MT NORDIC VALKYRIE", "tipo": "Shuttle Tanker", "vel": 12.6, "offset": (-0.01, 0.01)},
            {"mmsi": "MMSI-235088123", "nombre": "MV CALEDONIA GUARD", "tipo": "Standby Vessel", "vel": 8.0, "offset": (0.12, 0.14)},
            {"mmsi": "MMSI-219004511", "nombre": "FV SKAGERRAK", "tipo": "Pelagic Trawler", "vel": 7.2, "offset": (-0.22, -0.19)}
        ]
    }
}

def construir_geotiff_escena(info_escena):
    """Crea el archivo .tif físico en el disco si no existe, con formas orgánicas únicas."""
    ruta_completa = os.path.join(CARPETA_BASE, info_escena["archivo"])
    if os.path.exists(ruta_completa):
        return ruta_completa

    np.random.seed(info_escena["semilla"])
    h, w = 450, 450
    y, x = np.mgrid[:h, :w]

    # Fondo marino base con ondas capilares
    ruido_mar = gaussian_filter(np.random.randn(h, w), sigma=22)
    ruido_mar = (ruido_mar - ruido_mar.min()) / (ruido_mar.max() - ruido_mar.min())
    datos = np.random.normal(165, 14, (h, w)) + (ruido_mar * 20)

    # Turbulencia fractal multiescala
    t_gruesa = gaussian_filter(np.random.randn(h, w), sigma=14)
    t_gruesa = (t_gruesa - t_gruesa.mean()) / t_gruesa.std()
    t_fina = gaussian_filter(np.random.randn(h, w), sigma=4)
    t_fina = (t_fina - t_fina.mean()) / t_fina.std()

    morf = info_escena["tipo_morfologia"]
    if morf == "serpentina":
        ang = np.deg2rad(32)
        xr = (x - 225)*np.cos(ang) + (y - 225)*np.sin(ang)
        yr = -(x - 225)*np.sin(ang) + (y - 225)*np.cos(ang)
        yr_c = yr + 22 * np.sin(xr / 34.0) + 10 * np.cos(xr / 13.0)
        ancho = 22 + 14 * np.exp(-((xr + 45) / 85)**2)
        dist = np.sqrt((xr / 160)**2 + (yr_c / ancho)**2)
    elif morf == "doble_lobulo":
        d1 = np.sqrt(((x - 175)/75)**2 + ((y - 190)/42)**2)
        d2 = np.sqrt(((x - 275)/85)**2 + ((y - 255)/36)**2)
        puente = np.sqrt(((x - 225)/60)**2 + ((y - 220)/20)**2)
        dist = np.minimum(np.minimum(d1, d2), puente * 1.15)
    else:  # vortice
        dx, dy = x - 225, y - 225
        r = np.sqrt(dx**2 + dy**2) + 1e-5
        theta = np.arctan2(dy, dx) + (r / 58.0)
        espiral_x = r * np.cos(theta)
        espiral_y = r * np.sin(theta)
        d_principal = np.sqrt((espiral_x / 115)**2 + (espiral_y / 32)**2)
        d_satelite = np.sqrt(((x - 320)/42)**2 + ((y - 135)/24)**2)
        dist = np.minimum(d_principal, d_satelite)

    campo = dist - (0.35 * t_gruesa) - (0.16 * t_fina)

    datos[campo < 1.05] = np.random.normal(88, 8, np.sum(campo < 1.05))
    datos[campo < 0.74] = np.random.normal(54, 6, np.sum(campo < 0.74))
    datos[campo < 0.44] = np.random.normal(24, 4, np.sum(campo < 0.44))

    datos = np.clip(gaussian_filter(datos, sigma=0.8), 1, 255).astype('uint8')
    transform = from_origin(info_escena["lon_origen"], info_escena["lat_origen"], 0.004, 0.004)

    with rio.open(
        ruta_completa, 'w', driver='GTiff', height=h, width=w,
        count=1, dtype='uint8', crs='EPSG:4326', transform=transform
    ) as dst:
        dst.write(datos, 1)

    return ruta_completa

# Asegurar que los 3 archivos .tif existen al iniciar
for clave, meta in CATALOGO_ESCENAS.items():
    construir_geotiff_escena(meta)
    # También mantener productOverview.tif sincronizado con la primera escena
    if meta["archivo"] == "escena_01_sentina.tif":
        ruta_legacy = os.path.join(CARPETA_BASE, "productOverview.tif")
        if not os.path.exists(ruta_legacy):
            with rio.open(os.path.join(CARPETA_BASE, meta["archivo"])) as s:
                perfil = s.profile
                arr = s.read(1)
            with rio.open(ruta_legacy, 'w', **perfil) as d:
                d.write(arr, 1)

# =====================================================================
# 3. SIMULACIÓN FÍSICA REACTIVA EN VIVO (VIENTO, OLAS Y RUIDO)
# =====================================================================
def aplicar_fisica_viento_en_vivo(datos_base, viento_ms, sigma_filtro):
    """
    Modifica dinámicamente la matriz SAR según el viento seleccionado para que el usuario
    vea cómo cambia la imagen en tiempo real:
    - Viento < 4 m/s: Sombras oscuras de calma eólica invaden el mar (Falsos Positivos).
    - Viento 5.5 - 10.8 m/s: Contraste limpio óptimo.
    - Viento > 11 m/s: El oleaje brillante erosiona y mezcla la mancha (Falsos Negativos).
    """
    h, w = datos_base.shape
    np.random.seed(99)
    sar_mod = datos_base.astype(float).copy()

    if viento_ms < 4.5:
        # Generar parches oscuros de mar en calma (look-alikes) que crecen al bajar el viento
        intensidad_calma = (4.5 - viento_ms) / 4.0
        parches = gaussian_filter(np.random.randn(h, w), sigma=32)
        parches = (parches - parches.min()) / (parches.max() - parches.min())
        zonas_calma = parches > (1.0 - 0.55 * intensidad_calma)
        sar_mod[zonas_calma] = sar_mod[zonas_calma] * (1.0 - 0.68 * intensidad_calma)
        # Reducir el brillo general del mar por falta de ondas Bragg
        sar_mod = sar_mod * (0.65 + 0.35 * (viento_ms / 4.5))

    elif viento_ms > 10.8:
        # El oleaje intenso dispersa los bordes de la mancha y añade ruido de cresta blanca
        exceso_viento = (viento_ms - 10.8) / 7.2
        ruido_olas = np.random.normal(0, 28 * exceso_viento, (h, w))
        # El agua agitada invade la mancha oscura subiendo su backscatter
        es_mancha = sar_mod < 110
        sar_mod[es_mancha] = sar_mod[es_mancha] + (62.0 * exceso_viento)
        sar_mod = sar_mod + ruido_olas

    sar_mod = np.clip(sar_mod, 1, 255)
    sar_suavizado = gaussian_filter(sar_mod, sigma=sigma_filtro)
    return sar_mod.astype('uint8'), sar_suavizado

def clasificar_espesor(sar_suavizado, umbral_base):
    clases = np.zeros_like(sar_suavizado, dtype='uint8')
    clases[(sar_suavizado < umbral_base) & (sar_suavizado >= umbral_base - 25)] = 1
    clases[(sar_suavizado < umbral_base - 25) & (sar_suavizado >= umbral_base - 48)] = 2
    clases[sar_suavizado < umbral_base - 48] = 3
    return clases

def evaluar_ventana_beaufort(viento_ms):
    if viento_ms < 3.5:
        return "CALMA CRÍTICA (<3.5 m/s)", 0.25, "[ALERTA FALSO POSITIVO] El mar sin viento carece de ondas capilares y se vuelve negro en la imagen SAR, generando falsas alarmas masivas."
    elif 3.5 <= viento_ms < 5.5:
        return "SUBÓPTIMO (Fuerza 3)", 0.68, "[PRECAUCIÓN] Empiezan a aparecer sombras oscuras de viento bajo en los bordes de la escena."
    elif 5.5 <= viento_ms <= 10.8:
        return "ÓPTIMO (Beaufort 4-5)", 0.96, "[VENTANA NOMINAL] Contraste radiométrico limpio. La rugosidad del mar permite aislar la mancha con máxima precisión."
    else:
        return "TEMPORAL (>10.8 m/s)", 0.40, "[ALERTA FALSO NEGATIVO] El oleaje rompe la película superficial y mezcla el hidrocarburo, borrando la mancha del radar."

def extraer_poligono_y_area(mascara_binaria, transform):
    poligonos = [shape(geom) for geom, val in shapes(mascara_binaria, mask=(mascara_binaria == 1), transform=transform) if val == 1]
    if not poligonos:
        return gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:4326"), 0.0
    gdf = gpd.GeoDataFrame(geometry=poligonos, crs="EPSG:4326")
    gdf['area_deg'] = gdf.geometry.area
    gdf = gdf[gdf['area_deg'] > 0.00015].sort_values(by='area_deg', ascending=False).iloc[:8]
    if gdf.empty:
        return gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:4326"), 0.0
    area_km2 = round(gdf.to_crs(epsg=3857).geometry.area.sum() / 1e6, 2)
    return gdf, area_km2

def simular_ais_dinamico(bounds, centroide, dir_viento, horas_retro, viento_ms, meta_barcos):
    """Mueve dinámicamente el origen estimado según dirección, horas y velocidad de viento."""
    cx, cy = centroide.x, centroide.y
    rad = np.deg2rad(dir_viento)
    # Distancia recorrida por la mancha (~3% de la velocidad del viento)
    factor_distancia = 0.025 * (horas_retro / 6.0) * (max(2.0, viento_ms) / 7.5)
    ox = cx - np.sin(rad) * factor_distancia
    oy = cy - np.cos(rad) * factor_distancia

    # Punto base de referencia para las rutas fijas de esa escena
    ref_x = (bounds.left + bounds.right) / 2.0
    ref_y = (bounds.bottom + bounds.top) / 2.0

    flota = []
    for idx, b in enumerate(meta_barcos):
        off_x, off_y = b["offset"]
        px, py = ref_x + off_x, ref_y + off_y
        if idx == 0:
            linea = LineString([(bounds.left + 0.05, bounds.bottom + 0.1), (px, py), (bounds.right - 0.05, bounds.top - 0.1)])
        elif idx == 1:
            linea = LineString([(bounds.left + 0.05, py + 0.25), (px, py), (bounds.right - 0.05, py - 0.20)])
        else:
            linea = LineString([(px - 0.15, bounds.top - 0.05), (px, py), (px + 0.15, bounds.bottom + 0.05)])

        flota.append({
            "mmsi": b["mmsi"],
            "nombre": b["nombre"],
            "tipo": b["tipo"],
            "vel": b["vel"],
            "hora_paso": f"T-{round(horas_retro * (0.45 + idx*0.22), 1)}h",
            "geometry": linea
        })

    gdf_flota = gpd.GeoDataFrame(flota, crs="EPSG:4326")
    linea_deriva = LineString([(ox, oy), (cx, cy)])
    return gdf_flota, Point(ox, oy), linea_deriva

# =====================================================================
# 4. BARRA LATERAL INTERACTIVA (CONTROLES CON EFECTO VISUAL EN VIVO)
# =====================================================================
with st.sidebar:
    st.markdown("### `// 1. SELECCIÓN DE ARCHIVO .TIF`")
    nombre_escena = st.selectbox(
        "Escena Satelital Activa:",
        list(CATALOGO_ESCENAS.keys())
    )
    meta_actual = CATALOGO_ESCENAS[nombre_escena]
    st.caption(f"📄 Archivo cargado: `{meta_actual['archivo']}`")
    st.caption(meta_actual["descripcion"])

    st.markdown("---")
    st.markdown("### `// 2. FÍSICA DE VIENTO (REACTIVO)`")
    viento_ms = st.slider(
        "Velocidad del Viento (m/s):", 0.5, 18.0, 7.5, 0.5,
        help="¡Pruébalo! Baja de 3.5 m/s para ver cómo aparecen falsos positivos oscuros, o sube de 11 m/s para ver cómo las olas borran la mancha."
    )
    dir_viento = st.slider(
        "Rumbo de Empuje Viento/Corriente (°):", 0, 360, 135, 15,
        help="Rota en vivo el vector de deriva y el círculo de búsqueda en el mapa."
    )

    st.markdown("---")
    st.markdown("### `// 3. CALIBRACIÓN DEL DETECTOR IA`")
    umbral_ia = st.slider("Corte Backscatter (Sensibilidad):", 45, 145, 105, 5)
    sigma_ia = st.slider("Filtro Anti-Speckle (Suavizado Lee):", 0.5, 5.0, 1.8, 0.3)
    horas_ais = st.slider("Ventana Retrospectiva AIS (Horas):", 2, 24, 10, 2)

# =====================================================================
# 5. EJECUCIÓN DEL MOTOR REACTIVO
# =====================================================================
ruta_tif_actual = os.path.join(CARPETA_BASE, meta_actual["archivo"])
with rio.open(ruta_tif_actual) as src:
    datos_base_tif = src.read(1)
    transform = src.transform
    bounds = src.bounds

# Aplicar efectos dinámicos del viento y suavizado sobre los píxeles
datos_sar_vivo, sar_suavizado = aplicar_fisica_viento_en_vivo(datos_base_tif, viento_ms, sigma_ia)
mascara_binaria = (sar_suavizado < umbral_ia).astype('uint8')
mapa_espesor = clasificar_espesor(sar_suavizado, umbral_ia)

estado_viento, factor_viento, texto_viento = evaluar_ventana_beaufort(viento_ms)
gdf_mancha, area_total_km2 = extraer_poligono_y_area(mascara_binaria, transform)

proporcion_emulsion = np.sum(mapa_espesor >= 2) / max(1, np.sum(mapa_espesor >= 1))
area_emulsion_km2 = round(area_total_km2 * proporcion_emulsion, 2)
confianza_ia = round(min(98.0, 90.0 * factor_viento), 1) if area_total_km2 > 0 else 0.0

if not gdf_mancha.empty:
    centroide = gdf_mancha.geometry.iloc[0].centroid
    gdf_ais, origen_estimado, vector_deriva = simular_ais_dinamico(
        bounds, centroide, dir_viento, horas_ais, viento_ms, meta_actual["barcos"]
    )
    radio_buffer = 0.08 + (0.012 * horas_ais)
    buffer_origen = origen_estimado.buffer(radio_buffer)
    gdf_ais['distancia_km'] = (gdf_ais.geometry.distance(origen_estimado) * 111.0).round(1)
    gdf_ais['en_zona_origen'] = gdf_ais.geometry.intersects(buffer_origen)
else:
    gdf_ais = gpd.GeoDataFrame()

# =====================================================================
# 6. CABECERA Y CUADRO DE MANDO DINÁMICO
# =====================================================================
st.markdown(f"""
<div class="terminal-header">
    <span class="sys-badge">NASA NISAR L-BAND SAR // ARCHIVO ACTIVO: {meta_actual['archivo'].upper()}</span>
    <div class="sys-title">OCEANGUARDIAN_AI</div>
    <div class="sys-subtitle">
        Simulador interactivo de respuesta radiométrica SAR ante viento capilar, segmentación multicapa de hidrocarburos y retro-proyección vectorial de tráfico AIS.
    </div>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-lbl">ÁREA ANOMALÍA DETECTADA</div>
        <div class="kpi-val">{area_total_km2} km²</div>
        <div class="kpi-lbl">EMULSIÓN E60/E80: {area_emulsion_km2} km²</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-lbl">CONFIANZA DEL DETECTOR IA</div>
        <div class="kpi-val">{confianza_ia}%</div>
        <div class="kpi-lbl">{estado_viento} ({viento_ms} m/s)</div>
    </div>""", unsafe_allow_html=True)
with k3:
    n_sospechosos = int(gdf_ais['en_zona_origen'].sum()) if not gdf_ais.empty else 0
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-lbl">BUQUES EN BUFFER (-{horas_ais}H)</div>
        <div class="kpi-val">{n_sospechosos} OBJETIVOS</div>
        <div class="kpi-lbl">DERIVA RUMBO {dir_viento}°</div>
    </div>""", unsafe_allow_html=True)
with k4:
    porcentaje_mar_oscuro = round((np.sum(mascara_binaria == 1) / mascara_binaria.size) * 100, 1)
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-lbl">FRACCIÓN DE PÍXELES OSCUROS</div>
        <div class="kpi-val">{porcentaje_mar_oscuro}%</div>
        <div class="kpi-lbl">FILTRO SPECKLE SIGMA: {sigma_ia}</div>
    </div>""", unsafe_allow_html=True)

st.write("")

# =====================================================================
# 7. VISTA INTERACTIVA INTEGRADA (GRÁFICOS SAR + MAPA EN LA MISMA PANTALLA)
# =====================================================================
vista_activa = st.radio(
    "SELECCIÓN DE MODO DE PANTALLA:",
    [
        "⚡ MODO CENTRO DE MANDO (Visor SAR + Mapa Táctico AIS Simultáneos)",
        "🔬 MODO LABORATORIO SAR (Comparador a Pantalla Completa + Histograma Radiométrico)",
        "📖 DOCUMENTACIÓN CIENTÍFICA NISAR & ESCALA BEAUFORT"
    ],
    horizontal=True
)

cmap_matrix = ListedColormap(['#050505', '#004D26', '#00CC52', '#B8FFDA'])

if "CENTRO DE MANDO" in vista_activa:
    col_izq, col_der = st.columns([1.15, 1.25])

    with col_izq:
        st.markdown('<div class="panel-section">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">01 // Respuesta SAR en Tiempo Real & Segmentación IA</div>', unsafe_allow_html=True)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.7))
        fig.patch.set_facecolor('#090D09')
        
        ax1.imshow(datos_sar_vivo, cmap='Greys_r', vmin=1, vmax=255)
        ax1.set_title(f"SAR L-BAND (Viento: {viento_ms} m/s)", color='#E0E6ED', fontsize=9.5, fontfamily='monospace')
        ax1.axis('off')
        
        ax2.imshow(mapa_espesor, cmap=cmap_matrix, vmin=0, vmax=3)
        ax2.set_title(f"MÁSCARA IA (Corte: {umbral_ia} | σ: {sigma_ia})", color='#00FF66', fontsize=9.5, fontfamily='monospace')
        ax2.axis('off')
        plt.tight_layout()
        st.pyplot(fig)

        st.markdown(f"""<div class="tech-note">
        <strong>DIAGNÓSTICO FÍSICO EN VIVO:</strong><br>{texto_viento}
        </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_der:
        st.markdown('<div class="panel-section">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">02 // Mapa de Deriva Retrospectiva & Cruce AIS</div>', unsafe_allow_html=True)
        
        if not gdf_mancha.empty:
            m = folium.Map(location=[centroide.y, centroide.x], zoom_start=9, tiles="CartoDB dark_matter")
            
            # 1. Círculo de origen retrospectivo (se mueve al cambiar rumbo, viento u horas)
            folium.GeoJson(
                gpd.GeoSeries([buffer_origen], crs="EPSG:4326").to_json(),
                name=f"Zona Origen Estimada (-{horas_ais}h)",
                style_function=lambda x: {
                    'fillColor': '#00FF66', 'color': '#00FF66',
                    'weight': 2.0, 'dashArray': '6, 6', 'fillOpacity': 0.12
                },
                tooltip=f"Zona de búsqueda retrospectiva T-{horas_ais}h (Rumbo deriva: {dir_viento}°)"
            ).add_to(m)

            # 2. Vector de deriva (Línea que une el origen estimado con la posición actual de la mancha)
            folium.GeoJson(
                gpd.GeoSeries([vector_deriva], crs="EPSG:4326").to_json(),
                name="Vector de Deriva Marina",
                style_function=lambda x: {'color': '#B8FFDA', 'weight': 2.5, 'dashArray': '4, 8'},
                tooltip=f"Trayectoria de deriva estimada ({dir_viento}°)"
            ).add_to(m)

            # 3. Mancha detectada en vivo
            folium.GeoJson(
                gdf_mancha.to_json(),
                name="Anomalía SAR Detectada",
                style_function=lambda x: {
                    'fillColor': '#00FF66', 'color': '#B8FFDA',
                    'weight': 1.8, 'fillOpacity': 0.65
                },
                tooltip=f"Superficie: {area_total_km2} km²"
            ).add_to(m)

            # 4. Trayectorias AIS
            for _, barco in gdf_ais.iterrows():
                es_comp = barco['en_zona_origen']
                color_linea = "#00FF66" if es_comp else "#3B4252"
                peso = 3.8 if es_comp else 1.8
                folium.GeoJson(
                    gpd.GeoSeries([barco['geometry']], crs="EPSG:4326").to_json(),
                    name=f"AIS: {barco['nombre']}",
                    style_function=lambda x, c=color_linea, w=peso: {'color': c, 'weight': w},
                    tooltip=f"{barco['nombre']} | Dist. al origen: {barco['distancia_km']} km"
                ).add_to(m)

            folium.LayerControl().add_to(m)
            st_folium(m, width=680, height=380)
        else:
            st.warning("Umbral demasiado bajo: ninguna anomalía seleccionada.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabla dinámica de embarcaciones y Alerta inferior
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">03 // Telemetría AIS & Alerta Explicable en Tiempo Real</div>', unsafe_allow_html=True)
    
    c_ais1, c_ais2, c_ais3 = st.columns(3)
    for col_ui, (_, b) in zip([c_ais1, c_ais2, c_ais3], gdf_ais.iterrows()):
        with col_ui:
            estado_b = "🟢 **[COINCIDENCIA EN ORIGEN]**" if b['en_zona_origen'] else "⚫ **[DESCARTADO POR DERIVA]**"
            st.markdown(f"""
            **`{b['nombre']}`** (`{b['mmsi']}`)  
            {estado_b}  
            • **Tipo:** {b['tipo']} ({b['vel']} kn)  
            • **Distancia al centro de origen:** `{b['distancia_km']} km`  
            • **Paso estimado:** `{b['hora_paso']}`
            """)
    st.markdown('</div>', unsafe_allow_html=True)

elif "LABORATORIO SAR" in vista_activa:
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Inspección Radiométrica Detallada e Histograma de Corte</div>', unsafe_allow_html=True)
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.8))
    fig.patch.set_facecolor('#090D09')
    
    ax1.imshow(datos_sar_vivo, cmap='Greys_r', vmin=1, vmax=255)
    ax1.set_title("1. SAR L-BAND CON FÍSICA DE VIENTO", color='#E0E6ED', fontfamily='monospace')
    ax1.axis('off')
    
    ax2.imshow(mapa_espesor, cmap=cmap_matrix, vmin=0, vmax=3)
    ax2.set_title("2. SEGMENTACIÓN MULTICAPA DE EMULSIÓN", color='#00FF66', fontfamily='monospace')
    ax2.axis('off')
    
    # Histograma en vivo con la línea de corte
    ax3.set_facecolor('#050505')
    ax3.hist(sar_suavizado.ravel(), bins=50, color='#004D26', edgecolor='#00FF66', alpha=0.85)
    ax3.axvline(umbral_ia, color='#B8FFDA', linestyle='--', linewidth=2, label=f'Corte IA ({umbral_ia})')
    ax3.set_title("3. HISTOGRAMA BACKSCATTER EN VIVO", color='#00FF66', fontfamily='monospace')
    ax3.tick_params(colors='#8B949E')
    ax3.legend(facecolor='#090D09', labelcolor='#00FF66')
    
    plt.tight_layout()
    st.pyplot(fig)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="panel-section">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Documentación Científica NISAR & Escala de Viento de Beaufort</div>', unsafe_allow_html=True)
    st.markdown("""
    * **Escena 01 (`escena_01_sentina.tif`):** Descarga operativa en ruta comercial en el Estrecho de Gibraltar. Morfología lineal curvada por corrientes superficiales.
    * **Escena 02 (`escena_02_tanques.tif`):** Lavado ilegal de tanques en el Golfo de México. Presenta dos lóbulos densos con núcleos de emulsión agua-en-aceite (E60/E80).
    * **Escena 03 (`escena_03_fuga_plataforma.tif`):** Fuga en el Mar del Norte sometida a cizalladura de corriente y vórtices, fragmentando la mancha en múltiples islas.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
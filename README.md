# NASA-SPACEAPPS-2026
# 🛰️ NISAR-GUARD IA (OceanGuardian)
**Estación Operativa de Vigilancia Oceánica SAR Banda-L y Trazabilidad AIS**  
*NASA Space Apps Challenge 2026 · Detect the Invisible. Protect the Ocean.*

---

## 1. Descripción del Proyecto
**NISAR-GUARD IA** es una plataforma web interactiva de vigilancia ambiental marítima diseñada para detectar vertidos ilegales de hidrocarburos (aguas de sentina, purgas de combustible y lavado de tanques) utilizando datos de **Radar de Apertura Sintética (SAR) en Banda-L (1.257 GHz, λ = 23.84 cm)** de la misión **NASA/ISRO NISAR**, combinados con inteligencia artificial explicable y reconstrucción de tráfico marítimo **AIS**.

A diferencia de los sensores ópticos, que quedan bloqueados por las nubes o la oscuridad nocturna, el radar SAR mide la rugosidad capilar del océano (dispersión de Bragg), permitiendo identificar películas superficiales las 24 horas del día.

---

## 2. Metodología: Del Tutorial Base (QGIS y Python) a la Aplicación Web

Para construir este prototipo seguimos y ampliamos el flujo de trabajo oficial del tutorial de SAR del reto:

### Fase 1: Inspección Geoespacial y Validación en QGIS (Opción 1 del Tutorial)
1. **Generación y carga de datos Raster (`.tif`) y Vectoriales (`.shp`):** Se procesaron escenas GeoTIFF (`productOverview.tif`, `escena_01_sentina.tif`, `escena_02_tanques.tif`, `escena_03_fuga_plataforma.tif`) en proyección `EPSG:4326` junto con polígonos de límites marítimos (`mapa_fronteras.shp`).
2. **Comprobación visual en QGIS Desktop:** Arrastramos las capas `.tif` y `.shp` al lienzo de QGIS para verificar la alineación del Sistema de Referencia de Coordenadas (CRS), inspeccionar los niveles digitales de retrodispersión (backscatter) y ajustar la simbología transparente de las fronteras sobre las anomalías oscuras.

### Fase 2: Procesamiento Científico en Python (Opción 2 del Tutorial)
1. **Entorno Geoespacial Conda (`sar_env`):** Configuramos en Windows un entorno precompilado mediante `conda-forge` con `gdal`, `rasterio`, `geopandas`, `scipy`, `cartopy` y `matplotlib`.
2. **Lectura de Metadatos y Matrices SAR:** Utilizamos `gdal.Open()` y `rasterio.open()` para extraer la transformación geográfica (`GeoTransform`), aplicar filtrado espacial anti-speckle y segmentar las zonas de amortiguación capilar de Marangoni ($\Delta\sigma^0$).

### Fase 3: Estación Operativa Interactiva en Streamlit (`app.py`)
Transformamos los scripts estáticos de Jupyter Notebook en una consola operativa completa en tiempo real que integra:
* **Visor SAR Polarimétrico Multicapa:** Conmutación en vivo entre $\sigma^0_{HH}$ [dB], $\sigma^0_{HV}$ [dB], Ratio HH/HV, Entropía Polarimétrica de Cloude-Pottier ($H$) y máscara de segmentación **U-Net**.
* **Transepto Radiométrico Interactivo ($A - A'$):** Herramienta arrastrable sobre el lienzo SAR que muestrea en tiempo real la caída en decibelios ($\Delta\sigma^0$) respecto al nivel base del mar ($\sigma^0_{\text{mar}}$) y el suelo de ruido térmico (**NESZ = -27.5 dB**).
* **Descriptores Texturales GLCM y Explicabilidad SHAP ($\phi_i$):** Diferenciación automática entre vertidos reales de hidrocarburos (ej. Estrecho de Gibraltar y Corredor de Fisterra) y falsos positivos (*look-alikes*) por sombras de viento costeras o afloramientos biogénicos de fitoplancton (Mar Cantábrico).
* **Inversión de Deriva Metoceánica y Cruce AIS:** Retrocálculo vectorial ($V_{\text{deriva}} = V_{\text{curr}} + 0.03 \cdot W_{10}$) para estimar el punto de descarga ($T_0 - \Delta t$) y calcular la distancia de aproximación más cercana (**CPA**) de los buques en tránsito.
* **Boletín Operativo Nivel-2:** Generación y exportación instantánea de informes técnicos estandarizados para guardacostas y agencias marítimas (EMSA / CleanSeaNet).

---

## 3. Cómo ejecutar el proyecto en local

```bash
conda activate sar_env
pip install -r requirements.txt
streamlit run app.py

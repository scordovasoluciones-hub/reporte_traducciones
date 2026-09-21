# Reporte de Traducciones — Engagement (SDS) · Compassion Perú

Dashboard estático (HTML + Chart.js) que se genera desde el CSV histórico de traducciones
y se hospeda en GitHub Pages (repo público, cuenta personal) para incrustarse en el
Engagement Site de SharePoint.

## Estructura

    datos/            <- CSV histórico (el script toma el más reciente) y presupuesto.xlsx
                         con la hoja "PagoTraducciones" (opcional: si no está, se omite la
                         pestaña Presupuesto). Ambos viven en el repo — ver "Refresco mensual".
    generar.py        <- lee el CSV y el Excel de presupuesto, valida calidad de dato,
                         exporta los datos GRANULARES de ambas fuentes
    plantilla.html    <- plantilla del dashboard (token __DATA__ + motor de cálculo en JS)
    salida/           <- generado: index.html (lo que se despliega) + datos.json
    staticwebapp.config.json  <- headers de Azure (sin usar mientras se hospede en GitHub Pages;
                                  queda listo por si más adelante se consigue una suscripción de Azure)
    requirements.txt

Desde esta versión, `generar.py` **ya no calcula** KPIs/estacionalidad/proyección — solo
valida el CSV y exporta los datos agrupados a nivel mes+proveedor+traductor+plantilla.
Todo el cálculo (KPIs, estacionalidad, proyección, filtros) vive en JavaScript dentro de
`plantilla.html`, para que el mismo motor sirva tanto para la vista publicada como para
los filtros y la vista previa de un Excel nuevo cargado en el navegador.

## Funciones del dashboard

- **Pestañas**: "Reporte de Traducciones" (histórico + proyección) y "Presupuesto" (budget,
  pagos y licencias) — mismo link, se cambia con los botones de arriba a la derecha.
- **Panel de indicadores y filtros plegable**: el botón "Plegar/Desplegar" oculta los KPIs y
  filtros para dar más espacio a las gráficas, sobre todo en pantallas anchas/horizontales.
- **Filtros del Reporte** (arriba, plegable): rango de año fiscal, mes fiscal, proveedor,
  traductor y plantilla. Se pueden combinar; todas las gráficas y KPIs se recalculan al vuelo.
  El filtro de mes aplica a todo, incluida "Traductores por volumen", que muestra a **todos**
  los traductores del periodo filtrado (no solo los top) para detectar caídas puntuales de
  productividad en un mes específico.
- **Proyección FY**: gráfica + tabla numérica mes a mes, con 5 escenarios de productividad
  (1000/1500/2000/2500/3000 trad/mes) y un campo para simular un objetivo anual distinto sin
  tocar código.
- **Calidad esperada**: estimado de % de issues y % de devoluciones para el próximo FY,
  basado en el perfil estacional histórico de calidad (no es un modelo predictivo).
- **Pestaña Presupuesto**: KPIs (budget, pago ejecutado, % ejecución, cartas traducidas, costo
  promedio por carta, costo de licencias), budget vs. pago real por mes, costo por carta en el
  tiempo, pago por Tipo Traductor por año fiscal, y licencias (cantidad y costo). Filtros propios
  de FY y Tipo Traductor. Fuente independiente del reporte de traducciones (no se cruzan).
- **Cargar Excel/CSV** (vista previa, en cada pestaña): botón junto a los filtros para revisar
  cómo se vería el dashboard con datos nuevos, sin publicar nada — solo se ve en tu navegador.

## Refresco mensual — publicar para todos (sin Python, sin terminal)

El CSV y el Excel de presupuesto viven **dentro del repositorio** (`datos/`), y GitHub
Actions corre `generar.py` automáticamente en cada push a `main`. Actualizar es así:

    1. Antes de subir, usa el botón "Cargar Excel" en el propio dashboard para previsualizar
       el mes nuevo en tu navegador y confirmar que se ve bien (no publica nada todavía).
    2. En github.com, entra a la carpeta datos/.
    3. "Add file" -> "Upload files" -> arrastra el CSV (y/o presupuesto.xlsx) actualizado
       -> "Commit changes" directo a main.

En ~1 minuto, la pestaña "Actions" del repo muestra el build corriendo y el sitio queda
publicado con los datos nuevos. No hace falta instalar nada ni tocar la terminal.

Si prefieres seguir el camino local (útil para depurar), sigue funcionando igual:
`python generar.py` y luego `git add -A && git commit -m "..." && git push`.

El script imprime alertas de calidad del dato (outliers, meses faltantes, anomalías de
registro) y las muestra dentro del propio reporte; la carga de Excel en el navegador
calcula las mismas alertas para el archivo que subas.

## Supuestos configurables

Al inicio de `generar.py`:
- `PRODUCTIVIDADES` / `PROD_DEFAULT` — traducciones por traductor/mes (escenarios del selector;
  hoy 1000/1500/2000/2500/3000, por defecto 2000).
- `VOLUMEN_ANUAL_OBJ` / `CRECIMIENTO` — objetivo anual de la proyección (el usuario puede
  además ajustarlo temporalmente desde la propia página, sin tocar el script).
- `UMBRAL_ISSUES_ALTA` — % que marca una plantilla como crítica.

## Incrustar en SharePoint

1. El sitio queda publicado en `https://<usuario>.github.io/<repo>/` (HTTPS, GitHub Pages).
2. En SharePoint: Configuración -> Información del sitio -> Ver toda la configuración ->
   Seguridad de campos HTML -> agrega el dominio `github.io` (o la URL completa) a la lista permitida.
3. En la página: + -> elemento web "Insertar" -> pega la URL de GitHub Pages.

GitHub Pages no permite restringir por header quién puede incrustar la página (a diferencia
de Azure Static Web Apps), así que la URL es pública para cualquiera que la tenga — ver
"Notas de gobernanza" abajo.

## Notas de gobernanza

Es data organizacional (volúmenes, calidad, traductores y presupuesto de Compassion Perú).
El repo es público: cualquiera puede ver el dashboard publicado, **y también** entrar al
repositorio y descargar el CSV y el Excel de presupuesto tal cual (`datos/`), no solo verlos
procesados. Esto es una decisión consciente (se prioriza el self-service de actualizar sin
Python/terminal) — si más adelante deja de ser aceptable, las alternativas son: repo privado +
GitHub Pro, Cloudflare Pages + Cloudflare Access (gratis, con login), o Azure Static Web Apps
dentro del tenant de Compassion (usa `staticwebapp.config.json`, ya listo en este repo).
El dashboard es un snapshot: refleja el CSV con que se generó, no se conecta en vivo a Connect.
Para datos en vivo con refresco automático, la vía nativa es Power BI sobre el mismo SharePoint.

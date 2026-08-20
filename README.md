# Reporte de Traducciones — Engagement (SDS) · Compassion Perú

Dashboard estático (HTML + Chart.js) que se genera desde el CSV histórico de traducciones
y se hospeda en GitHub Pages (repo público, cuenta personal) para incrustarse en el
Engagement Site de SharePoint.

## Estructura

    datos/            <- coloca aquí el CSV histórico (el script toma el más reciente)
    generar.py        <- lee el CSV, valida calidad de dato, exporta los datos GRANULARES
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

- **Filtros** (arriba del todo): rango de año fiscal, proveedor, traductor y plantilla.
  Se pueden combinar; todas las gráficas y KPIs se recalculan al vuelo.
- **Proyección FY**: gráfica + tabla numérica mes a mes, con 3 escenarios de productividad
  (500/560/600 trad/mes) y un campo para simular un objetivo anual distinto sin tocar código.
- **Calidad esperada**: estimado de % de issues y % de devoluciones para el próximo FY,
  basado en el perfil estacional histórico de calidad (no es un modelo predictivo).
- **Cargar Excel/CSV** (vista previa): botón junto a los filtros para revisar cómo se vería
  el dashboard con un mes nuevo, sin publicar nada — solo se ve en tu navegador.

## Refresco mensual — publicar para todos (3 pasos)

    1. Reemplaza el CSV en datos/ por la base actualizada.
    2. python generar.py
    3. git add -A && git commit -m "Actualiza datos a <mes>" && git push

Con el flujo de CI en GitHub Actions, el push ya deja publicada la nueva versión.
Antes de este paso puedes usar el botón "Cargar Excel" en el propio dashboard para
previsualizar el mes nuevo y confirmar que se ve bien.

El script imprime alertas de calidad del dato (outliers, meses faltantes, anomalías de
registro) y las muestra dentro del propio reporte; la carga de Excel en el navegador
calcula las mismas alertas para el archivo que subas.

## Supuestos configurables

Al inicio de `generar.py`:
- `PRODUCTIVIDADES` / `PROD_DEFAULT` — traducciones por traductor/mes (escenarios del selector).
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

Es data organizacional (volúmenes, calidad y traductores de Compassion Perú). Al estar en
un repo público de GitHub y sin muro de acceso, la URL publicada es visible para cualquiera
que la obtenga. Si esto deja de ser aceptable, las alternativas son: repo privado + GitHub
Pro, Cloudflare Pages + Cloudflare Access (gratis, con login), o Azure Static Web Apps dentro
del tenant de Compassion (usa `staticwebapp.config.json`, ya listo en este repo).
El dashboard es un snapshot: refleja el CSV con que se generó, no se conecta en vivo a Connect.
Para datos en vivo con refresco automático, la vía nativa es Power BI sobre el mismo SharePoint.

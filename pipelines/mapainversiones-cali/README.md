# ETL MapaInversiones Cali — PaQueVeas

Pipeline ELT en Python para actualizar los datos de la plataforma [PaQueVeas Cali](https://paqueveas.cali.gov.co).

Actualiza:
- Presupuesto de Inversión (CUIPO)
- Proyectos de Inversión
- Procesos y Contratos (SECOP II)
- Exportación a datos abiertos (CSV/XLSX)

---

## 1. Requisitos previos

- Python 3.12
- ODBC Driver 17 o 18 para SQL Server ([descargar](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server))
- Acceso a la base de datos SQL Server (staging y modelo final)

---

## 2. Instalación

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.lock
pip install --no-deps .
```

---

## 3. Configuración de credenciales

Copiar el archivo de ejemplo y completar con los datos del entorno:

```bash
cp .env.example .env
```

Editar `.env`:

```
DB_SERVER=<servidor SQL Server>
DB_NAME=<base de datos staging, ej: PISGRSTG_Cali>
DB_USER=<usuario SQL>
DB_PASSWORD=<contraseña>
```

> **El archivo `.env` nunca se versiona.** Está en `.gitignore`.

---

## 4. Preparar archivos de entrada

Los archivos Excel de cada período deben colocarse en `data/AAAAMM/` (esta carpeta no está en el repositorio):

```
data/
└── 202601/
    ├── CUIPO.xlsx
    ├── CATALOGO_DE_PRODUCTOS.xlsx
    ├── BASE BID.xlsx
    └── REPORTE_RPC.xlsx
```

Luego actualizar en `config/config.yaml` las rutas `path` y el campo `periodo` de cada `extract_sources` con el período nuevo.

---

## 5. Ejecución

```bash
# Ver todos los perfiles disponibles
python -m mapainversiones_cali.main --list-runs

# Ejecutar un dominio completo (extract + transform + load + opendata)
python -m mapainversiones_cali.main --run presupuesto_full
python -m mapainversiones_cali.main --run procesos_full
python -m mapainversiones_cali.main --run contratos_full

# Solo exportar datos abiertos (sin reprocesar staging)
python -m mapainversiones_cali.main --run opendata_full

# Ejecución manual por dominio y etapa
python -m mapainversiones_cali.main --domain presupuesto --stage extract
python -m mapainversiones_cali.main --domain contratos --stage load
python -m mapainversiones_cali.main --domain procesos,contratos --stage extract,load
```

---

## 6. Flujo del pipeline

Los diagramas describen el código y la configuración actual de [config/config.yaml](config/config.yaml).
Las rutas relativas se resuelven desde el directorio de ejecución; ejecutar desde
`MapaInversiones.Datos/`. Los archivos de entrada son externos al repositorio.

### Orquestación y carpetas

```mermaid
flowchart TD
    CFG["config/config.yaml + includes opcionales<br/>.env: conexión SQL Server<br/>CLI: --run / --domain / --stage"] --> MAIN["src/mapainversiones_cali/main.py<br/>Seleccionar dominios y etapas"]
    MAIN --> EX["1. extract<br/>src/mapainversiones_cali/extract/xlsx_extractor.py<br/>Leer hojas, detectar encabezado,<br/>normalizar columnas y agregar periodo"]
    INPUT["Origen configurado (Windows)<br/>G:/My Drive/BID/COL/Cali/PruebaCali/202512/<br/>CUIPO.xlsx · CATALOGO_DE_PRODUCTOS.xlsx<br/>BASE BID.xlsx · REPORTE_RPC.xlsx"] --> EX
    EX --> LOADER["src/mapainversiones_cali/db_loader_pyodbc.py<br/>Recrear staging como NVARCHAR(MAX)<br/>Insertar por lotes"]
    LOADER --> STG[("SQL Server: DB_NAME.dbo.stg_cali_*")]
    STG --> VALID["2. transform<br/>src/mapainversiones_cali/sql_runner.py ejecuta sql/valid/*.sql<br/>Histórico CUIPO y tablas dbo.Validos*"]
    VALID --> MODEL["3. load<br/>src/mapainversiones_cali/sql_runner.py ejecuta sql/model/*.sql<br/>MERGE, INSERT, UPDATE o DELETE según script"]
    STG --> MODEL
    MODEL --> DB[("Destino SQL<br/>MapaInversionesCali.dbo<br/>MapaInversionesCali.consulta")]
    DB -. "Vistas existentes en la base" .-> VIEWS["MapainversionesCali.consulta.VwDatosAbiertos*"]
    VIEWS --> EXPORT["4. opendata<br/>src/mapainversiones_cali/opendata_export/generator.py<br/>SELECT * de cada vista"]
    EXPORT --> WRITERS["src/mapainversiones_cali/opendata_export/csv_exporter.py<br/>src/mapainversiones_cali/opendata_export/xlsx_exporter.py"]
    WRITERS --> OUT["Destino de archivos<br/>MapaInversiones.Datos/src/data/opendata/<br/>nombre_export.csv + nombre_export.xlsx"]
```

Se ejecutan las etapas seleccionadas en el orden `extract → transform → load → opendata`,
y los elementos de cada etapa en el orden del YAML. Los perfiles pueden omitir etapas;
`opendata_full` consulta las vistas existentes sin volver a cargar Excel.
Una excepción detiene el pipeline; cada script SQL tiene su propia transacción,
sin rollback global de las etapas anteriores.

La configuración actual usa `periodo: "202512"` y rutas absolutas de Windows.
En Windows esas rutas prevalecen sobre `base_dir: "data"`. En Linux deben adaptarse:
por ejemplo, `base_dir: "data"` y `path: "202512/CUIPO.xlsx"` para leer
`MapaInversiones.Datos/data/202512/CUIPO.xlsx`. El campo `periodo` también debe actualizarse.

### Archivos y hojas de origen → tablas staging

Todas estas tablas pertenecen a la base indicada por `DB_NAME` (habitualmente
`PISGRSTG_Cali`). Las flechas pasan por el extractor XLSX y el cargador anteriores.

```mermaid
flowchart LR
    subgraph INPUTS["G:/My Drive/BID/COL/Cali/PruebaCali/202512/"]
        F0["CUIPO.xlsx<br/>Hoja: CUIPO"]
        F1["CATALOGO_DE_PRODUCTOS.xlsx<br/>Hoja: Catálogo de Productos"]
        F2["BASE BID.xlsx<br/>Hoja: Procesos"]
        F3["BASE BID.xlsx<br/>Hoja: Contratos"]
        F4["REPORTE_RPC.xlsx<br/>Hoja: REPORTE"]
    end
    F0 --> S0[("dbo.stg_cali_cuipo")]
    F1 --> S1[("dbo.stg_cali_catalogo_productos")]
    F2 --> S2[("dbo.stg_cali_procesos")]
    F3 --> S3[("dbo.stg_cali_contratos")]
    F4 --> S4[("dbo.stg_cali_reporte_rpc")]
```

Si no se encuentran archivos o no hay filas, el cargador omite la carga y conserva
la tabla staging anterior. Cuando hay datos, elimina y recrea la tabla.

### Transformaciones y destinos SQL

Los nombres de scripts de cada nodo son archivos de la carpeta indicada.
Este diagrama resume rutas de datos; el orden de ejecución lo define `config/config.yaml`.

```mermaid
flowchart TD
    CUIPO[("dbo.stg_cali_cuipo")] --> HIST["sql/valid/valid_procesar_cuipo_historico.sql"]
    HIST --> H[("dbo.stg_cali_cuipo_historico")]
    CUIPO --> VB["sql/valid/<br/>valid_entidades.sql<br/>valid_fondo.sql<br/>valid_area_funcional.sql<br/>valid_linea_presupuestal.sql"]
    CAT[("dbo.stg_cali_catalogo_productos")] --> VB
    VB --> VT[("dbo.ValidosEntidades / ValidosFondo<br/>ValidosAreaFuncional / ValidosLineaPresupuestal")]
    VT --> MB["sql/model/<br/>model_entidades.sql / model_fondo.sql<br/>model_area_funcional.sql / model_linea_presupuestal.sql"]
    MB --> BT[("MapaInversionesCali.consulta<br/>CatalogoEntidades / CatalogoFondo<br/>CatalogoAreaFuncional / CatalogoLineaPresupuestal")]
    CUIPO --> FACT["sql/model/<br/>model_FactPresupuesto.sql<br/>model_CatalogoPresupuestoXProyInv.sql"]
    BT --> FACT
    FACT --> FT[("MapaInversionesCali.consulta<br/>FactPresupuesto / CatalogoPresupuestoXProyInv")]
    PROC[("dbo.stg_cali_procesos")] --> VP["sql/valid/valid_procesos.sql<br/>→ dbo.ValidosProcesos"]
    VP --> MP["sql/model/model_procesos.sql"]
    MP --> PT[("MapaInversionesCali.dbo.Procesos")]
    CONT[("dbo.stg_cali_contratos")] --> MC["sql/model/<br/>model_contratos.sql / model_contratista.sql"]
    MC --> CT[("MapaInversionesCali.dbo<br/>Contratos / Contratistas")]
    CT --> CE["sql/model/model_ContratoXEntidad.sql"]
    CE --> CET[("MapaInversionesCali.consulta.ContratoXEntidad")]
    CUIPO --> CP["sql/model/model_ContratoXProyectoInversion.sql"]
    RPC[("dbo.stg_cali_reporte_rpc")] --> CP
    CONT --> CP
    CP --> CPT[("MapaInversionesCali.consulta.ContratoXProyectoInversion")]
    CPT --> PP["sql/model/model_ProcesoXProyectoInversion.sql"]
    PT --> PP
    PP --> PPT[("MapaInversionesCali.consulta.ProcesoXProyectoInversion")]
    CUIPO --> META["sql/model/<br/>model_fuente_de_los_recursos_ppto.sql<br/>model_fuente_de_los_recursos_contratos.sql"]
    META --> MT[("MapaInversionesCali.dbo.fuentedelosrecursos<br/>Fechas de corte y actualización")]
```

Los dominios dependen de datos previamente existentes: los scripts también consultan
`MapaInversionesCali.dbo.Proyecto`, catálogos del modelo final,
`PISGRSTG_Cali.dbo.EquivalenciaEntidades`, `dbo.ProcesosSECOP_II_Total`,
`dbo.VwProcesosAdicionalesDesdeContratos` y `dbo.VwProcesosConFechaPreviaFirmaContrato`.
No se crean ni extraen todos estos objetos en el pipeline configurado.
En particular, contratos necesita staging de CUIPO y REPORTE RPC aunque su perfil
solo extraiga CONTRATOS. La validación de líneas presupuestales consulta catálogos
existentes antes de la etapa `load`.

### Vistas de origen → archivos de destino

Cada flecha genera **dos archivos** en `MapaInversiones.Datos/src/data/opendata/`:
uno `.csv` (UTF-8 con BOM) y otro `.xlsx`. El exportador crea la carpeta si falta y
sobrescribe los archivos del mismo nombre. Una vista vacía no genera archivos
ni elimina exportaciones anteriores. Las vistas deben existir previamente;
el pipeline solo las consulta.

```mermaid
flowchart LR
    subgraph V["Origen: MapainversionesCali.consulta"]
        V0["VwDatosAbiertosPresupuestoXProyInv"]
        V1["VwDatosAbiertosProcesosXProyectosInv"]
        V2["VwDatosAbiertosContratosXProyectosInv"]
        V3["VwDatosAbiertosProyectosAprobadosInv"]
        V4["VwDatosAbiertosProyectosPresupuestoAvanceFisicoXAnio"]
        V5["VwDatosAbiertosProyectosEjecucionFinancieraDetallada"]
        V6["VwDatosAbiertosProyectosXTerritorio"]
        V7["VwDatosAbiertosEmprestito"]
        V8["VwDatosAbiertosProyectosEmprestito"]
    end
    subgraph O["Destino: MapaInversiones.Datos/src/data/opendata/"]
        O0["DatosAbiertosPresupuestoXProyInv.csv<br/>DatosAbiertosPresupuestoXProyInv.xlsx"]
        O1["DatosAbiertosProcesosXProyectosInv.csv<br/>DatosAbiertosProcesosXProyectosInv.xlsx"]
        O2["DatosAbiertosContratosXProyectosInv.csv<br/>DatosAbiertosContratosXProyectosInv.xlsx"]
        O3["DatosAbiertosProyectosInversion.csv<br/>DatosAbiertosProyectosInversion.xlsx"]
        O4["DatosAbiertosProyectosInversionPresupuestoAvanceFisicoxAnio.csv<br/>DatosAbiertosProyectosInversionPresupuestoAvanceFisicoxAnio.xlsx"]
        O5["DatosAbiertosProyectosInversionEjecucionFinancieraDetallada.csv<br/>DatosAbiertosProyectosInversionEjecucionFinancieraDetallada.xlsx"]
        O6["DatosAbiertosProyectosInversionXTerritorio.csv<br/>DatosAbiertosProyectosInversionXTerritorio.xlsx"]
        O7["DatosAbiertosEmprestito.csv<br/>DatosAbiertosEmprestito.xlsx"]
        O8["DatosAbiertosProyectosInversionEmprestito.csv<br/>DatosAbiertosProyectosInversionEmprestito.xlsx"]
    end
    V0 --> O0
    V1 --> O1
    V2 --> O2
    V3 --> O3
    V4 --> O4
    V5 --> O5
    V6 --> O6
    V7 --> O7
    V8 --> O8
```

---

## 7. Configuración avanzada (`config/config.yaml`)

El archivo `config/config.yaml` controla todo el pipeline sin tocar el código:

- **`extract_sources`**: fuentes Excel → tablas staging
- **`transform_models`**: scripts SQL `sql/valid/` (staging → válidos)
- **`load_models`**: scripts SQL `sql/model/` (válidos → modelo final)
- **`opendata_exports`**: vistas a exportar como CSV/XLSX
- **`domains`**: agrupa items por dominio de negocio
- **`runs`**: perfiles de ejecución reutilizables

### Includes (configuración modular)

Se pueden componer varios YAML desde uno principal:

```yaml
includes:
  - config/base.yaml
  - config/domains/presupuesto.yaml
```

---

## 8. Estructura del repositorio

```
├── src/
│   ├── main.py                  # Orquestador principal
│   ├── db_loader_pyodbc.py      # Cargador usado por main.py (SQL Server)
│   ├── sql_runner.py            # Ejecuta scripts SQL
│   ├── extract/                 # Extractores (xlsx, csv, api, adls)
│   └── opendata_export/         # Exportadores CSV/XLSX
├── sql/
│   ├── valid/                   # Scripts transform (staging → válidos)
│   └── model/                   # Scripts load (válidos → modelo final)
├── config/config.yaml                  # Configuración del pipeline
├── requirements.txt
├── .env.example                 # Plantilla de credenciales
└── Dockerfile
```

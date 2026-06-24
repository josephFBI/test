# 🏗️ ARQUITECTURA DEL SISTEMA - Diagrama Detallado

## 1. FLUJO DE DATOS GENERAL

```
┌─────────────────────────────────────────────────────────────────┐
│                     INTERFAZ DEL USUARIO                        │
│              (Frontend React / Cliente HTTP)                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API FastAPI (main.py)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Endpoints REST                                           │  │
│  │ - /proyectos/*                                          │  │
│  │ - /examenes/*                                           │  │
│  │ - /buscar/*                                             │  │
│  │ - /estadisticas/*                                       │  │
│  │ - /backup, /import, /export                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────┬───────────────────────────────┬──────────────────┘
               │                               │
        Lectura/Escritura               Lectura/Escritura
               │                               │
               ▼                               ▼
    ┌─────────────────────┐      ┌────────────────────────┐
    │  SQLITE DATABASE    │      │   SISTEMA DE ARCHIVOS  │
    │  (Metadatos Rápido) │      │  (Datos Complejos JSON)│
    │                     │      │                        │
    │  - proyectos        │      │ user_data/projects/    │
    │  - examenes         │      │ {uuid}/                │
    │  - etiquetas        │      │                        │
    │  - configuracion    │      │ ├─ metadata.json      │
    │                     │      │ ├─ transcripcion.json  │
    │  Índices:           │      │ ├─ resumen.json       │
    │  - fecha            │      │ ├─ preguntas.json     │
    │  - rol              │      │ ├─ examen_historial   │
    │  - título           │      │ └─ audio/             │
    │  - nota             │      │    ├─ original.wav   │
    │                     │      │    └─ procesado.wav  │
    └─────────────────────┘      └────────────────────────┘
```

---

## 2. CAPAS DEL SISTEMA

```
┌─────────────────────────────────────────────────────────────────┐
│                       CAPA DE PRESENTACIÓN                       │
│                    (Frontend React - No incluido)               │
│  - Interfaz gráfica                                            │
│  - Gestión de proyectos                                        │
│  - Toma de exámenes                                            │
│  - Visualización de estadísticas                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ JSON/HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE API (FastAPI)                       │
│                         (main.py)                               │
│  - Validación con Pydantic                                     │
│  - Enrutamiento de requests                                    │
│  - Manejo de errores HTTP                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ CAPA LÓGICA      │  │ CAPA LÓGICA      │  │ CAPA LÓGICA      │
│ (Búsqueda)       │  │ (Proyectos)      │  │ (Import/Export)  │
│ search_engine.py │  │ project_mgr.py   │  │ import_export.py │
│                  │  │                  │  │                  │
│ - BuscadorProy.  │  │ - Crear carpetas │  │ - ZIP Export     │
│ - BuscadorExam.  │  │ - CRUD JSON      │  │ - ZIP Import     │
│ - Estadísticas   │  │ - Validación     │  │ - Backups        │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE BASE DE DATOS                          │
│                      (database.py)                              │
│                                                                 │
│  DatabaseConnection ◄─┐                                        │
│  ├─ ProyectosDB       │ Singleton Pattern                      │
│  ├─ ExamenesDB        │                                        │
│  ├─ EtiquetasDB       │                                        │
│  └─ ConfiguracionDB   │                                        │
│                                                                 │
│  - Conexión SQLite                                             │
│  - CRUD Operations                                             │
│  - Transacciones ACID                                          │
│  - Índices para búsquedas rápidas                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
            ┌───────────────┐   ┌───────────────┐
            │  SQLite DB    │   │  JSON Files   │
            │  app.db       │   │  (Sistema FS) │
            │               │   │               │
            │  - 256 MB     │   │  - 1+ GB      │
            │  - Indexado   │   │  - No indexado
            │  - Búsquedas  │   │  - Audios     │
            │  - Rápidas    │   │  - Texto      │
            └───────────────┘   └───────────────┘
```

---

## 3. ESTRUCTURA DE DIRECTORIOS

```
proyecto-raiz/
│
├── database.py                    # Capa SQLite
│   ├── DatabaseConnection (Singleton)
│   ├── ProyectosDB
│   ├── ExamenesDB
│   ├── EtiquetasDB
│   └── ConfiguracionDB
│
├── project_manager.py             # Gestor de proyectos
│   └── ProjectManager
│       ├── crear_proyecto()
│       ├── obtener_proyecto()
│       ├── actualizar_*()
│       ├── eliminar_proyecto()
│       └── validar_integridad()
│
├── search_engine.py               # Búsqueda y estadísticas
│   ├── BuscadorProyectos
│   ├── BuscadorExamenes
│   └── Estadisticas
│
├── import_export.py               # Import/Export
│   ├── ImportadorExportador
│   └── BackupManager
│
├── main.py                        # API FastAPI
│   ├── @app.post("/proyectos/crear")
│   ├── @app.get("/proyectos/{id}")
│   ├── @app.post("/proyectos/{id}/examenes")
│   ├── @app.get("/buscar/*")
│   ├── @app.get("/estadisticas/*")
│   ├── @app.post("/backup")
│   └── ... (más endpoints)
│
├── init_system.py                 # Inicializador
│   └── InicializadorSistema
│       ├── crear_estructura_carpetas()
│       ├── inicializar_base_datos()
│       ├── crear_archivo_configuracion()
│       └── crear_ejemplo_proyecto()
│
├── tests.py                       # Suite de tests
│   ├── TestDatabase
│   ├── TestProjectManager
│   ├── TestSearch
│   ├── TestImportExport
│   ├── TestBackup
│   └── TestIntegracion
│
├── requirements.txt               # Dependencias
├── README.md                      # Documentación
├── ARQUITECTURA.md                # Este archivo
│
└── user_data/                     # Datos de usuario (creados en runtime)
    ├── database/
    │   ├── app.db                 # Base de datos SQLite
    │   └── backups/
    │       ├── backup_20260618_100000.db
    │       ├── backup_20260618_110000.db
    │       └── ...
    │
    ├── projects/                  # Proyectos de usuario
    │   ├── {uuid-1}/
    │   │   ├── metadata.json
    │   │   ├── transcripcion_completa.json
    │   │   ├── resumen.json
    │   │   ├── preguntas.json
    │   │   ├── examen_historial.json
    │   │   └── audio/
    │   │       ├── audio_original.wav
    │   │       └── audio_procesado.wav
    │   │
    │   ├── {uuid-2}/
    │   │   └── [estructura similar]
    │   │
    │   └── ...
    │
    ├── config.json                # Configuración global
    │
    └── logs/
        └── sistema.log            # Archivo de log
```

---

## 4. FLUJO DE UN PROYECTO DOCENTE

```
                    DOCENTE
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    Graba      Importa      Carga archivo
    Audio/      ZIP         local
    Video
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │  Procesa con AI Local    │
        │  (Whisper + NLP)         │
        │                          │
        │ ├─ Transcripción         │
        │ ├─ Segmentación          │
        │ └─ Generación de Q       │
        └──────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    Guarda      Crea       Guarda
    en SQLite   Carpeta    en JSON
        │             │             │
    (Metadatos)  (UUID)      (Datos)
        │             │             │
        │    ┌────────┴────────┐    │
        │    │                 │    │
        ▼    ▼                 ▼    ▼
    ┌─────────────────────────────────┐
    │    user_data/projects/{uuid}/   │
    │                                 │
    │ ├─ metadata.json (2 KB)         │
    │ ├─ transcripcion_completa.json  │
    │ ├─ resumen.json                 │
    │ ├─ preguntas.json               │
    │ ├─ examen_historial.json        │
    │ └─ audio/                       │
    │    ├─ original.wav (100+ MB)    │
    │    └─ procesado.wav (50 MB)     │
    └─────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    Puede      Puede         Puede
    editar     exportar      compartir
    contenido  como ZIP      con alumnos
        │             │             │
        │             ▼             ▼
        │      Archivo ZIP    Alumno recibe
        │     (contiene todo)  e importa
        │
        └─► Alumno accede
            a través de REST API
```

---

## 5. FLUJO DE UN ALUMNO CON EXAMEN

```
                    ALUMNO
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    Importa      Descarga      Carga
    ZIP del      desde URL     local
    docente
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │  Lee contenido JSON      │
        │                          │
        │ ├─ Transcripción         │
        │ ├─ Resumen (nivel ado)   │
        │ ├─ Palabras clave        │
        │ ├─ Preguntas (5-10)      │
        │ └─ Audios de referencia  │
        └──────────────────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │  Realiza Examen          │
        │                          │
        │ ├─ Lee preguntas         │
        │ ├─ Responde una a una    │
        │ ├─ Cronómetro            │
        │ └─ Obtiene feedback      │
        └──────────────────────────┘
                      │
                      ▼
        ┌──────────────────────────┐
        │  Examen Completado       │
        │                          │
        │ ├─ Calcula nota          │
        │ ├─ Identifica falladas    │
        │ ├─ Muestra explicaciones │
        │ └─ Guarda en JSON        │
        └──────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    Guarda      Registra      Actualiza
    en SQLite   en JSON       estadísticas
        │             │             │
        │             │             │
        ▼             ▼             ▼
    Nota &    Respuestas     Historial
    Puntuación detalladas    & promedio
```

---

## 6. OPERACIONES SQLite - Ejemplos

### Búsqueda: "Todas las clases de matemáticas del mes pasado"

```sql
SELECT p.* FROM proyectos p
JOIN proyectos_etiquetas pe ON p.id = pe.proyecto_id
JOIN etiquetas e ON pe.etiqueta_id = e.id
WHERE e.nombre = 'matemáticas'
  AND p.fecha_creacion >= '2026-05-18'
  AND p.fecha_creacion <= '2026-06-18'
ORDER BY p.fecha_creacion DESC;
```

### Búsqueda: "Desempeño de un alumno"

```sql
SELECT 
    COUNT(*) as total_examenes,
    AVG(nota) as promedio,
    MAX(nota) as maxima,
    MIN(nota) as minima
FROM examenes
WHERE alumno_nombre = 'Juan García';
```

### Búsqueda: "Etiquetas más usadas"

```sql
SELECT e.nombre, COUNT(pe.proyecto_id) as cantidad
FROM etiquetas e
LEFT JOIN proyectos_etiquetas pe ON e.id = pe.etiqueta_id
GROUP BY e.id
ORDER BY cantidad DESC
LIMIT 10;
```

---

## 7. ESTRUCTURA JSON - Ejemplos

### metadata.json (2 KB)

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "titulo": "Programación Python - Semana 1",
  "descripcion": "Introducción a variables y tipos de datos",
  "rol": "docente",
  "perfil_edad": "adulto",
  "fecha_creacion": "2026-06-18T10:30:00",
  "duracion_segundos": 5400,
  "config": {
    "idioma": "es",
    "modelo_whisper": "tiny",
    "filtro_ruido": true,
    "segmentar_silencios": true
  },
  "etiquetas": ["programación", "python", "principiantes"],
  "ultima_modificacion": "2026-06-18T14:00:00"
}
```

### transcripcion_completa.json (500 KB)

```json
[
  {
    "timestamp": 0.0,
    "texto": "Bienvenidos al curso de Python",
    "orador": "profesor"
  },
  {
    "timestamp": 45.3,
    "texto": "Hoy aprenderemos sobre variables",
    "orador": "profesor"
  },
  {
    "timestamp": 120.5,
    "texto": "¿Alguien tiene dudas?",
    "orador": "profesor"
  },
  {
    "timestamp": 125.2,
    "texto": "¿Qué es una variable?",
    "orador": "alumno1"
  }
]
```

### resumen.json (3 KB)

```json
{
  "version_nino": "Una variable es como una caja donde guardas números o palabras. En Python, das un nombre a la caja y pones lo que quieres dentro.",
  
  "version_adolescente": "Una variable es un contenedor que almacena un valor. En Python creas variables con el símbolo igual: x = 10. Esto crea una variable llamada 'x' con el valor 10.",
  
  "version_adulto": "Variables en Python: Una variable es una referencia a un objeto en memoria. En Python, todo es un objeto. Cuando asignas x = 10, creas un objeto entero y x es una referencia a él.",
  
  "palabras_clave": [
    "variable",
    "asignación",
    "tipo de dato",
    "entero",
    "cadena",
    "booleano"
  ]
}
```

### preguntas.json (2 KB)

```json
[
  {
    "id": 1,
    "tipo": "verdadero_falso",
    "texto": "En Python, una variable debe declararse antes de usarse",
    "respuesta_correcta": false,
    "explicacion": "Python detecta automáticamente los tipos"
  },
  {
    "id": 2,
    "tipo": "opcion_multiple",
    "texto": "¿Cuál es la forma correcta de crear una variable con el valor 10?",
    "opciones": [
      "10 = x",
      "x = 10",
      "var x = 10",
      "define x = 10"
    ],
    "respuesta_correcta": "x = 10",
    "explicacion": "Python usa el operador = para asignación"
  },
  {
    "id": 3,
    "tipo": "completar",
    "texto": "El tipo de dato de 'Hola' es ______",
    "respuesta_correcta": "str",
    "explicacion": "Las comillas indican que es una cadena de texto"
  }
]
```

---

## 8. RENDIMIENTO Y ESCALABILIDAD

### SQLite
- **Búsquedas**: O(log n) con índices
- **Máximo recomendado**: 1 GB de datos (varios millones de registros)
- **Conexiones simultáneas**: 1 principalmente (archivo SQLite)

### Sistema de Archivos (JSON)
- **Lectura**: Rápida para archivos < 10 MB
- **Escalabilidad**: Ideal para datos hasta 100 GB

### Recomendaciones
- **SQLite**: Para metadatos, búsquedas, estadísticas
- **JSON**: Para datos no estructurados, archivos grandes, audios
- **Si necesitas escalar**: Migrar a PostgreSQL (misma interfaz de código)

---

## 9. MIGRACIÓN A PostgreSQL

El código está diseñado para permitir migración fácil:

```python
# Cambio mínimo en database.py:

# SQLite (actual)
db = DatabaseConnection(Path("app.db"))

# PostgreSQL (futuro)
db = DatabaseConnection(
    "postgresql://user:pass@localhost/clases_db"
)
```

---

## 10. SEGURIDAD

### Datos Locales
✓ Todos los datos quedan en el dispositivo del usuario
✓ No hay sincronización con servidores externos
✓ Control total del usuario sobre sus archivos

### Base de Datos
✓ Transacciones ACID (integridad garantizada)
✓ Validación de entrada con Pydantic
✓ Manejo de errores robusto

### Backups
✓ Función de backup automático
✓ Restauración desde punto anterior
✓ Múltiples copias seguras

---

**Última actualización**: 18/06/2026

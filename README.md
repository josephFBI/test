# 📚 Sistema de Gestor de Clases - Arquitectura Híbrida SQLite + JSON

Un programa de escritorio **OFFLINE** para resumir clases y generar exámenes automáticos, con arquitectura híbrida que combina SQLite para metadatos y JSON para datos complejos.

## 🎯 Características Principales

### ✅ Gestión de Proyectos
- **Crear proyectos** como docente o alumno
- **Organizar** por etiquetas y perfiles de edad
- **Cargar audio/video** de clases
- **Procesar automáticamente** con Whisper + NLP

### 📊 Generación de Contenido
- **Transcripción completa** con timestamps
- **Resúmenes en 3 niveles**: niño, adolescente, adulto
- **Banco de preguntas** generado automáticamente
- **Exámenes interactivos** para alumnos

### 📈 Estadísticas y Reportes
- **Búsqueda avanzada** por título, rol, fechas, etiquetas
- **Estadísticas de desempeño** por alumno
- **Historial de exámenes** detallado
- **Reportes de etiquetas** más usadas

### 💾 Backup e Importación/Exportación
- **Exportar proyectos** como ZIP
- **Importar** desde ZIP
- **Backup automático** de BD
- **Restauración** desde backups

---

## 🏗️ Arquitectura del Sistema

### Base de Datos - SQLite
Almacena metadatos y permite búsquedas rápidas:

```
├── proyectos
│   ├── id (UUID)
│   ├── titulo
│   ├── rol (docente/alumno)
│   ├── perfil_edad
│   ├── fecha_creacion
│   ├── duracion_segundos
│   ├── ruta_carpeta
│   └── ultima_modificacion
│
├── examenes
│   ├── id
│   ├── proyecto_id (FK)
│   ├── alumno_nombre
│   ├── fecha
│   ├── nota
│   ├── preguntas_acertadas
│   ├── preguntas_totales
│   ├── preguntas_falladas_json
│   └── tiempo_segundos
│
├── etiquetas
│   ├── id
│   └── nombre (UNIQUE)
│
├── proyectos_etiquetas (muchos a muchos)
│   ├── proyecto_id (FK)
│   └── etiqueta_id (FK)
│
└── configuracion
    ├── clave (PK)
    └── valor
```

### Sistema de Archivos - JSON
Almacena datos complejos sin saturar la BD:

```
user_data/
├── projects/
│   └── {proyecto_id}/
│       ├── metadata.json
│       │   └── Información del proyecto
│       │
│       ├── transcripcion_completa.json
│       │   └── Array con segmentos: [timestamp, texto, orador]
│       │
│       ├── resumen.json
│       │   ├── version_nino
│       │   ├── version_adolescente
│       │   ├── version_adulto
│       │   └── palabras_clave
│       │
│       ├── preguntas.json
│       │   └── Array de preguntas con tipo, opciones, respuesta
│       │
│       ├── examen_historial.json
│       │   └── Array de exámenes completados
│       │
│       └── audio/
│           ├── audio_original.wav
│           └── audio_procesado.wav
│
├── database/
│   ├── app.db
│   └── backups/
│       └── backup_*.db
│
└── config.json
```

---

## 🚀 Instalación y Configuración

### 1. Requisitos Previos
- Python 3.8+
- pip (gestor de paquetes)

### 2. Instalación

```bash
# Clonar o descargar el proyecto
cd sistema-gestor-clases

# Instalar dependencias
pip install -r requirements.txt

# Inicializar el sistema
python init_system.py

# Opcional: crear sin proyecto de ejemplo
python init_system.py --sin-ejemplo
```

### 3. Configuración Inicial

El archivo `user_data/config.json` se crea automáticamente:

```json
{
  "aplicacion": {
    "nombre": "Sistema de Gestor de Clases",
    "version": "1.0.0"
  },
  "procesamiento": {
    "idioma": "es",
    "modelo_whisper": "tiny",
    "filtro_ruido": true,
    "segmentar_silencios": true
  },
  "api": {
    "host": "0.0.0.0",
    "puerto": 8000,
    "debug": false
  }
}
```

---

## 📡 Ejecución de la API

### Iniciar el servidor

```bash
python main.py
```

La API estará disponible en: **http://localhost:8000**

### Documentación interactiva
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📚 Endpoints de la API

### Proyectos

#### Crear proyecto
```
POST /proyectos/crear
Content-Type: application/json

{
  "titulo": "Matemáticas - Funciones",
  "descripcion": "Clase sobre funciones lineales",
  "rol": "docente",
  "perfil_edad": "adulto",
  "duracion_segundos": 3600,
  "etiquetas": ["matemáticas", "funciones"]
}
```

#### Obtener proyecto
```
GET /proyectos/{proyecto_id}
```

Retorna todo el contenido: metadata, transcripción, resumen, preguntas, historial.

#### Listar proyectos
```
GET /proyectos?limite=50&offset=0
```

#### Actualizar proyecto
```
PUT /proyectos/{proyecto_id}
Content-Type: application/json
```

#### Eliminar proyecto
```
DELETE /proyectos/{proyecto_id}
```

---

### Contenido

#### Actualizar transcripción
```
PUT /proyectos/{proyecto_id}/transcripcion
Content-Type: application/json

[
  {"timestamp": 0.0, "texto": "Bienvenidos", "orador": "profesor"},
  {"timestamp": 5.2, "texto": "Vamos a ver funciones", "orador": "profesor"}
]
```

#### Actualizar resumen
```
PUT /proyectos/{proyecto_id}/resumen

{
  "version_nino": "Las funciones son...",
  "version_adolescente": "Una función lineal es...",
  "version_adulto": "Matemáticamente, una función...",
  "palabras_clave": ["función", "variable", "pendiente"]
}
```

#### Actualizar preguntas
```
PUT /proyectos/{proyecto_id}/preguntas

[
  {
    "id": 1,
    "tipo": "verdadero_falso",
    "texto": "Una función lineal siempre pasa por el origen",
    "respuesta_correcta": "false",
    "explicacion": "Solo si la intersección es 0"
  }
]
```

---

### Exámenes

#### Crear examen
```
POST /proyectos/{proyecto_id}/examenes
Content-Type: application/json

{
  "alumno_nombre": "Carlos Pérez",
  "respuestas": [
    {"pregunta_id": 1, "respuesta": "false", "correcta": true},
    {"pregunta_id": 2, "respuesta": "Δy/Δx", "correcta": true}
  ],
  "nota": 9.5,
  "tiempo_segundos": 300
}
```

#### Obtener exámenes del proyecto
```
GET /proyectos/{proyecto_id}/examenes
```

#### Obtener exámenes del alumno
```
GET /alumnos/{alumno_nombre}/examenes
```

#### Estadísticas del alumno
```
GET /alumnos/{alumno_nombre}/estadisticas
```

---

### Búsqueda

#### Búsqueda por título
```
GET /buscar/titulo?q=matemáticas&limite=50
```

#### Búsqueda por rol
```
GET /buscar/rol?rol=docente&limite=50
```

#### Búsqueda por etiqueta
```
GET /buscar/etiqueta/programación?limite=50
```

#### Búsqueda últimos N días
```
GET /buscar/dias?dias=7&limite=50
```

#### Búsqueda avanzada
```
POST /buscar/avanzada

{
  "titulo": "matemáticas",
  "rol": "docente",
  "fecha_inicio": "2026-06-01",
  "fecha_fin": "2026-06-30",
  "etiquetas": ["matemáticas", "secundaria"],
  "duracion_min": 1800,
  "duracion_max": 7200,
  "orden_por": "fecha",
  "orden_ascendente": false,
  "limite": 50
}
```

---

### Estadísticas

#### Estadísticas generales
```
GET /estadisticas/generales
```

Retorna:
```json
{
  "total_proyectos": 25,
  "total_examenes": 150,
  "duracion_promedio_segundos": 3600,
  "nota_promedio_examenes": 8.5,
  "proyectos_por_rol": {
    "docente": 15,
    "alumno": 10
  }
}
```

#### Estadísticas de proyecto
```
GET /estadisticas/proyecto/{proyecto_id}
```

#### Etiquetas más usadas
```
GET /estadisticas/etiquetas?limite=10
```

#### Alumnos más activos
```
GET /estadisticas/alumnos?limite=10
```

---

### Etiquetas

#### Obtener todas las etiquetas
```
GET /etiquetas
```

#### Agregar etiqueta a proyecto
```
POST /etiquetas/{proyecto_id}/{nombre_etiqueta}
```

---

### Import/Export

#### Exportar proyecto como ZIP
```
GET /exportar/proyecto/{proyecto_id}
```

Descarga un ZIP con toda la carpeta del proyecto.

#### Importar proyecto desde ZIP
```
POST /importar
Content-Type: multipart/form-data

[archivo ZIP]
```

---

### Backup

#### Crear backup
```
POST /backup
```

#### Listar backups
```
GET /backups
```

#### Restaurar backup
```
POST /restaurar/{nombre_backup}
```

---

## 🔧 Estructura del Código

```
├── database.py              # Capa de BD SQLite
│   ├── DatabaseConnection   # Gestor de conexiones
│   ├── ProyectosDB          # CRUD Proyectos
│   ├── ExamenesDB           # CRUD Exámenes
│   ├── EtiquetasDB          # CRUD Etiquetas
│   └── ConfiguracionDB      # CRUD Config
│
├── project_manager.py       # Gestor de proyectos (carpetas + JSON)
│   └── ProjectManager       # Crear, leer, actualizar, eliminar
│
├── search_engine.py         # Búsqueda y estadísticas
│   ├── BuscadorProyectos    # Búsquedas combinadas
│   ├── BuscadorExamenes     # Filtros de exámenes
│   └── Estadisticas         # Reportes y agregaciones
│
├── import_export.py         # Import/Export y Backups
│   ├── ImportadorExportador # ZIP y migraciones
│   └── BackupManager        # Backups automáticos
│
├── main.py                  # API FastAPI
│   └── [Todos los endpoints REST]
│
└── init_system.py           # Script de inicialización
```

---

## 📖 Ejemplos de Uso

### Ejemplo 1: Crear un proyecto de clase

```python
from database import DatabaseConnection, ProyectosDB
from project_manager import ProjectManager

# Inicializar
db = DatabaseConnection(Path("user_data/database/app.db"))
pm = ProjectManager("user_data")
db_crud = ProyectosDB(db)

# Crear proyecto
datos = {
    "titulo": "Programación en Python - Semana 1",
    "descripcion": "Introducción a Python y estructuras básicas",
    "rol": "docente",
    "perfil_edad": "adulto",
    "duracion_segundos": 5400,
    "etiquetas": ["programación", "python", "principiantes"]
}

proyecto_id = pm.crear_proyecto(datos, db_crud)
print(f"Proyecto creado: {proyecto_id}")
```

### Ejemplo 2: Cargar transcripción

```python
transcripcion = [
    {
        "timestamp": 0.0,
        "texto": "Bienvenidos al curso de Python",
        "orador": "profesor"
    },
    {
        "timestamp": 30.5,
        "texto": "Hoy vamos a aprender variables",
        "orador": "profesor"
    }
]

pm.actualizar_transcripcion(proyecto_id, transcripcion)
```

### Ejemplo 3: Agregar preguntas

```python
preguntas = [
    {
        "id": 1,
        "tipo": "verdadero_falso",
        "texto": "Python es un lenguaje compilado",
        "respuesta_correcta": False,
        "explicacion": "Python es interpretado, no compilado"
    },
    {
        "id": 2,
        "tipo": "opcion_multiple",
        "texto": "¿Cuál es la sintaxis correcta para crear una variable?",
        "opciones": [
            "var x = 10",
            "x = 10",
            "define x = 10",
            "set x = 10"
        ],
        "respuesta_correcta": "x = 10",
        "explicacion": "En Python no necesitas palabra clave var"
    }
]

pm.actualizar_preguntas(proyecto_id, preguntas)
```

### Ejemplo 4: Registrar examen

```python
from import_export import ImportadorExportador

examen = {
    "alumno_nombre": "Juan García",
    "respuestas": [
        {"pregunta_id": 1, "respuesta": False, "correcta": True},
        {"pregunta_id": 2, "respuesta": "x = 10", "correcta": True}
    ],
    "nota": 10.0,
    "tiempo_segundos": 600
}

pm.guardar_examen(proyecto_id, examen)
```

### Ejemplo 5: Búsqueda avanzada

```python
from search_engine import BuscadorProyectos

buscador = BuscadorProyectos(db, pm)

# Buscar todos los proyectos de docentes con etiqueta "programación"
# desde el 1 de junio al 30 de junio
filtros = {
    "rol": "docente",
    "etiquetas": ["programación"],
    "fecha_inicio": "2026-06-01",
    "fecha_fin": "2026-06-30",
    "orden_por": "fecha",
    "orden_ascendente": False
}

resultados = buscador.buscar_avanzada(filtros)
for proyecto in resultados:
    print(f"{proyecto['titulo']} - {proyecto['fecha_creacion']}")
```

### Ejemplo 6: Exportar e Importar

```python
from import_export import ImportadorExportador

importador = ImportadorExportador(pm, db_crud)

# Exportar proyecto
zip_path = importador.exportar_proyecto_zip("proyecto_123")
print(f"Exportado a: {zip_path}")

# Importar proyecto
nuevo_id = importador.importar_proyecto_zip(zip_path)
print(f"Importado con ID: {nuevo_id}")
```

---

## 🔒 Seguridad

### Offline-First
- **Sin conexión a internet requerida** ✓
- **Todos los datos locales** ✓
- **Sin dependencias en la nube** ✓

### Validación
- **Validación de entrada** con Pydantic
- **Transacciones ACID** en SQLite
- **Manejo de errores** robusto
- **Logging completo** de todas las operaciones

### Integridad de Datos
- **Relaciones FK** en la BD
- **Índices** para búsquedas rápidas
- **Backups** automáticos
- **Validación** de estructura de carpetas

---

## 📊 Caso de Uso Completo

**Flujo de Docente:**

1. **Graba clase** (audio/video)
2. **Recorta si es necesario**
3. **Procesa con Whisper + NLP local**
   - Genera transcripción completa
   - Crea resumen en 3 niveles
   - Genera banco de preguntas
4. **Guarda en BD**:
   - SQLite: metadatos
   - JSON: contenido completo
5. **Puede exportar** como ZIP (compartir con otros)

**Flujo de Alumno:**

1. **Importa clase** (ZIP o archivo local)
2. **Revisa contenido**:
   - Lee transcripción
   - Estudia resumen (nivel adolescente)
   - Ve palabras clave
3. **Realiza examen**
4. **Obtiene**:
   - Nota inmediata
   - Preguntas acertadas/falladas
   - Explicaciones
5. **Sistema registra**:
   - En SQLite: nota y estadísticas
   - En JSON: respuestas detalladas

---

## 🐛 Troubleshooting

### Error: "Base de datos no encontrada"
```bash
python init_system.py
```

### Error: "Puerto 8000 en uso"
```bash
# Usar otro puerto
uvicorn main:app --port 8001
```

### Error: "Importar ZIP falla"
- Verifica que el ZIP tenga estructura válida
- Debe contener `metadata.json` en la raíz

### Error: "Proyecto huérfano (en carpeta pero no en BD)"
```python
# Usar función de reparación
pm.reparar_proyecto(project_id)
```

---

## 📝 Licencia

MIT License - Libre para usar y modificar

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-caracteristica`)
3. Commit cambios (`git commit -am 'Agrega nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

---

## 📞 Soporte

- 📧 Email: soporte@sistema-clases.local
- 📚 Documentación: http://localhost:8000/docs
- 🐛 Issues: Crear en el repositorio

---

## 🎯 Roadmap

### v1.1.0
- [ ] Frontend React para la interfaz gráfica
- [ ] Integración con Whisper local
- [ ] Soporte para múltiples idiomas
- [ ] Editor visual de preguntas

### v1.2.0
- [ ] Sincronización entre dispositivos (local)
- [ ] Exportación a PDF
- [ ] Gráficos de estadísticas
- [ ] Sistema de reportes

### v2.0.0
- [ ] Aplicación de escritorio (Electron/PyQt)
- [ ] Base de datos PostgreSQL (opcional)
- [ ] API GraphQL
- [ ] Autenticación multi-usuario

---

**¡Gracias por usar el Sistema de Gestor de Clases! 🎓**

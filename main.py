"""
=============================================================================
API FASTAPI - Endpoints REST
=============================================================================
Proporciona una API REST para todas las funcionalidades del sistema.
Endpoints para proyectos, exámenes, búsquedas, estadísticas, etc.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import uuid

# Importar módulos de la aplicación
from database import (
    DatabaseConnection, ProyectosDB, ExamenesDB, 
    EtiquetasDB, ConfiguracionDB
)
from project_manager import ProjectManager
from search_engine import BuscadorProyectos, BuscadorExamenes, Estadisticas
from import_export import ImportadorExportador, BackupManager

# Configuración
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicializar FastAPI
app = FastAPI(
    title="Sistema de Gestor de Clases",
    description="API para gestionar clases, exámenes y estadísticas",
    version="1.0.0"
)

# Inicializar componentes
BASE_PATH = Path("user_data")
DB = DatabaseConnection(BASE_PATH / "database" / "app.db")
PM = ProjectManager(str(BASE_PATH))

# CRUD
proyectos_db = ProyectosDB(DB)
examenes_db = ExamenesDB(DB)
etiquetas_db = EtiquetasDB(DB)
config_db = ConfiguracionDB(DB)

# Búsqueda y estadísticas
buscador_proyectos = BuscadorProyectos(DB, PM)
buscador_examenes = BuscadorExamenes(DB)
estadisticas = Estadisticas(DB)

# Import/Export
importador_exportador = ImportadorExportador(PM, proyectos_db)
backup_manager = BackupManager(BASE_PATH / "database" / "app.db")


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class MetadataProyecto(BaseModel):
    """Metadatos de un proyecto."""
    titulo: str = Field(..., min_length=1)
    descripcion: str = ""
    rol: str = Field(..., pattern="^(docente|alumno)$")
    perfil_edad: Optional[str] = Field(None, pattern="^(nino|adolescente|adulto)$")
    duracion_segundos: int = 0
    etiquetas: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class SegmentTranscripcion(BaseModel):
    """Segmento de transcripción."""
    timestamp: float
    texto: str
    orador: str


class Resumen(BaseModel):
    """Resumen en múltiples versiones."""
    version_nino: str = ""
    version_adolescente: str = ""
    version_adulto: str = ""
    palabras_clave: List[str] = Field(default_factory=list)


class Pregunta(BaseModel):
    """Pregunta de examen."""
    id: int
    tipo: str  # verdadero_falso, opcion_multiple, completar, etc
    texto: str
    opciones: Optional[List[str]] = None
    respuesta_correcta: str
    explicacion: Optional[str] = None


class RespuestaExamen(BaseModel):
    """Respuesta a una pregunta en un examen."""
    pregunta_id: int
    respuesta: Any
    correcta: bool


class DatosExamen(BaseModel):
    """Datos de un examen completo."""
    alumno_nombre: str
    respuestas: List[RespuestaExamen]
    nota: float = Field(..., ge=0, le=10)
    tiempo_segundos: int = 0


class FiltrosBusqueda(BaseModel):
    """Filtros para búsqueda avanzada."""
    titulo: Optional[str] = None
    rol: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    etiquetas: List[str] = Field(default_factory=list)
    duracion_min: Optional[int] = None
    duracion_max: Optional[int] = None
    perfil_edad: Optional[str] = None
    orden_por: str = "fecha"  # fecha, duracion, titulo
    orden_ascendente: bool = False
    limite: int = Field(50, le=500)


# ============================================================================
# ENDPOINTS - PROYECTOS
# ============================================================================

@app.post("/proyectos/crear")
async def crear_proyecto(metadata: MetadataProyecto) -> Dict[str, Any]:
    """
    Crea un nuevo proyecto.
    
    La API crea:
    - Carpeta en user_data/projects/{uuid}/
    - Archivos JSON iniciales
    - Registro en SQLite
    """
    try:
        proyecto_id = PM.crear_proyecto(metadata.dict(), proyectos_db)
        
        if not proyecto_id:
            raise HTTPException(status_code=400, detail="Error al crear proyecto")
        
        return {
            "proyecto_id": proyecto_id,
            "mensaje": "Proyecto creado exitosamente"
        }
    
    except Exception as e:
        logger.error(f"Error al crear proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proyectos/{proyecto_id}")
async def obtener_proyecto(proyecto_id: str) -> Dict[str, Any]:
    """Obtiene un proyecto completo con todos sus datos."""
    try:
        proyecto = PM.obtener_proyecto(proyecto_id)
        
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        return proyecto
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proyectos")
async def listar_proyectos(
    limite: int = Query(50, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Lista todos los proyectos con paginación."""
    try:
        proyectos = proyectos_db.obtener_todos(limite, offset)
        
        return {
            "total": len(proyectos),
            "limite": limite,
            "offset": offset,
            "proyectos": proyectos
        }
    
    except Exception as e:
        logger.error(f"Error al listar proyectos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/proyectos/{proyecto_id}")
async def actualizar_proyecto(proyecto_id: str, 
                             metadata: MetadataProyecto) -> Dict[str, str]:
    """Actualiza los metadatos de un proyecto."""
    try:
        # Actualizar en JSON
        exito = PM.actualizar_metadata(proyecto_id, metadata.dict())
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al actualizar proyecto")
        
        # Actualizar en SQLite
        proyectos_db.actualizar(
            proyecto_id,
            titulo=metadata.titulo,
            rol=metadata.rol,
            perfil_edad=metadata.perfil_edad,
            duracion_segundos=metadata.duracion_segundos
        )
        
        return {"mensaje": "Proyecto actualizado exitosamente"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/proyectos/{proyecto_id}")
async def eliminar_proyecto(proyecto_id: str) -> Dict[str, str]:
    """Elimina un proyecto completamente."""
    try:
        exito = PM.eliminar_proyecto(proyecto_id, proyectos_db)
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al eliminar proyecto")
        
        return {"mensaje": "Proyecto eliminado exitosamente"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar proyecto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - TRANSCRIPCIÓN Y CONTENIDO
# ============================================================================

@app.put("/proyectos/{proyecto_id}/transcripcion")
async def actualizar_transcripcion(
    proyecto_id: str,
    transcripcion: List[SegmentTranscripcion]
) -> Dict[str, str]:
    """Actualiza la transcripción de un proyecto."""
    try:
        exito = PM.actualizar_transcripcion(proyecto_id, 
                                           [t.dict() for t in transcripcion])
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al actualizar transcripción")
        
        return {"mensaje": "Transcripción actualizada"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/proyectos/{proyecto_id}/resumen")
async def actualizar_resumen(proyecto_id: str, 
                            resumen: Resumen) -> Dict[str, str]:
    """Actualiza el resumen de un proyecto."""
    try:
        exito = PM.actualizar_resumen(proyecto_id, resumen.dict())
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al actualizar resumen")
        
        return {"mensaje": "Resumen actualizado"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/proyectos/{proyecto_id}/preguntas")
async def actualizar_preguntas(proyecto_id: str,
                              preguntas: List[Pregunta]) -> Dict[str, str]:
    """Actualiza el banco de preguntas de un proyecto."""
    try:
        exito = PM.actualizar_preguntas(proyecto_id, 
                                       [p.dict() for p in preguntas])
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al actualizar preguntas")
        
        return {"mensaje": "Preguntas actualizadas"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - EXÁMENES
# ============================================================================

@app.post("/proyectos/{proyecto_id}/examenes")
async def crear_examen(proyecto_id: str, 
                      datos_examen: DatosExamen) -> Dict[str, Any]:
    """Crea un nuevo examen para un alumno."""
    try:
        # Validar proyecto
        proyecto = proyectos_db.obtener(proyecto_id)
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        # Generar ID único para examen
        examen_id = str(uuid.uuid4())
        
        # Calcular estadísticas
        preguntas_acertadas = sum(1 for r in datos_examen.respuestas if r.correcta)
        preguntas_totales = len(datos_examen.respuestas)
        preguntas_falladas = [r.pregunta_id for r in datos_examen.respuestas 
                             if not r.correcta]
        
        # Guardar en SQLite
        import json
        exito = examenes_db.crear(
            examen_id=examen_id,
            proyecto_id=proyecto_id,
            alumno_nombre=datos_examen.alumno_nombre,
            nota=datos_examen.nota,
            preguntas_acertadas=preguntas_acertadas,
            preguntas_totales=preguntas_totales,
            preguntas_falladas_json=json.dumps(preguntas_falladas),
            tiempo_segundos=datos_examen.tiempo_segundos
        )
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al guardar examen")
        
        # Guardar en JSON
        PM.guardar_examen(proyecto_id, {
            "id": examen_id,
            "alumno": datos_examen.alumno_nombre,
            "respuestas": [r.dict() for r in datos_examen.respuestas],
            "nota": datos_examen.nota,
            "tiempo_segundos": datos_examen.tiempo_segundos
        })
        
        return {
            "examen_id": examen_id,
            "nota": datos_examen.nota,
            "preguntas_acertadas": preguntas_acertadas,
            "preguntas_totales": preguntas_totales
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear examen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proyectos/{proyecto_id}/examenes")
async def obtener_examenes_proyecto(proyecto_id: str) -> List[Dict[str, Any]]:
    """Obtiene todos los exámenes de un proyecto."""
    try:
        examenes = buscador_examenes.obtener_examenes_proyecto(proyecto_id)
        return examenes
    except Exception as e:
        logger.error(f"Error al obtener exámenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alumnos/{alumno_nombre}/examenes")
async def obtener_examenes_alumno(alumno_nombre: str) -> List[Dict[str, Any]]:
    """Obtiene todos los exámenes de un alumno."""
    try:
        examenes = buscador_examenes.obtener_examenes_alumno(alumno_nombre)
        return examenes
    except Exception as e:
        logger.error(f"Error al obtener exámenes del alumno: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alumnos/{alumno_nombre}/estadisticas")
async def estadisticas_alumno(alumno_nombre: str) -> Dict[str, Any]:
    """Obtiene estadísticas de desempeño de un alumno."""
    try:
        stats = estadisticas.estadisticas_alumno(alumno_nombre)
        return stats
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - BÚSQUEDA
# ============================================================================

@app.get("/buscar/titulo")
async def buscar_por_titulo(q: str, limite: int = Query(50, le=500)) -> List[Dict[str, Any]]:
    """Busca proyectos por título."""
    try:
        return buscador_proyectos.buscar_por_titulo(q, limite)
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/buscar/rol")
async def buscar_por_rol(rol: str, 
                         limite: int = Query(50, le=500)) -> List[Dict[str, Any]]:
    """Busca proyectos por rol."""
    try:
        return buscador_proyectos.buscar_por_rol(rol, limite)
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/buscar/etiqueta/{etiqueta}")
async def buscar_por_etiqueta(etiqueta: str,
                             limite: int = Query(50, le=500)) -> List[Dict[str, Any]]:
    """Busca proyectos por etiqueta."""
    try:
        return buscador_proyectos.buscar_por_etiqueta(etiqueta, limite)
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/buscar/dias")
async def buscar_dias_atras(dias: int = 7,
                           limite: int = Query(50, le=500)) -> List[Dict[str, Any]]:
    """Busca proyectos de los últimos N días."""
    try:
        return buscador_proyectos.buscar_por_dias_atras(dias, limite)
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/buscar/avanzada")
async def buscar_avanzada(filtros: FiltrosBusqueda) -> List[Dict[str, Any]]:
    """Búsqueda avanzada con múltiples filtros."""
    try:
        return buscador_proyectos.buscar_avanzada(filtros.dict(), filtros.limite)
    except Exception as e:
        logger.error(f"Error en búsqueda avanzada: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - ESTADÍSTICAS
# ============================================================================

@app.get("/estadisticas/generales")
async def estadisticas_generales() -> Dict[str, Any]:
    """Obtiene estadísticas generales del sistema."""
    try:
        return estadisticas.estadisticas_generales()
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/estadisticas/proyecto/{proyecto_id}")
async def estadisticas_proyecto(proyecto_id: str) -> Dict[str, Any]:
    """Obtiene estadísticas de un proyecto específico."""
    try:
        return estadisticas.estadisticas_proyecto(proyecto_id)
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/estadisticas/etiquetas")
async def etiquetas_mas_usadas(limite: int = Query(10, le=50)) -> List[Dict[str, Any]]:
    """Obtiene las etiquetas más usadas."""
    try:
        return estadisticas.etiquetas_mas_usadas(limite)
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/estadisticas/alumnos")
async def alumnos_mas_activos(limite: int = Query(10, le=50)) -> List[Dict[str, Any]]:
    """Obtiene los alumnos más activos."""
    try:
        return estadisticas.alumnos_mas_activos(limite)
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - ETIQUETAS
# ============================================================================

@app.get("/etiquetas")
async def obtener_etiquetas() -> List[Dict[str, Any]]:
    """Obtiene todas las etiquetas disponibles."""
    try:
        return etiquetas_db.obtener_todas()
    except Exception as e:
        logger.error(f"Error al obtener etiquetas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/etiquetas/{proyecto_id}/{etiqueta_nombre}")
async def agregar_etiqueta(proyecto_id: str, etiqueta_nombre: str) -> Dict[str, str]:
    """Agrega una etiqueta a un proyecto."""
    try:
        exito = etiquetas_db.agregar_a_proyecto(proyecto_id, etiqueta_nombre)
        
        if not exito:
            raise HTTPException(status_code=400, detail="Error al agregar etiqueta")
        
        return {"mensaje": "Etiqueta agregada"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - IMPORT/EXPORT
# ============================================================================

@app.get("/exportar/proyecto/{proyecto_id}")
async def exportar_proyecto(proyecto_id: str) -> FileResponse:
    """Exporta un proyecto como ZIP."""
    try:
        zip_path = importador_exportador.exportar_proyecto_zip(proyecto_id)
        
        if not zip_path:
            raise HTTPException(status_code=400, detail="Error al exportar proyecto")
        
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=zip_path.name
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al exportar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/importar")
async def importar_proyecto(archivo: UploadFile = File(...)) -> Dict[str, Any]:
    """Importa un proyecto desde un ZIP."""
    try:
        # Guardar archivo temporalmente
        temp_path = Path(f"temp_{archivo.filename}")
        
        with open(temp_path, "wb") as f:
            contenido = await archivo.read()
            f.write(contenido)
        
        # Importar
        proyecto_id = importador_exportador.importar_proyecto_zip(temp_path)
        
        # Limpiar temporal
        temp_path.unlink()
        
        if not proyecto_id:
            raise HTTPException(status_code=400, detail="Error al importar proyecto")
        
        return {
            "proyecto_id": proyecto_id,
            "mensaje": "Proyecto importado exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al importar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS - BACKUP
# ============================================================================

@app.post("/backup")
async def crear_backup(nombre: Optional[str] = None) -> Dict[str, str]:
    """Crea un backup de la base de datos."""
    try:
        backup_path = backup_manager.crear_backup(nombre)
        
        if not backup_path:
            raise HTTPException(status_code=400, detail="Error al crear backup")
        
        return {
            "backup": backup_path.name,
            "ruta": str(backup_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/backups")
async def listar_backups() -> Dict[str, Any]:
    """Lista todos los backups disponibles."""
    try:
        backups = backup_manager.listar_backups()
        return {
            "total": len(backups),
            "backups": [{"nombre": b.name, "ruta": str(b)} for b in backups]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Verifica que la API está funcionando."""
    return {"status": "ok", "mensaje": "Sistema operativo"}


# ============================================================================
# EJECUTAR
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   SISTEMA DE GESTOR DE CLASES - API INICIADA            ║
    ║                                                          ║
    ║   Base de datos: user_data/database/app.db              ║
    ║   Proyectos:    user_data/projects/                     ║
    ║                                                          ║
    ║   Abre tu navegador en: http://localhost:8000           ║
    ║   Documentación: http://localhost:8000/docs            ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

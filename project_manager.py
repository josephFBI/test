"""
=============================================================================
GESTOR DE PROYECTOS - Carpetas y JSON
=============================================================================
Maneja la creación, lectura, actualización y eliminación de proyectos.
Crea y mantiene la estructura de carpetas y archivos JSON.
"""

import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Gestor central de proyectos.
    Coordina operaciones entre la BD (SQLite) y el sistema de archivos (JSON).
    """
    
    def __init__(self, base_path: str = "user_data"):
        self.base_path = Path(base_path)
        self.projects_path = self.base_path / "projects"
        self.projects_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ProjectManager inicializado en {self.base_path}")
    
    def _crear_estructura_carpeta(self, project_id: str) -> Path:
        """
        Crea la estructura de carpetas para un proyecto.
        Retorna la ruta de la carpeta creada.
        """
        project_folder = self.projects_path / project_id
        project_folder.mkdir(parents=True, exist_ok=True)
        
        # Crear subcarpetas si es necesario
        (project_folder / "audio").mkdir(exist_ok=True)
        (project_folder / "archivos").mkdir(exist_ok=True)
        
        return project_folder
    
    def _crear_json_iniciales(self, project_folder: Path, titulo: str, 
                               rol: str, perfil_edad: str = "adulto"):
        """Crea los archivos JSON iniciales para un proyecto."""
        
        # metadata.json
        metadata = {
            "id": project_folder.name,
            "titulo": titulo,
            "descripcion": "",
            "rol": rol,
            "perfil_edad": perfil_edad,
            "fecha_creacion": datetime.now().isoformat(),
            "duracion_segundos": 0,
            "config": {
                "idioma": "es",
                "modelo_whisper": "tiny",
                "filtro_ruido": True,
                "segmentar_silencios": True
            },
            "etiquetas": []
        }
        
        self._guardar_json(project_folder / "metadata.json", metadata)
        
        # transcripcion_completa.json
        self._guardar_json(project_folder / "transcripcion_completa.json", [])
        
        # resumen.json
        resumen = {
            "version_nino": "",
            "version_adolescente": "",
            "version_adulto": "",
            "palabras_clave": []
        }
        self._guardar_json(project_folder / "resumen.json", resumen)
        
        # preguntas.json
        self._guardar_json(project_folder / "preguntas.json", [])
        
        # examen_historial.json
        self._guardar_json(project_folder / "examen_historial.json", [])
        
        logger.info(f"Estructura JSON creada para proyecto {project_folder.name}")
    
    def crear_proyecto(self, datos: Dict[str, Any], db_crud) -> Optional[str]:
        """
        Crea un nuevo proyecto (en BD y sistema de archivos).
        
        Args:
            datos: Diccionario con:
                - titulo (requerido)
                - rol: 'docente' o 'alumno' (requerido)
                - perfil_edad: 'nino', 'adolescente', 'adulto' (opcional)
                - etiquetas: lista de strings (opcional)
                - duracion_segundos: int (opcional)
            
            db_crud: Instancia de ProyectosDB para guardar en SQLite
        
        Returns:
            El ID del proyecto creado, o None si hubo error
        """
        try:
            # Generar ID único
            project_id = str(uuid.uuid4())
            
            # Crear carpeta
            project_folder = self._crear_estructura_carpeta(project_id)
            
            # Crear JSONs iniciales
            rol = datos.get("rol", "alumno")
            perfil_edad = datos.get("perfil_edad", "adulto")
            titulo = datos.get("titulo", "Clase sin título")
            
            self._crear_json_iniciales(project_folder, titulo, rol, perfil_edad)
            
            # Guardar en SQLite
            etiquetas = datos.get("etiquetas", [])
            duracion = datos.get("duracion_segundos", 0)
            
            exito = db_crud.crear(
                proyecto_id=project_id,
                titulo=titulo,
                rol=rol,
                perfil_edad=perfil_edad,
                duracion_segundos=duracion,
                ruta_carpeta=str(project_folder),
                etiquetas=etiquetas
            )
            
            if not exito:
                # Si falla la BD, eliminar carpeta
                shutil.rmtree(project_folder)
                logger.error(f"Error al guardar proyecto en BD: {project_id}")
                return None
            
            logger.info(f"Proyecto creado: {project_id}")
            return project_id
        
        except Exception as e:
            logger.error(f"Error al crear proyecto: {e}")
            return None
    
    def obtener_proyecto(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un proyecto completo (metadata + JSONs).
        
        Returns:
            Diccionario con toda la información del proyecto
        """
        try:
            project_folder = self.projects_path / project_id
            
            if not project_folder.exists():
                logger.warning(f"Carpeta del proyecto no existe: {project_id}")
                return None
            
            # Cargar metadata
            metadata_path = project_folder / "metadata.json"
            metadata = self._cargar_json(metadata_path)
            
            if not metadata:
                logger.warning(f"metadata.json no encontrado: {project_id}")
                return None
            
            # Cargar JSONs asociados
            proyecto = {
                "metadata": metadata,
                "transcripcion": self._cargar_json(project_folder / "transcripcion_completa.json", []),
                "resumen": self._cargar_json(project_folder / "resumen.json", {}),
                "preguntas": self._cargar_json(project_folder / "preguntas.json", []),
                "examen_historial": self._cargar_json(project_folder / "examen_historial.json", [])
            }
            
            return proyecto
        
        except Exception as e:
            logger.error(f"Error al obtener proyecto: {e}")
            return None
    
    def actualizar_metadata(self, project_id: str, metadata: Dict[str, Any]) -> bool:
        """Actualiza el archivo metadata.json."""
        try:
            project_folder = self.projects_path / project_id
            metadata_path = project_folder / "metadata.json"
            
            # Preservar campos que no se deben cambiar
            metadata_actual = self._cargar_json(metadata_path, {})
            
            # Actualizar solo campos permitidos
            campos_permitidos = {'titulo', 'descripcion', 'duracion_segundos', 
                               'config', 'etiquetas', 'perfil_edad'}
            
            for campo in campos_permitidos:
                if campo in metadata:
                    metadata_actual[campo] = metadata[campo]
            
            metadata_actual['ultima_modificacion'] = datetime.now().isoformat()
            
            self._guardar_json(metadata_path, metadata_actual)
            return True
        
        except Exception as e:
            logger.error(f"Error al actualizar metadata: {e}")
            return False
    
    def actualizar_transcripcion(self, project_id: str, 
                                transcripcion: List[Dict[str, Any]]) -> bool:
        """Actualiza transcripcion_completa.json."""
        try:
            project_folder = self.projects_path / project_id
            transcripcion_path = project_folder / "transcripcion_completa.json"
            self._guardar_json(transcripcion_path, transcripcion)
            return True
        except Exception as e:
            logger.error(f"Error al actualizar transcripción: {e}")
            return False
    
    def actualizar_resumen(self, project_id: str, 
                          resumen: Dict[str, Any]) -> bool:
        """Actualiza resumen.json."""
        try:
            project_folder = self.projects_path / project_id
            resumen_path = project_folder / "resumen.json"
            self._guardar_json(resumen_path, resumen)
            return True
        except Exception as e:
            logger.error(f"Error al actualizar resumen: {e}")
            return False
    
    def actualizar_preguntas(self, project_id: str, 
                            preguntas: List[Dict[str, Any]]) -> bool:
        """Actualiza preguntas.json."""
        try:
            project_folder = self.projects_path / project_id
            preguntas_path = project_folder / "preguntas.json"
            self._guardar_json(preguntas_path, preguntas)
            return True
        except Exception as e:
            logger.error(f"Error al actualizar preguntas: {e}")
            return False
    
    def guardar_examen(self, project_id: str, datos_examen: Dict[str, Any]) -> bool:
        """
        Guarda los resultados de un examen en examen_historial.json.
        
        Args:
            project_id: ID del proyecto
            datos_examen: Diccionario con:
                - id: ID único del examen
                - alumno: Nombre del alumno
                - fecha: Timestamp ISO
                - respuestas: Lista de {pregunta_id, respuesta, correcta}
                - nota: Nota del examen (0-10)
                - tiempo_segundos: Tiempo tomado
        """
        try:
            project_folder = self.projects_path / project_id
            historial_path = project_folder / "examen_historial.json"
            
            # Cargar historial actual
            historial = self._cargar_json(historial_path, [])
            
            # Agregar nuevo examen
            historial.append({
                "id": datos_examen.get("id", str(uuid.uuid4())),
                "alumno": datos_examen.get("alumno", ""),
                "fecha": datos_examen.get("fecha", datetime.now().isoformat()),
                "respuestas": datos_examen.get("respuestas", []),
                "nota": datos_examen.get("nota", 0),
                "tiempo_segundos": datos_examen.get("tiempo_segundos", 0)
            })
            
            self._guardar_json(historial_path, historial)
            return True
        
        except Exception as e:
            logger.error(f"Error al guardar examen: {e}")
            return False
    
    def eliminar_proyecto(self, project_id: str, db_crud) -> bool:
        """
        Elimina un proyecto completamente (BD + carpeta).
        
        Args:
            project_id: ID del proyecto
            db_crud: Instancia de ProyectosDB para eliminar de SQLite
        """
        try:
            # Eliminar de SQLite (en cascada, también elimina exámenes)
            db_crud.eliminar(project_id)
            
            # Eliminar carpeta del proyecto
            project_folder = self.projects_path / project_id
            if project_folder.exists():
                shutil.rmtree(project_folder)
            
            logger.info(f"Proyecto eliminado: {project_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error al eliminar proyecto: {e}")
            return False
    
    def obtener_ruta_proyecto(self, project_id: str) -> Optional[Path]:
        """Obtiene la ruta del proyecto."""
        project_folder = self.projects_path / project_id
        return project_folder if project_folder.exists() else None
    
    def _cargar_json(self, ruta: Path, default: Any = None) -> Any:
        """Carga un archivo JSON de forma segura."""
        try:
            if not ruta.exists():
                return default
            
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON {ruta}: {e}")
            return default
        except Exception as e:
            logger.error(f"Error al cargar JSON {ruta}: {e}")
            return default
    
    def _guardar_json(self, ruta: Path, datos: Any) -> bool:
        """Guarda datos en un archivo JSON de forma segura."""
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Error al guardar JSON {ruta}: {e}")
            return False
    
    def validar_integridad_proyecto(self, project_id: str) -> bool:
        """
        Valida que un proyecto tenga todos sus archivos necesarios.
        """
        try:
            project_folder = self.projects_path / project_id
            
            archivos_requeridos = [
                "metadata.json",
                "transcripcion_completa.json",
                "resumen.json",
                "preguntas.json",
                "examen_historial.json"
            ]
            
            for archivo in archivos_requeridos:
                if not (project_folder / archivo).exists():
                    logger.warning(f"Archivo faltante en {project_id}: {archivo}")
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error al validar integridad: {e}")
            return False
    
    def reparar_proyecto(self, project_id: str) -> bool:
        """
        Intenta reparar un proyecto creando archivos JSON faltantes.
        """
        try:
            project_folder = self.projects_path / project_id
            
            if not project_folder.exists():
                return False
            
            # Cargar metadata existente
            metadata = self._cargar_json(project_folder / "metadata.json", {})
            
            # Recrear JSONs faltantes
            if not (project_folder / "transcripcion_completa.json").exists():
                self._guardar_json(project_folder / "transcripcion_completa.json", [])
            
            if not (project_folder / "resumen.json").exists():
                self._guardar_json(project_folder / "resumen.json", {
                    "version_nino": "",
                    "version_adolescente": "",
                    "version_adulto": "",
                    "palabras_clave": []
                })
            
            if not (project_folder / "preguntas.json").exists():
                self._guardar_json(project_folder / "preguntas.json", [])
            
            if not (project_folder / "examen_historial.json").exists():
                self._guardar_json(project_folder / "examen_historial.json", [])
            
            logger.info(f"Proyecto reparado: {project_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error al reparar proyecto: {e}")
            return False
    
    def listar_proyectos_huerfanos(self) -> List[str]:
        """
        Encuentra carpetas de proyectos sin registro en SQLite.
        (Útil para limpieza)
        """
        proyectos_locales = set(d.name for d in self.projects_path.iterdir() 
                               if d.is_dir())
        return list(proyectos_locales)


# Logging básico
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Prueba de creación
    pm = ProjectManager()
    print("✓ ProjectManager inicializado")

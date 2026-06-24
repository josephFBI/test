"""
=============================================================================
MOTOR DE BÚSQUEDA - Búsquedas avanzadas y estadísticas
=============================================================================
Proporciona búsquedas combinadas, filtros, ordenamiento y estadísticas.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BuscadorProyectos:
    """Motor de búsqueda avanzada para proyectos."""
    
    def __init__(self, db_connection, project_manager):
        """
        Args:
            db_connection: Instancia de DatabaseConnection
            project_manager: Instancia de ProjectManager
        """
        self.db = db_connection
        self.pm = project_manager
    
    def buscar_por_titulo(self, titulo: str, limite: int = 50) -> List[Dict[str, Any]]:
        """
        Busca proyectos por título (búsqueda parcial).
        """
        try:
            rows = self.db.execute(
                """
                    SELECT * FROM proyectos 
                    WHERE titulo LIKE ? 
                    ORDER BY fecha_creacion DESC
                    LIMIT ?
                """,
                (f"%{titulo}%", limite)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda por título: {e}")
            return []
    
    def buscar_por_rol(self, rol: str, limite: int = 50) -> List[Dict[str, Any]]:
        """
        Filtra proyectos por rol (docente/alumno).
        """
        if rol not in ['docente', 'alumno']:
            return []
        
        try:
            rows = self.db.execute(
                """
                    SELECT * FROM proyectos 
                    WHERE rol = ? 
                    ORDER BY fecha_creacion DESC
                    LIMIT ?
                """,
                (rol, limite)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda por rol: {e}")
            return []
    
    def buscar_por_rango_fechas(self, fecha_inicio: str, fecha_fin: str, 
                               limite: int = 50) -> List[Dict[str, Any]]:
        """
        Filtra proyectos por rango de fechas (ISO format).
        
        Args:
            fecha_inicio: Fecha inicio en formato ISO (ej: "2026-06-01")
            fecha_fin: Fecha fin en formato ISO (ej: "2026-06-30")
        """
        try:
            rows = self.db.execute(
                """
                    SELECT * FROM proyectos 
                    WHERE fecha_creacion >= ? AND fecha_creacion <= ?
                    ORDER BY fecha_creacion DESC
                    LIMIT ?
                """,
                (fecha_inicio, fecha_fin, limite)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda por fechas: {e}")
            return []
    
    def buscar_por_etiqueta(self, etiqueta: str, limite: int = 50) -> List[Dict[str, Any]]:
        """
        Filtra proyectos por una etiqueta específica.
        """
        try:
            rows = self.db.execute(
                """
                    SELECT DISTINCT p.* FROM proyectos p
                    JOIN proyectos_etiquetas pe ON p.id = pe.proyecto_id
                    JOIN etiquetas e ON pe.etiqueta_id = e.id
                    WHERE e.nombre = ?
                    ORDER BY p.fecha_creacion DESC
                    LIMIT ?
                """,
                (etiqueta, limite)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda por etiqueta: {e}")
            return []
    
    def buscar_por_multiples_etiquetas(self, etiquetas: List[str], 
                                      modo_and: bool = True, 
                                      limite: int = 50) -> List[Dict[str, Any]]:
        """
        Filtra proyectos por múltiples etiquetas.
        
        Args:
            etiquetas: Lista de nombres de etiquetas
            modo_and: Si True, el proyecto debe tener TODAS las etiquetas.
                     Si False, el proyecto debe tener ALGUNA.
        """
        if not etiquetas:
            return []
        
        try:
            placeholders = ','.join(['?' for _ in etiquetas])
            
            if modo_and:
                # Proyecto debe tener TODAS las etiquetas
                query = f"""
                    SELECT p.* FROM proyectos p
                    JOIN proyectos_etiquetas pe ON p.id = pe.proyecto_id
                    JOIN etiquetas e ON pe.etiqueta_id = e.id
                    WHERE e.nombre IN ({placeholders})
                    GROUP BY p.id
                    HAVING COUNT(DISTINCT e.id) = ?
                    ORDER BY p.fecha_creacion DESC
                    LIMIT ?
                """
                params = etiquetas + [len(etiquetas), limite]
            else:
                # Proyecto debe tener ALGUNA de las etiquetas
                query = f"""
                    SELECT DISTINCT p.* FROM proyectos p
                    JOIN proyectos_etiquetas pe ON p.id = pe.proyecto_id
                    JOIN etiquetas e ON pe.etiqueta_id = e.id
                    WHERE e.nombre IN ({placeholders})
                    ORDER BY p.fecha_creacion DESC
                    LIMIT ?
                """
                params = etiquetas + [limite]
            
            rows = self.db.execute(query, tuple(params))
            return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Error en búsqueda por múltiples etiquetas: {e}")
            return []
    
    def buscar_avanzada(self, filtros: Dict[str, Any], limite: int = 50) -> List[Dict[str, Any]]:
        """
        Búsqueda avanzada combinando múltiples filtros.
        
        Args:
            filtros: Diccionario con:
                - titulo: string (búsqueda parcial)
                - rol: 'docente' o 'alumno'
                - fecha_inicio: string ISO
                - fecha_fin: string ISO
                - etiquetas: lista de strings
                - duracion_min: int (segundos)
                - duracion_max: int (segundos)
                - perfil_edad: string
                - orden_por: 'fecha', 'duracion', 'titulo' (default: fecha)
                - orden_ascendente: boolean
        
        Returns:
            Lista de proyectos que coinciden con todos los filtros
        """
        try:
            query = "SELECT DISTINCT p.* FROM proyectos p"
            params = []
            condiciones = []
            
            # Añadir JOIN para etiquetas si es necesario
            etiquetas = filtros.get('etiquetas', [])
            if etiquetas:
                query += """
                    LEFT JOIN proyectos_etiquetas pe ON p.id = pe.proyecto_id
                    LEFT JOIN etiquetas e ON pe.etiqueta_id = e.id
                """
            
            # Filtro por título
            if filtros.get('titulo'):
                condiciones.append("p.titulo LIKE ?")
                params.append(f"%{filtros['titulo']}%")
            
            # Filtro por rol
            if filtros.get('rol'):
                condiciones.append("p.rol = ?")
                params.append(filtros['rol'])
            
            # Filtro por rango de fechas
            if filtros.get('fecha_inicio'):
                condiciones.append("p.fecha_creacion >= ?")
                params.append(filtros['fecha_inicio'])
            
            if filtros.get('fecha_fin'):
                condiciones.append("p.fecha_creacion <= ?")
                params.append(filtros['fecha_fin'])
            
            # Filtro por duración
            if filtros.get('duracion_min'):
                condiciones.append("p.duracion_segundos >= ?")
                params.append(filtros['duracion_min'])
            
            if filtros.get('duracion_max'):
                condiciones.append("p.duracion_segundos <= ?")
                params.append(filtros['duracion_max'])
            
            # Filtro por perfil de edad
            if filtros.get('perfil_edad'):
                condiciones.append("p.perfil_edad = ?")
                params.append(filtros['perfil_edad'])
            
            # Filtro por etiquetas
            if etiquetas:
                placeholders = ','.join(['?' for _ in etiquetas])
                condiciones.append(f"e.nombre IN ({placeholders})")
                params.extend(etiquetas)
            
            # Construir WHERE
            if condiciones:
                query += " WHERE " + " AND ".join(condiciones)
            
            # Ordenamiento
            orden_por = filtros.get('orden_por', 'fecha')
            orden_ascendente = filtros.get('orden_ascendente', False)
            orden_dir = "ASC" if orden_ascendente else "DESC"
            
            if orden_por == 'duracion':
                query += f" ORDER BY p.duracion_segundos {orden_dir}"
            elif orden_por == 'titulo':
                query += f" ORDER BY p.titulo {orden_dir}"
            else:  # fecha
                query += f" ORDER BY p.fecha_creacion {orden_dir}"
            
            query += f" LIMIT ?"
            params.append(limite)
            
            rows = self.db.execute(query, tuple(params))
            return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Error en búsqueda avanzada: {e}")
            return []
    
    def buscar_por_dias_atras(self, dias: int = 7, limite: int = 50) -> List[Dict[str, Any]]:
        """
        Obtiene proyectos de los últimos N días.
        """
        try:
            fecha_limite = (datetime.now() - timedelta(days=dias)).isoformat()
            return self.buscar_por_rango_fechas(fecha_limite, 
                                               datetime.now().isoformat(), 
                                               limite)
        except Exception as e:
            logger.error(f"Error en búsqueda por días: {e}")
            return []


class BuscadorExamenes:
    """Motor de búsqueda para exámenes."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def obtener_examenes_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los exámenes de un proyecto."""
        try:
            rows = self.db.execute(
                "SELECT * FROM examenes WHERE proyecto_id = ? ORDER BY fecha DESC",
                (proyecto_id,)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener exámenes: {e}")
            return []
    
    def obtener_examenes_alumno(self, alumno_nombre: str) -> List[Dict[str, Any]]:
        """Obtiene todos los exámenes de un alumno."""
        try:
            rows = self.db.execute(
                "SELECT * FROM examenes WHERE alumno_nombre = ? ORDER BY fecha DESC",
                (alumno_nombre,)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener exámenes del alumno: {e}")
            return []
    
    def buscar_por_nota(self, proyecto_id: str, nota_min: float, 
                       nota_max: float = 10.0) -> List[Dict[str, Any]]:
        """Filtra exámenes por rango de notas."""
        try:
            rows = self.db.execute(
                """
                    SELECT * FROM examenes 
                    WHERE proyecto_id = ? AND nota >= ? AND nota <= ?
                    ORDER BY nota DESC
                """,
                (proyecto_id, nota_min, nota_max)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda por nota: {e}")
            return []
    
    def buscar_por_rango_fechas(self, proyecto_id: str, fecha_inicio: str, 
                               fecha_fin: str) -> List[Dict[str, Any]]:
        """Filtra exámenes por rango de fechas."""
        try:
            rows = self.db.execute(
                """
                    SELECT * FROM examenes 
                    WHERE proyecto_id = ? 
                    AND fecha >= ? AND fecha <= ?
                    ORDER BY fecha DESC
                """,
                (proyecto_id, fecha_inicio, fecha_fin)
            )
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error en búsqueda de exámenes por fechas: {e}")
            return []


class Estadisticas:
    """Generador de estadísticas y reportes."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def estadisticas_generales(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales del sistema."""
        try:
            # Total de proyectos
            total_proyectos = self.db.execute_single(
                "SELECT COUNT(*) as count FROM proyectos"
            )['count']
            
            # Total por rol
            por_rol = self.db.execute(
                """
                    SELECT rol, COUNT(*) as count 
                    FROM proyectos 
                    GROUP BY rol
                """
            )
            
            # Duración promedio
            duracion_promedio = self.db.execute_single(
                "SELECT AVG(duracion_segundos) as avg FROM proyectos"
            )
            
            # Total de exámenes
            total_examenes = self.db.execute_single(
                "SELECT COUNT(*) as count FROM examenes"
            )['count']
            
            # Nota promedio
            nota_promedio = self.db.execute_single(
                "SELECT AVG(nota) as avg FROM examenes"
            )
            
            return {
                "total_proyectos": total_proyectos,
                "total_examenes": total_examenes,
                "duracion_promedio_segundos": duracion_promedio['avg'],
                "nota_promedio_examenes": nota_promedio['avg'],
                "proyectos_por_rol": {row['rol']: row['count'] for row in por_rol}
            }
        except Exception as e:
            logger.error(f"Error en estadísticas generales: {e}")
            return {}
    
    def estadisticas_proyecto(self, proyecto_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de un proyecto específico."""
        try:
            # Datos básicos del proyecto
            proyecto = self.db.execute_single(
                "SELECT * FROM proyectos WHERE id = ?",
                (proyecto_id,)
            )
            
            if not proyecto:
                return {}
            
            # Exámenes del proyecto
            examenes = self.db.execute(
                "SELECT * FROM examenes WHERE proyecto_id = ?",
                (proyecto_id,)
            )
            
            examenes_list = [dict(row) for row in examenes]
            
            # Calcular estadísticas
            total_examenes = len(examenes_list)
            
            if total_examenes > 0:
                notas = [e['nota'] for e in examenes_list]
                promedio_nota = sum(notas) / len(notas)
                nota_maxima = max(notas)
                nota_minima = min(notas)
            else:
                promedio_nota = nota_maxima = nota_minima = 0
            
            # Etiquetas
            etiquetas = self.db.execute(
                """
                    SELECT e.nombre FROM etiquetas e
                    JOIN proyectos_etiquetas pe ON e.id = pe.etiqueta_id
                    WHERE pe.proyecto_id = ?
                """,
                (proyecto_id,)
            )
            
            return {
                "proyecto_id": proyecto_id,
                "titulo": proyecto['titulo'],
                "rol": proyecto['rol'],
                "duracion_segundos": proyecto['duracion_segundos'],
                "fecha_creacion": proyecto['fecha_creacion'],
                "total_examenes": total_examenes,
                "promedio_nota": promedio_nota,
                "nota_maxima": nota_maxima,
                "nota_minima": nota_minima,
                "etiquetas": [row['nombre'] for row in etiquetas]
            }
        except Exception as e:
            logger.error(f"Error en estadísticas del proyecto: {e}")
            return {}
    
    def estadisticas_alumno(self, alumno_nombre: str) -> Dict[str, Any]:
        """Obtiene estadísticas de desempeño de un alumno."""
        try:
            examenes = self.db.execute(
                "SELECT * FROM examenes WHERE alumno_nombre = ? ORDER BY fecha DESC",
                (alumno_nombre,)
            )
            
            examenes_list = [dict(row) for row in examenes]
            
            if not examenes_list:
                return {
                    "alumno": alumno_nombre,
                    "total_examenes": 0
                }
            
            notas = [e['nota'] for e in examenes_list]
            aciertos = [e['preguntas_acertadas'] for e in examenes_list]
            
            return {
                "alumno": alumno_nombre,
                "total_examenes": len(examenes_list),
                "promedio_nota": sum(notas) / len(notas),
                "nota_maxima": max(notas),
                "nota_minima": min(notas),
                "promedio_aciertos": sum(aciertos) / len(aciertos) if aciertos else 0,
                "ultimos_5_examenes": examenes_list[:5]
            }
        except Exception as e:
            logger.error(f"Error en estadísticas del alumno: {e}")
            return {}
    
    def etiquetas_mas_usadas(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Obtiene las etiquetas más usadas."""
        try:
            rows = self.db.execute(
                """
                    SELECT e.nombre, COUNT(pe.proyecto_id) as count
                    FROM etiquetas e
                    LEFT JOIN proyectos_etiquetas pe ON e.id = pe.etiqueta_id
                    GROUP BY e.id
                    ORDER BY count DESC
                    LIMIT ?
                """,
                (limite,)
            )
            return [{"etiqueta": row['nombre'], "count": row['count']} for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener etiquetas más usadas: {e}")
            return []
    
    def alumnos_mas_activos(self, limite: int = 10) -> List[Dict[str, Any]]:
        """Obtiene los alumnos con más exámenes realizados."""
        try:
            rows = self.db.execute(
                """
                    SELECT alumno_nombre, COUNT(*) as count, AVG(nota) as promedio
                    FROM examenes
                    GROUP BY alumno_nombre
                    ORDER BY count DESC
                    LIMIT ?
                """,
                (limite,)
            )
            return [{"alumno": row['alumno_nombre'], 
                    "examenes": row['count'], 
                    "promedio_nota": row['promedio']} 
                   for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener alumnos más activos: {e}")
            return []


# Logging
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("✓ Módulo de búsqueda cargado")

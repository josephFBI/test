"""
=============================================================================
CAPA DE BASE DE DATOS - SQLite
=============================================================================
Maneja toda la conexión, inicialización y operaciones CRUD con SQLite.
Incluye transacciones, índices y validaciones.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Gestor de conexiones a SQLite con soporte para transacciones.
    Implementa el patrón Singleton para evitar conexiones múltiples.
    """
    
    _instance = None
    
    def __new__(cls, db_path: Path):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Path):
        if self._initialized:
            return
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        self._initialize_database()
    
    def _initialize_database(self):
        """Crea las tablas si no existen."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Tabla de proyectos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proyectos (
                    id TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    rol TEXT CHECK(rol IN ('docente', 'alumno')) NOT NULL,
                    perfil_edad TEXT CHECK(perfil_edad IN ('nino', 'adolescente', 'adulto', '')),
                    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                    duracion_segundos INTEGER DEFAULT 0,
                    ruta_carpeta TEXT NOT NULL,
                    ultima_modificacion TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de exámenes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS examenes (
                    id TEXT PRIMARY KEY,
                    proyecto_id TEXT NOT NULL,
                    alumno_nombre TEXT NOT NULL,
                    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                    nota REAL CHECK(nota >= 0 AND nota <= 10),
                    preguntas_acertadas INTEGER DEFAULT 0,
                    preguntas_totales INTEGER DEFAULT 0,
                    preguntas_falladas_json TEXT,
                    tiempo_segundos INTEGER,
                    FOREIGN KEY(proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
                )
            """)
            
            # Tabla de etiquetas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS etiquetas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL
                )
            """)
            
            # Tabla de relación proyectos-etiquetas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proyectos_etiquetas (
                    proyecto_id TEXT,
                    etiqueta_id INTEGER,
                    PRIMARY KEY (proyecto_id, etiqueta_id),
                    FOREIGN KEY(proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
                    FOREIGN KEY(etiqueta_id) REFERENCES etiquetas(id) ON DELETE CASCADE
                )
            """)
            
            # Tabla de configuración global
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracion (
                    clave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL
                )
            """)
            
            # Crear índices para búsquedas rápidas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proyectos_fecha ON proyectos(fecha_creacion)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proyectos_rol ON proyectos(rol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proyectos_titulo ON proyectos(titulo)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_examenes_proyecto ON examenes(proyecto_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_examenes_nota ON examenes(nota)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_examenes_alumno ON examenes(alumno_nombre)")
            
            conn.commit()
            logger.info(f"Base de datos inicializada en {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Error al inicializar la base de datos: {e}")
            raise
        finally:
            conn.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """Retorna una conexión a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Ejecuta una consulta SELECT."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()
    
    def execute_single(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Ejecuta una consulta SELECT que retorna un único resultado."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            conn.close()
    
    def insert(self, query: str, params: tuple = ()) -> int:
        """Ejecuta un INSERT y retorna el last_insert_rowid."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error al insertar: {e}")
            raise
        finally:
            conn.close()
    
    def update(self, query: str, params: tuple = ()) -> int:
        """Ejecuta un UPDATE y retorna el número de filas afectadas."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error al actualizar: {e}")
            raise
        finally:
            conn.close()
    
    def delete(self, query: str, params: tuple = ()) -> int:
        """Ejecuta un DELETE y retorna el número de filas afectadas."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error al eliminar: {e}")
            raise
        finally:
            conn.close()
    
    def execute_transaction(self, operations: List[Tuple[str, tuple]]) -> bool:
        """
        Ejecuta múltiples operaciones en una transacción.
        Si alguna falla, revierte todas.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            for query, params in operations:
                cursor.execute(query, params)
            conn.commit()
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Error en transacción: {e}")
            return False
        finally:
            conn.close()


class ProyectosDB:
    """CRUD para la tabla de proyectos."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def crear(self, proyecto_id: str, titulo: str, rol: str, 
              perfil_edad: str, duracion_segundos: int, 
              ruta_carpeta: str, etiquetas: List[str] = None) -> bool:
        """Crea un nuevo proyecto en la BD."""
        fecha_actual = datetime.now().isoformat()
        
        try:
            operations = [
                ("""
                    INSERT INTO proyectos 
                    (id, titulo, rol, perfil_edad, fecha_creacion, 
                     duracion_segundos, ruta_carpeta, ultima_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (proyecto_id, titulo, rol, perfil_edad, fecha_actual, 
                      duracion_segundos, ruta_carpeta, fecha_actual))
            ]
            
            # Agregar etiquetas
            if etiquetas:
                for etiqueta in etiquetas:
                    operations.append((
                        "INSERT OR IGNORE INTO etiquetas (nombre) VALUES (?)",
                        (etiqueta,)
                    ))
                
                # Obtener IDs de etiquetas y crear relaciones
                for etiqueta in etiquetas:
                    operations.append((
                        "SELECT id FROM etiquetas WHERE nombre = ?",
                        (etiqueta,)
                    ))
            
            return self.db.execute_transaction(operations)
        
        except Exception as e:
            logger.error(f"Error al crear proyecto: {e}")
            return False
    
    def obtener(self, proyecto_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un proyecto por su ID."""
        row = self.db.execute_single(
            "SELECT * FROM proyectos WHERE id = ?",
            (proyecto_id,)
        )
        return dict(row) if row else None
    
    def obtener_todos(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Obtiene todos los proyectos con paginación."""
        rows = self.db.execute(
            "SELECT * FROM proyectos ORDER BY fecha_creacion DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [dict(row) for row in rows]
    
    def actualizar(self, proyecto_id: str, **kwargs) -> bool:
        """Actualiza un proyecto."""
        campos_permitidos = {'titulo', 'rol', 'perfil_edad', 'duracion_segundos'}
        campos = {k: v for k, v in kwargs.items() if k in campos_permitidos}
        
        if not campos:
            return False
        
        campos['ultima_modificacion'] = datetime.now().isoformat()
        
        set_clause = ', '.join([f"{k} = ?" for k in campos.keys()])
        values = list(campos.values()) + [proyecto_id]
        
        try:
            self.db.update(
                f"UPDATE proyectos SET {set_clause} WHERE id = ?",
                tuple(values)
            )
            return True
        except Exception as e:
            logger.error(f"Error al actualizar proyecto: {e}")
            return False
    
    def eliminar(self, proyecto_id: str) -> bool:
        """Elimina un proyecto (también elimina exámenes asociados)."""
        try:
            self.db.delete("DELETE FROM proyectos WHERE id = ?", (proyecto_id,))
            return True
        except Exception as e:
            logger.error(f"Error al eliminar proyecto: {e}")
            return False


class ExamenesDB:
    """CRUD para la tabla de exámenes."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def crear(self, examen_id: str, proyecto_id: str, alumno_nombre: str,
              nota: float, preguntas_acertadas: int, preguntas_totales: int,
              preguntas_falladas_json: str = None, tiempo_segundos: int = 0) -> bool:
        """Crea un nuevo examen."""
        fecha_actual = datetime.now().isoformat()
        
        try:
            self.db.insert(
                """
                    INSERT INTO examenes 
                    (id, proyecto_id, alumno_nombre, fecha, nota, 
                     preguntas_acertadas, preguntas_totales, 
                     preguntas_falladas_json, tiempo_segundos)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (examen_id, proyecto_id, alumno_nombre, fecha_actual, nota,
                 preguntas_acertadas, preguntas_totales, 
                 preguntas_falladas_json, tiempo_segundos)
            )
            return True
        except Exception as e:
            logger.error(f"Error al crear examen: {e}")
            return False
    
    def obtener(self, examen_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un examen por su ID."""
        row = self.db.execute_single(
            "SELECT * FROM examenes WHERE id = ?",
            (examen_id,)
        )
        return dict(row) if row else None
    
    def obtener_por_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los exámenes de un proyecto."""
        rows = self.db.execute(
            "SELECT * FROM examenes WHERE proyecto_id = ? ORDER BY fecha DESC",
            (proyecto_id,)
        )
        return [dict(row) for row in rows]
    
    def obtener_por_alumno(self, alumno_nombre: str) -> List[Dict[str, Any]]:
        """Obtiene todos los exámenes de un alumno."""
        rows = self.db.execute(
            "SELECT * FROM examenes WHERE alumno_nombre = ? ORDER BY fecha DESC",
            (alumno_nombre,)
        )
        return [dict(row) for row in rows]
    
    def obtener_estadisticas_alumno(self, alumno_nombre: str) -> Dict[str, Any]:
        """Obtiene estadísticas de un alumno."""
        row = self.db.execute_single(
            """
                SELECT 
                    COUNT(*) as total_examenes,
                    AVG(nota) as promedio_nota,
                    MAX(nota) as nota_maxima,
                    MIN(nota) as nota_minima
                FROM examenes 
                WHERE alumno_nombre = ?
            """,
            (alumno_nombre,)
        )
        return dict(row) if row else {}
    
    def actualizar(self, examen_id: str, **kwargs) -> bool:
        """Actualiza un examen."""
        campos_permitidos = {'nota', 'preguntas_acertadas', 'preguntas_totales',
                           'preguntas_falladas_json', 'tiempo_segundos'}
        campos = {k: v for k, v in kwargs.items() if k in campos_permitidos}
        
        if not campos:
            return False
        
        set_clause = ', '.join([f"{k} = ?" for k in campos.keys()])
        values = list(campos.values()) + [examen_id]
        
        try:
            self.db.update(
                f"UPDATE examenes SET {set_clause} WHERE id = ?",
                tuple(values)
            )
            return True
        except Exception as e:
            logger.error(f"Error al actualizar examen: {e}")
            return False
    
    def eliminar(self, examen_id: str) -> bool:
        """Elimina un examen."""
        try:
            self.db.delete("DELETE FROM examenes WHERE id = ?", (examen_id,))
            return True
        except Exception as e:
            logger.error(f"Error al eliminar examen: {e}")
            return False


class EtiquetasDB:
    """CRUD para la tabla de etiquetas."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def crear(self, nombre: str) -> int:
        """Crea una nueva etiqueta."""
        try:
            return self.db.insert(
                "INSERT OR IGNORE INTO etiquetas (nombre) VALUES (?)",
                (nombre,)
            )
        except Exception as e:
            logger.error(f"Error al crear etiqueta: {e}")
            return -1
    
    def obtener_todas(self) -> List[Dict[str, Any]]:
        """Obtiene todas las etiquetas."""
        rows = self.db.execute("SELECT * FROM etiquetas ORDER BY nombre")
        return [dict(row) for row in rows]
    
    def obtener_por_proyecto(self, proyecto_id: str) -> List[str]:
        """Obtiene las etiquetas de un proyecto."""
        rows = self.db.execute(
            """
                SELECT e.nombre FROM etiquetas e
                JOIN proyectos_etiquetas pe ON e.id = pe.etiqueta_id
                WHERE pe.proyecto_id = ?
            """,
            (proyecto_id,)
        )
        return [row['nombre'] for row in rows]
    
    def agregar_a_proyecto(self, proyecto_id: str, etiqueta_nombre: str) -> bool:
        """Agrega una etiqueta a un proyecto."""
        try:
            # Crear etiqueta si no existe
            self.crear(etiqueta_nombre)
            
            # Obtener ID de la etiqueta
            row = self.db.execute_single(
                "SELECT id FROM etiquetas WHERE nombre = ?",
                (etiqueta_nombre,)
            )
            
            if not row:
                return False
            
            etiqueta_id = row['id']
            
            # Agregar relación
            self.db.insert(
                """
                    INSERT OR IGNORE INTO proyectos_etiquetas 
                    (proyecto_id, etiqueta_id) VALUES (?, ?)
                """,
                (proyecto_id, etiqueta_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error al agregar etiqueta a proyecto: {e}")
            return False
    
    def eliminar_de_proyecto(self, proyecto_id: str, etiqueta_nombre: str) -> bool:
        """Elimina una etiqueta de un proyecto."""
        try:
            row = self.db.execute_single(
                "SELECT id FROM etiquetas WHERE nombre = ?",
                (etiqueta_nombre,)
            )
            
            if not row:
                return False
            
            self.db.delete(
                "DELETE FROM proyectos_etiquetas WHERE proyecto_id = ? AND etiqueta_id = ?",
                (proyecto_id, row['id'])
            )
            return True
        except Exception as e:
            logger.error(f"Error al eliminar etiqueta de proyecto: {e}")
            return False


class ConfiguracionDB:
    """CRUD para la tabla de configuración."""
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def obtener(self, clave: str, default: str = "") -> str:
        """Obtiene un valor de configuración."""
        row = self.db.execute_single(
            "SELECT valor FROM configuracion WHERE clave = ?",
            (clave,)
        )
        return row['valor'] if row else default
    
    def guardar(self, clave: str, valor: str) -> bool:
        """Guarda un valor de configuración."""
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
                (clave, valor)
            )
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False
    
    def obtener_todos(self) -> Dict[str, str]:
        """Obtiene toda la configuración."""
        rows = self.db.execute("SELECT * FROM configuracion")
        return {row['clave']: row['valor'] for row in rows}


# Logging básico
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Prueba de inicialización
    db_path = Path("user_data/database/app.db")
    db = DatabaseConnection(db_path)
    print("✓ Base de datos inicializada correctamente")

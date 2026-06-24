"""
=============================================================================
IMPORTACIÓN/EXPORTACIÓN - ZIP y Backups
=============================================================================
Permite exportar e importar proyectos como archivos ZIP.
Incluye backup automático de la base de datos.
"""

import zipfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class ImportadorExportador:
    """Gestor de importación/exportación de proyectos."""
    
    def __init__(self, project_manager, db_crud):
        """
        Args:
            project_manager: Instancia de ProjectManager
            db_crud: Instancia de ProyectosDB
        """
        self.pm = project_manager
        self.db_crud = db_crud
        self.exports_path = Path("exports")
        self.exports_path.mkdir(exist_ok=True)
    
    def exportar_proyecto_zip(self, project_id: str, 
                             ruta_destino: Optional[Path] = None) -> Optional[Path]:
        """
        Exporta un proyecto completo como archivo ZIP.
        Incluye todos los archivos JSON y audios.
        
        Args:
            project_id: ID del proyecto a exportar
            ruta_destino: Ruta donde guardar el ZIP (default: exports/)
        
        Returns:
            Ruta del archivo ZIP creado, o None si hay error
        """
        try:
            # Obtener información del proyecto
            proyecto = self.db_crud.obtener(project_id)
            if not proyecto:
                logger.error(f"Proyecto no encontrado: {project_id}")
                return None
            
            # Ruta de la carpeta del proyecto
            project_folder = Path(proyecto['ruta_carpeta'])
            if not project_folder.exists():
                logger.error(f"Carpeta del proyecto no existe: {project_folder}")
                return None
            
            # Definir ruta de destino
            if ruta_destino is None:
                ruta_destino = self.exports_path
                ruta_destino.mkdir(exist_ok=True)
            
            # Crear nombre del ZIP
            fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
            titulo_safe = proyecto['titulo'].replace(" ", "_").replace("/", "-")
            zip_nombre = f"{titulo_safe}_{fecha_actual}.zip"
            zip_path = ruta_destino / zip_nombre
            
            # Crear ZIP
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Agregar todos los archivos de la carpeta
                for archivo in project_folder.rglob('*'):
                    if archivo.is_file():
                        # Ruta relativa dentro del ZIP
                        arcname = archivo.relative_to(project_folder.parent)
                        zipf.write(archivo, arcname)
            
            logger.info(f"Proyecto exportado: {zip_path}")
            return zip_path
        
        except Exception as e:
            logger.error(f"Error al exportar proyecto: {e}")
            return None
    
    def exportar_multiples_proyectos_zip(self, project_ids: List[str],
                                        ruta_destino: Optional[Path] = None) -> Optional[Path]:
        """
        Exporta múltiples proyectos en un único ZIP.
        
        Args:
            project_ids: Lista de IDs de proyectos
            ruta_destino: Ruta donde guardar el ZIP
        
        Returns:
            Ruta del archivo ZIP creado
        """
        try:
            if ruta_destino is None:
                ruta_destino = self.exports_path
                ruta_destino.mkdir(exist_ok=True)
            
            fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_nombre = f"proyectos_exportados_{fecha_actual}.zip"
            zip_path = ruta_destino / zip_nombre
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for project_id in project_ids:
                    proyecto = self.db_crud.obtener(project_id)
                    if not proyecto:
                        logger.warning(f"Proyecto no encontrado: {project_id}")
                        continue
                    
                    project_folder = Path(proyecto['ruta_carpeta'])
                    if not project_folder.exists():
                        logger.warning(f"Carpeta no existe: {project_folder}")
                        continue
                    
                    # Agregar archivos
                    for archivo in project_folder.rglob('*'):
                        if archivo.is_file():
                            arcname = archivo.relative_to(project_folder.parent)
                            zipf.write(archivo, arcname)
            
            logger.info(f"Múltiples proyectos exportados: {zip_path}")
            return zip_path
        
        except Exception as e:
            logger.error(f"Error al exportar múltiples proyectos: {e}")
            return None
    
    def importar_proyecto_zip(self, zip_path: Path) -> Optional[str]:
        """
        Importa un proyecto desde un archivo ZIP.
        
        Args:
            zip_path: Ruta del archivo ZIP
        
        Returns:
            ID del proyecto importado, o None si hay error
        """
        try:
            if not zip_path.exists():
                logger.error(f"Archivo ZIP no encontrado: {zip_path}")
                return None
            
            # Crear carpeta temporal para extracción
            temp_extract = Path("temp_extract")
            temp_extract.mkdir(exist_ok=True)
            
            # Extraer ZIP
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_extract)
            
            # Buscar carpeta de proyecto (debe tener metadata.json)
            project_folder = None
            for carpeta in temp_extract.iterdir():
                if (carpeta / "metadata.json").exists():
                    project_folder = carpeta
                    break
            
            if not project_folder:
                logger.error("ZIP no contiene una estructura válida de proyecto")
                shutil.rmtree(temp_extract)
                return None
            
            # Cargar metadata
            with open(project_folder / "metadata.json", 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Crear nuevo ID para evitar conflictos
            import uuid
            nuevo_id = str(uuid.uuid4())
            nueva_carpeta = self.pm.projects_path / nuevo_id
            
            # Mover carpeta
            shutil.move(str(project_folder), str(nueva_carpeta))
            
            # Actualizar metadata con nuevo ID
            metadata['id'] = nuevo_id
            with open(nueva_carpeta / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Guardar en BD
            exito = self.db_crud.crear(
                proyecto_id=nuevo_id,
                titulo=metadata.get('titulo', 'Proyecto importado'),
                rol=metadata.get('rol', 'alumno'),
                perfil_edad=metadata.get('perfil_edad', 'adulto'),
                duracion_segundos=metadata.get('duracion_segundos', 0),
                ruta_carpeta=str(nueva_carpeta),
                etiquetas=metadata.get('etiquetas', [])
            )
            
            # Limpiar temporal
            shutil.rmtree(temp_extract)
            
            if exito:
                logger.info(f"Proyecto importado: {nuevo_id}")
                return nuevo_id
            else:
                logger.error("Error al registrar proyecto en BD")
                shutil.rmtree(nueva_carpeta)
                return None
        
        except Exception as e:
            logger.error(f"Error al importar proyecto: {e}")
            return None
    
    def exportar_todas_clases_docente(self, rol: str = 'docente',
                                     ruta_destino: Optional[Path] = None) -> Optional[Path]:
        """
        Exporta todas las clases de un rol específico (docente/alumno).
        
        Args:
            rol: 'docente' o 'alumno'
            ruta_destino: Ruta donde guardar el ZIP
        
        Returns:
            Ruta del archivo ZIP
        """
        try:
            # Obtener todos los proyectos del rol
            rows = self.db.db.execute(
                "SELECT id FROM proyectos WHERE rol = ?",
                (rol,)
            )
            
            project_ids = [row['id'] for row in rows]
            
            if not project_ids:
                logger.warning(f"No hay proyectos con rol: {rol}")
                return None
            
            return self.exportar_multiples_proyectos_zip(project_ids, ruta_destino)
        
        except Exception as e:
            logger.error(f"Error al exportar clases: {e}")
            return None


class BackupManager:
    """Gestor de backups de la base de datos."""
    
    def __init__(self, db_path: Path):
        """
        Args:
            db_path: Ruta de la base de datos SQLite
        """
        self.db_path = db_path
        self.backups_path = db_path.parent / "backups"
        self.backups_path.mkdir(exist_ok=True)
    
    def crear_backup(self, nombre_custom: Optional[str] = None) -> Optional[Path]:
        """
        Crea un backup de la base de datos.
        
        Args:
            nombre_custom: Nombre personalizado (sin .db)
        
        Returns:
            Ruta del archivo de backup
        """
        try:
            if not self.db_path.exists():
                logger.warning("Base de datos no encontrada")
                return None
            
            if nombre_custom:
                backup_nombre = f"{nombre_custom}.db"
            else:
                fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_nombre = f"backup_{fecha_actual}.db"
            
            backup_path = self.backups_path / backup_nombre
            
            # Copiar base de datos
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Backup creado: {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Error al crear backup: {e}")
            return None
    
    def listar_backups(self) -> List[Path]:
        """Lista todos los backups disponibles."""
        try:
            return sorted(self.backups_path.glob("backup_*.db"))
        except Exception as e:
            logger.error(f"Error al listar backups: {e}")
            return []
    
    def restaurar_backup(self, backup_path: Path) -> bool:
        """
        Restaura una base de datos desde un backup.
        
        CUIDADO: Esto sobrescribe la base de datos actual.
        
        Args:
            backup_path: Ruta del backup a restaurar
        
        Returns:
            True si se restauró exitosamente
        """
        try:
            if not backup_path.exists():
                logger.error(f"Archivo de backup no encontrado: {backup_path}")
                return False
            
            # Crear backup del actual antes de sobrescribir
            self.crear_backup("pre_restauracion")
            
            # Restaurar
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Base de datos restaurada desde: {backup_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error al restaurar backup: {e}")
            return False
    
    def eliminar_backup(self, backup_path: Path) -> bool:
        """Elimina un archivo de backup."""
        try:
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Backup eliminado: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al eliminar backup: {e}")
            return False
    
    def limpiar_backups_antiguos(self, dias: int = 30) -> int:
        """
        Elimina backups más antiguos que N días.
        
        Args:
            dias: Antigüedad mínima en días
        
        Returns:
            Número de backups eliminados
        """
        try:
            from datetime import timedelta
            
            fecha_limite = datetime.now() - timedelta(days=dias)
            contador = 0
            
            for backup_path in self.listar_backups():
                # Obtener fecha de modificación
                mtime = datetime.fromtimestamp(backup_path.stat().st_mtime)
                
                if mtime < fecha_limite:
                    self.eliminar_backup(backup_path)
                    contador += 1
            
            logger.info(f"Backups antiguos eliminados: {contador}")
            return contador
        
        except Exception as e:
            logger.error(f"Error al limpiar backups: {e}")
            return 0


# Logging
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("✓ Módulo de importación/exportación cargado")

"""
=============================================================================
INICIALIZACIÓN DEL SISTEMA
=============================================================================
Script que inicializa la base de datos, crea las carpetas necesarias
y configura el sistema para la primera ejecución.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import logging
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InicializadorSistema:
    """Inicializa la estructura del sistema."""
    
    def __init__(self, base_path: str = "user_data"):
        self.base_path = Path(base_path)
        self.db_path = self.base_path / "database"
        self.projects_path = self.base_path / "projects"
        self.backups_path = self.base_path / "backups"
        self.exports_path = Path("exports")
        self.logs_path = self.base_path / "logs"
    
    def crear_estructura_carpetas(self) -> bool:
        """Crea la estructura de carpetas necesarias."""
        try:
            carpetas = [
                self.db_path,
                self.projects_path,
                self.backups_path,
                self.exports_path,
                self.logs_path
            ]
            
            for carpeta in carpetas:
                carpeta.mkdir(parents=True, exist_ok=True)
                print(f"✓ Carpeta creada/verificada: {carpeta}")
            
            logger.info("Estructura de carpetas creada exitosamente")
            return True
        
        except Exception as e:
            print(f"✗ Error al crear carpetas: {e}")
            logger.error(f"Error al crear carpetas: {e}")
            return False
    
    def inicializar_base_datos(self) -> bool:
        """Inicializa la base de datos SQLite."""
        try:
            from database import DatabaseConnection
            
            db = DatabaseConnection(self.db_path / "app.db")
            print("✓ Base de datos inicializada")
            logger.info("Base de datos SQLite inicializada")
            return True
        
        except Exception as e:
            print(f"✗ Error al inicializar BD: {e}")
            logger.error(f"Error al inicializar BD: {e}")
            return False
    
    def crear_archivo_configuracion(self) -> bool:
        """Crea un archivo de configuración inicial."""
        try:
            config = {
                "aplicacion": {
                    "nombre": "Sistema de Gestor de Clases",
                    "version": "1.0.0",
                    "fecha_instalacion": datetime.now().isoformat()
                },
                "rutas": {
                    "base": str(self.base_path),
                    "proyectos": str(self.projects_path),
                    "backups": str(self.backups_path),
                    "logs": str(self.logs_path)
                },
                "base_datos": {
                    "tipo": "SQLite",
                    "ruta": str(self.db_path / "app.db")
                },
                "procesamiento": {
                    "idioma": "es",
                    "modelo_whisper": "tiny",
                    "filtro_ruido": True,
                    "segmentar_silencios": True
                },
                "api": {
                    "host": "0.0.0.0",
                    "puerto": 8000,
                    "debug": False
                }
            }
            
            config_path = self.base_path / "config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Archivo de configuración creado: {config_path}")
            logger.info("Archivo de configuración creado")
            return True
        
        except Exception as e:
            print(f"✗ Error al crear configuración: {e}")
            logger.error(f"Error al crear configuración: {e}")
            return False
    
    def crear_ejemplo_proyecto(self) -> bool:
        """Crea un proyecto de ejemplo."""
        try:
            from database import DatabaseConnection, ProyectosDB
            from project_manager import ProjectManager
            import uuid
            
            db = DatabaseConnection(self.db_path / "app.db")
            db_crud = ProyectosDB(db)
            pm = ProjectManager(str(self.base_path))
            
            # Crear proyecto de ejemplo
            proyecto_id = str(uuid.uuid4())
            
            datos_ejemplo = {
                "titulo": "Ejemplo: Introducción a la Programación",
                "descripcion": "Clase de ejemplo del sistema",
                "rol": "docente",
                "perfil_edad": "adulto",
                "duracion_segundos": 3600,
                "etiquetas": ["programación", "ejemplo", "principiantes"]
            }
            
            proyecto_id = pm.crear_proyecto(datos_ejemplo, db_crud)
            
            if proyecto_id:
                print(f"✓ Proyecto de ejemplo creado: {proyecto_id}")
                logger.info(f"Proyecto de ejemplo creado: {proyecto_id}")
                return True
            else:
                print("✗ Error al crear proyecto de ejemplo")
                return False
        
        except Exception as e:
            print(f"✗ Error al crear proyecto de ejemplo: {e}")
            logger.error(f"Error al crear proyecto de ejemplo: {e}")
            return False
    
    def ejecutar_inicializacion(self, crear_ejemplo: bool = True) -> bool:
        """Ejecuta todo el proceso de inicialización."""
        print("""
        ╔════════════════════════════════════════════════════════════╗
        ║   INICIALIZADOR DEL SISTEMA - Gestor de Clases             ║
        ║   Versión 1.0.0                                            ║
        ╚════════════════════════════════════════════════════════════╝
        """)
        
        pasos = [
            ("Creando estructura de carpetas...", self.crear_estructura_carpetas),
            ("Inicializando base de datos...", self.inicializar_base_datos),
            ("Creando archivo de configuración...", self.crear_archivo_configuracion)
        ]
        
        # Agregar creación de ejemplo si se solicita
        if crear_ejemplo:
            pasos.append(("Creando proyecto de ejemplo...", self.crear_ejemplo_proyecto))
        
        todos_ok = True
        
        for paso, funcion in pasos:
            print(f"\n{paso}")
            if not funcion():
                todos_ok = False
                logger.warning(f"Paso no completado: {paso}")
        
        if todos_ok:
            print("""
        ╔════════════════════════════════════════════════════════════╗
        ║   ✓ INICIALIZACIÓN COMPLETADA EXITOSAMENTE                ║
        ║                                                            ║
        ║   Pasos siguientes:                                        ║
        ║   1. Revisa el archivo user_data/config.json             ║
        ║   2. Ejecuta: python main.py                              ║
        ║   3. Abre http://localhost:8000 en tu navegador            ║
        ║   4. Accede a la documentación en /docs                    ║
        ╚════════════════════════════════════════════════════════════╝
            """)
            logger.info("Inicialización completada exitosamente")
            return True
        else:
            print("""
        ╔════════════════════════════════════════════════════════════╗
        ║   ✗ INICIALIZACIÓN INCOMPLETE                             ║
        ║                                                            ║
        ║   Revisa el archivo sistema.log para más detalles          ║
        ╚════════════════════════════════════════════════════════════╝
            """)
            logger.error("Inicialización fallida")
            return False


def main():
    """Punto de entrada del inicializador."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Inicializa el Sistema de Gestor de Clases'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        default='user_data',
        help='Ruta base para los datos (default: user_data)'
    )
    parser.add_argument(
        '--sin-ejemplo',
        action='store_true',
        help='No crear proyecto de ejemplo'
    )
    
    args = parser.parse_args()
    
    inicializador = InicializadorSistema(args.base_path)
    exito = inicializador.ejecutar_inicializacion(
        crear_ejemplo=not args.sin_ejemplo
    )
    
    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    main()

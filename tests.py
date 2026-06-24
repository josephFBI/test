"""
=============================================================================
TESTS - Suite de pruebas del sistema
=============================================================================
Pruebas unitarias e integración para verificar el correcto funcionamiento.

Ejecutar: python -m pytest tests.py -v
"""

import pytest
import uuid
import json
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# Importar módulos del sistema
from database import DatabaseConnection, ProyectosDB, ExamenesDB, EtiquetasDB
from project_manager import ProjectManager
from search_engine import BuscadorProyectos, BuscadorExamenes, Estadisticas
from import_export import ImportadorExportador, BackupManager


class TestDatabase:
    """Tests para la capa de base de datos."""
    
    @pytest.fixture
    def db_temp(self):
        """Crea una BD temporal para las pruebas."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseConnection(db_path)
        yield db
        # Limpiar
        shutil.rmtree(temp_dir)
    
    def test_crear_proyecto(self, db_temp):
        """Test: crear un proyecto en la BD."""
        db_crud = ProyectosDB(db_temp)
        
        exito = db_crud.crear(
            proyecto_id=str(uuid.uuid4()),
            titulo="Test Proyecto",
            rol="docente",
            perfil_edad="adulto",
            duracion_segundos=3600,
            ruta_carpeta="/test/path"
        )
        
        assert exito is True
    
    def test_obtener_proyecto(self, db_temp):
        """Test: obtener un proyecto de la BD."""
        db_crud = ProyectosDB(db_temp)
        proyecto_id = str(uuid.uuid4())
        
        # Crear
        db_crud.crear(
            proyecto_id=proyecto_id,
            titulo="Test Proyecto",
            rol="alumno",
            perfil_edad="adolescente",
            duracion_segundos=1800,
            ruta_carpeta="/test/path"
        )
        
        # Obtener
        proyecto = db_crud.obtener(proyecto_id)
        
        assert proyecto is not None
        assert proyecto['titulo'] == "Test Proyecto"
        assert proyecto['rol'] == "alumno"
    
    def test_actualizar_proyecto(self, db_temp):
        """Test: actualizar un proyecto."""
        db_crud = ProyectosDB(db_temp)
        proyecto_id = str(uuid.uuid4())
        
        # Crear
        db_crud.crear(
            proyecto_id=proyecto_id,
            titulo="Original",
            rol="docente",
            perfil_edad="adulto",
            duracion_segundos=3600,
            ruta_carpeta="/test"
        )
        
        # Actualizar
        exito = db_crud.actualizar(
            proyecto_id,
            titulo="Actualizado",
            duracion_segundos=5400
        )
        
        assert exito is True
        
        # Verificar
        proyecto = db_crud.obtener(proyecto_id)
        assert proyecto['titulo'] == "Actualizado"
        assert proyecto['duracion_segundos'] == 5400
    
    def test_eliminar_proyecto(self, db_temp):
        """Test: eliminar un proyecto."""
        db_crud = ProyectosDB(db_temp)
        proyecto_id = str(uuid.uuid4())
        
        # Crear
        db_crud.crear(
            proyecto_id=proyecto_id,
            titulo="A Eliminar",
            rol="docente",
            perfil_edad="adulto",
            duracion_segundos=3600,
            ruta_carpeta="/test"
        )
        
        # Eliminar
        exito = db_crud.eliminar(proyecto_id)
        assert exito is True
        
        # Verificar que no existe
        proyecto = db_crud.obtener(proyecto_id)
        assert proyecto is None
    
    def test_crear_examen(self, db_temp):
        """Test: crear un examen."""
        db_crud_p = ProyectosDB(db_temp)
        db_crud_e = ExamenesDB(db_temp)
        proyecto_id = str(uuid.uuid4())
        examen_id = str(uuid.uuid4())
        
        # Crear proyecto primero
        db_crud_p.crear(
            proyecto_id=proyecto_id,
            titulo="Test",
            rol="docente",
            perfil_edad="adulto",
            duracion_segundos=3600,
            ruta_carpeta="/test"
        )
        
        # Crear examen
        exito = db_crud_e.crear(
            examen_id=examen_id,
            proyecto_id=proyecto_id,
            alumno_nombre="Juan Pérez",
            nota=8.5,
            preguntas_acertadas=17,
            preguntas_totales=20
        )
        
        assert exito is True
    
    def test_crear_etiqueta(self, db_temp):
        """Test: crear una etiqueta."""
        db_crud = EtiquetasDB(db_temp)
        
        id_etiqueta = db_crud.crear("Programación")
        
        assert id_etiqueta > 0


class TestProjectManager:
    """Tests para el gestor de proyectos."""
    
    @pytest.fixture
    def temp_env(self):
        """Crea un entorno temporal."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "database" / "test.db"
        
        db = DatabaseConnection(db_path)
        pm = ProjectManager(temp_dir)
        db_crud = ProyectosDB(db)
        
        yield {
            "db": db,
            "pm": pm,
            "db_crud": db_crud,
            "temp_dir": temp_dir
        }
        
        # Limpiar
        shutil.rmtree(temp_dir)
    
    def test_crear_proyecto(self, temp_env):
        """Test: crear un proyecto completo."""
        datos = {
            "titulo": "Prueba de Proyecto",
            "rol": "docente",
            "perfil_edad": "adulto",
            "duracion_segundos": 3600,
            "etiquetas": ["test", "prueba"]
        }
        
        proyecto_id = temp_env["pm"].crear_proyecto(datos, temp_env["db_crud"])
        
        assert proyecto_id is not None
        
        # Verificar que la carpeta existe
        project_folder = temp_env["pm"].projects_path / proyecto_id
        assert project_folder.exists()
        
        # Verificar que los JSONs existen
        assert (project_folder / "metadata.json").exists()
        assert (project_folder / "transcripcion_completa.json").exists()
        assert (project_folder / "resumen.json").exists()
        assert (project_folder / "preguntas.json").exists()
        assert (project_folder / "examen_historial.json").exists()
    
    def test_obtener_proyecto(self, temp_env):
        """Test: obtener un proyecto."""
        # Crear primero
        datos = {
            "titulo": "Proyecto Test",
            "rol": "alumno",
            "perfil_edad": "adolescente",
            "etiquetas": ["test"]
        }
        
        proyecto_id = temp_env["pm"].crear_proyecto(datos, temp_env["db_crud"])
        
        # Obtener
        proyecto = temp_env["pm"].obtener_proyecto(proyecto_id)
        
        assert proyecto is not None
        assert proyecto["metadata"]["titulo"] == "Proyecto Test"
    
    def test_validar_integridad(self, temp_env):
        """Test: validar integridad de un proyecto."""
        datos = {
            "titulo": "Test",
            "rol": "docente",
            "perfil_edad": "adulto"
        }
        
        proyecto_id = temp_env["pm"].crear_proyecto(datos, temp_env["db_crud"])
        
        # Validar
        es_valido = temp_env["pm"].validar_integridad_proyecto(proyecto_id)
        
        assert es_valido is True
    
    def test_eliminar_proyecto(self, temp_env):
        """Test: eliminar un proyecto."""
        datos = {
            "titulo": "A Eliminar",
            "rol": "docente",
            "perfil_edad": "adulto"
        }
        
        proyecto_id = temp_env["pm"].crear_proyecto(datos, temp_env["db_crud"])
        project_folder = temp_env["pm"].projects_path / proyecto_id
        
        assert project_folder.exists()
        
        # Eliminar
        exito = temp_env["pm"].eliminar_proyecto(proyecto_id, temp_env["db_crud"])
        
        assert exito is True
        assert not project_folder.exists()


class TestSearch:
    """Tests para el motor de búsqueda."""
    
    @pytest.fixture
    def env_con_datos(self):
        """Crea un entorno con datos de prueba."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "database" / "test.db"
        
        db = DatabaseConnection(db_path)
        pm = ProjectManager(temp_dir)
        db_crud = ProyectosDB(db)
        
        # Crear algunos proyectos
        for i in range(5):
            datos = {
                "titulo": f"Proyecto {i}",
                "rol": "docente" if i % 2 == 0 else "alumno",
                "perfil_edad": "adulto",
                "etiquetas": ["general"]
            }
            pm.crear_proyecto(datos, db_crud)
        
        buscador = BuscadorProyectos(db, pm)
        
        yield {
            "db": db,
            "buscador": buscador,
            "temp_dir": temp_dir
        }
        
        shutil.rmtree(temp_dir)
    
    def test_buscar_por_titulo(self, env_con_datos):
        """Test: buscar por título."""
        resultados = env_con_datos["buscador"].buscar_por_titulo("Proyecto 1")
        
        assert len(resultados) > 0
    
    def test_buscar_por_rol(self, env_con_datos):
        """Test: buscar por rol."""
        resultados = env_con_datos["buscador"].buscar_por_rol("docente")
        
        assert len(resultados) > 0
        for proyecto in resultados:
            assert proyecto['rol'] == "docente"


class TestImportExport:
    """Tests para importación/exportación."""
    
    @pytest.fixture
    def env_export(self):
        """Crea un entorno para export/import."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "database" / "test.db"
        
        db = DatabaseConnection(db_path)
        pm = ProjectManager(temp_dir)
        db_crud = ProyectosDB(db)
        importador = ImportadorExportador(pm, db_crud)
        
        yield {
            "db": db,
            "pm": pm,
            "db_crud": db_crud,
            "importador": importador,
            "temp_dir": temp_dir
        }
        
        shutil.rmtree(temp_dir)
    
    def test_exportar_proyecto(self, env_export):
        """Test: exportar un proyecto como ZIP."""
        # Crear proyecto
        datos = {
            "titulo": "A Exportar",
            "rol": "docente",
            "perfil_edad": "adulto"
        }
        
        proyecto_id = env_export["pm"].crear_proyecto(datos, env_export["db_crud"])
        
        # Exportar
        zip_path = env_export["importador"].exportar_proyecto_zip(proyecto_id)
        
        assert zip_path is not None
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"


class TestBackup:
    """Tests para backup y restauración."""
    
    @pytest.fixture
    def env_backup(self):
        """Crea un entorno para backup."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "database" / "test.db"
        
        db = DatabaseConnection(db_path)
        backup_manager = BackupManager(db_path)
        
        yield {
            "db": db,
            "backup_manager": backup_manager,
            "temp_dir": temp_dir,
            "db_path": db_path
        }
        
        shutil.rmtree(temp_dir)
    
    def test_crear_backup(self, env_backup):
        """Test: crear un backup."""
        backup_path = env_backup["backup_manager"].crear_backup("test_backup")
        
        assert backup_path is not None
        assert backup_path.exists()
    
    def test_listar_backups(self, env_backup):
        """Test: listar backups."""
        # Crear algunos backups
        env_backup["backup_manager"].crear_backup("backup1")
        env_backup["backup_manager"].crear_backup("backup2")
        
        backups = env_backup["backup_manager"].listar_backups()
        
        assert len(backups) >= 2


# ============================================================================
# SUITE DE INTEGRACIÓN
# ============================================================================

class TestIntegracion:
    """Tests de integración del flujo completo."""
    
    def test_flujo_docente_completo(self):
        """Test: flujo completo de un docente."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Inicializar sistema
            db = DatabaseConnection(Path(temp_dir) / "database" / "test.db")
            pm = ProjectManager(temp_dir)
            db_crud = ProyectosDB(db)
            etiquetas_crud = EtiquetasDB(db)
            buscador = BuscadorProyectos(db, pm)
            
            # 1. Crear proyecto
            datos = {
                "titulo": "Programación Python",
                "descripcion": "Curso completo",
                "rol": "docente",
                "perfil_edad": "adulto",
                "duracion_segundos": 7200,
                "etiquetas": ["programación", "python"]
            }
            
            proyecto_id = pm.crear_proyecto(datos, db_crud)
            assert proyecto_id is not None
            
            # 2. Agregar transcripción
            transcripcion = [
                {"timestamp": 0.0, "texto": "Hola", "orador": "profesor"},
                {"timestamp": 60.0, "texto": "Hoy aprenderemos Python", "orador": "profesor"}
            ]
            
            exito = pm.actualizar_transcripcion(proyecto_id, transcripcion)
            assert exito is True
            
            # 3. Agregar resumen
            resumen = {
                "version_nino": "Python es un lenguaje fácil",
                "version_adolescente": "Python es un lenguaje de programación",
                "version_adulto": "Python es un lenguaje interpretado de alto nivel",
                "palabras_clave": ["lenguaje", "interpretado", "variables"]
            }
            
            exito = pm.actualizar_resumen(proyecto_id, resumen)
            assert exito is True
            
            # 4. Agregar preguntas
            preguntas = [
                {
                    "id": 1,
                    "tipo": "verdadero_falso",
                    "texto": "Python es compilado",
                    "respuesta_correcta": False
                }
            ]
            
            exito = pm.actualizar_preguntas(proyecto_id, preguntas)
            assert exito is True
            
            # 5. Buscar proyecto
            resultados = buscador.buscar_por_titulo("Programación Python")
            assert len(resultados) > 0
            
            # 6. Verificar proyecto
            proyecto = pm.obtener_proyecto(proyecto_id)
            assert proyecto["metadata"]["titulo"] == "Programación Python"
            assert len(proyecto["transcripcion"]) == 2
            
            print("✓ Flujo de docente completado exitosamente")
            
        finally:
            shutil.rmtree(temp_dir)
    
    def test_flujo_alumno_con_examen(self):
        """Test: flujo de alumno tomando examen."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Inicializar
            db = DatabaseConnection(Path(temp_dir) / "database" / "test.db")
            pm = ProjectManager(temp_dir)
            db_crud_p = ProyectosDB(db)
            db_crud_e = ExamenesDB(db)
            
            # 1. Crear proyecto de alumno
            datos = {
                "titulo": "Mi clase de matemáticas",
                "rol": "alumno",
                "perfil_edad": "adolescente"
            }
            
            proyecto_id = pm.crear_proyecto(datos, db_crud_p)
            assert proyecto_id is not None
            
            # 2. Agregar preguntas
            preguntas = [
                {"id": 1, "tipo": "verdadero_falso", "texto": "2+2=4", "respuesta_correcta": True},
                {"id": 2, "tipo": "opcion_multiple", "texto": "5+3=?", 
                 "opciones": ["8", "10", "6"], "respuesta_correcta": "8"}
            ]
            
            pm.actualizar_preguntas(proyecto_id, preguntas)
            
            # 3. Realizar examen
            examen_id = str(uuid.uuid4())
            exito = db_crud_e.crear(
                examen_id=examen_id,
                proyecto_id=proyecto_id,
                alumno_nombre="María García",
                nota=9.5,
                preguntas_acertadas=2,
                preguntas_totales=2,
                tiempo_segundos=600
            )
            
            assert exito is True
            
            # 4. Guardar detalles del examen
            examen_data = {
                "id": examen_id,
                "alumno": "María García",
                "respuestas": [
                    {"pregunta_id": 1, "respuesta": True, "correcta": True},
                    {"pregunta_id": 2, "respuesta": "8", "correcta": True}
                ],
                "nota": 9.5,
                "tiempo_segundos": 600
            }
            
            exito = pm.guardar_examen(proyecto_id, examen_data)
            assert exito is True
            
            print("✓ Flujo de alumno completado exitosamente")
            
        finally:
            shutil.rmtree(temp_dir)


# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

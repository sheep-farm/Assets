#!/usr/bin/env python3
"""
dependency_manager.py - Gerenciador de dependências com wheels

Permite ao usuário adicionar/remover wheels de um projeto .assets
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Set, Optional
from .zip_project import AssetsProject


class DependencyManager:
    """Gerencia dependências de um projeto .assets"""

    def __init__(self, project_path: str):
        """
        Args:
            project_path: Caminho do arquivo .assets
        """
        self.project = AssetsProject(project_path)

    def scan_imports(self, graph_data: dict) -> Set[str]:
        """
        Escaneia código dos nós para detectar imports.

        Args:
            graph_data: Dados do grafo .assets

        Returns:
            Set de nomes de pacotes importados
        """
        imports = set()

        # Mapear import name → package name
        import_map = {
            'pd': 'pandas',
            'np': 'numpy',
            'plt': 'matplotlib',
            'sns': 'seaborn',
            'sm': 'statsmodels',
            'scipy': 'scipy',
            'sklearn': 'scikit-learn',
            'cv2': 'opencv-python',
            'PIL': 'Pillow',
            'requests': 'requests',
            'bs4': 'beautifulsoup4',
            'fredapi': 'fredapi',
            'yf': 'yfinance',
            'yfinance': 'yfinance',
        }

        # Escanear código de todos os nós
        for node in graph_data.get("nodes", []):
            code = node.get("code", "")

            # Detectar imports
            for line in code.split('\n'):
                line = line.strip()

                # import xxx
                if line.startswith("import "):
                    parts = line.split()
                    if len(parts) >= 2:
                        module = parts[1].split('.')[0].split(',')[0]
                        imports.add(module)

                # from xxx import yyy
                elif line.startswith("from "):
                    parts = line.split()
                    if len(parts) >= 2:
                        module = parts[1].split('.')[0]
                        imports.add(module)

        # Mapear para nomes de pacotes
        packages = set()
        for imp in imports:
            package = import_map.get(imp, imp)

            # Ignorar built-ins
            if package not in ['os', 'sys', 'json', 'math', 'time', 'datetime',
                              'pathlib', 'itertools', 'functools', 'collections',
                              'random', 're', 'subprocess', 'threading', 'multiprocessing',
                              'io', 'pickle', 'csv', 'sqlite3', 'urllib', 'http',
                              'email', 'html', 'xml', 'logging', 'unittest', 'argparse']:
                packages.add(package)

        return packages

    def get_missing_packages(self, graph_data: dict) -> Set[str]:
        """
        Retorna pacotes que faltam (detectados no código mas não disponíveis)

        Args:
            graph_data: Dados do grafo

        Returns:
            set: Pacotes faltando
        """
        required = self.scan_imports(graph_data)

        if not required:
            return set()

        # Verificar o que já está instalado (built-in + wheels)
        installed = set()
        for package in required:
            try:
                # Normalizar nome (- → _)
                module_name = package.replace('-', '_')
                __import__(module_name)
                installed.add(package)
            except ImportError:
                pass

        return required - installed

    def download_wheels(self, package_names: List[str], dest_dir: Path, blacklist: Optional[List[str]] = None) -> List[Path]:
        """
        Baixa wheels para os pacotes especificados

        Args:
            package_names: Lista de nomes de pacotes
            dest_dir: Diretório de destino
            blacklist: Lista de pacotes para NÃO baixar (opcional)

        Returns:
            list: Lista de caminhos de wheels baixados
        """
        if not package_names:
            return []

        # Filtrar pacotes da blacklist (se fornecida)
        if blacklist:
            filtered_packages = [pkg for pkg in package_names if pkg not in blacklist]

            if len(filtered_packages) < len(package_names):
                blacklisted = set(package_names) - set(filtered_packages)
                print(f"⚠️  Pacotes bloqueados pelo projeto: {', '.join(blacklisted)}")
        else:
            filtered_packages = package_names

        if not filtered_packages:
            return []

        print(f"📦 Baixando wheels para: {', '.join(filtered_packages)}")

        try:
            # Tentar usar pip3 diretamente se sys.executable não tiver pip
            import shutil
            pip_cmd = shutil.which('pip3') or shutil.which('pip')

            if not pip_cmd:
                # Tentar usando python -m pip
                try:
                    cmd = [
                        sys.executable, '-m', 'pip', 'download',
                        '--dest', str(dest_dir),
                        '--only-binary', ':all:',
                        '--platform', 'manylinux2014_x86_64',
                        '--python-version', '3.12',
                        *filtered_packages
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f"❌ pip não disponível no sistema")
                    print(f"\n{'='*60}")
                    print(f"⚠️  INSTALAÇÃO MANUAL DE WHEELS NECESSÁRIA")
                    print(f"{'='*60}")
                    print(f"Para adicionar dependências, baixe os wheels manualmente e use:")
                    print(f"\n  python3 -m src add-wheels {self.project.project_path} <wheels_dir>/")
                    print(f"\nOu instale pip:")
                    print(f"  sudo apt install python3-pip")
                    print(f"{'='*60}\n")
                    return []
            else:
                # Usar pip3 diretamente
                cmd = [
                    pip_cmd, 'download',
                    '--dest', str(dest_dir),
                    '--only-binary', ':all:',
                    '--platform', 'manylinux2014_x86_64',
                    '--python-version', '3.12',
                    *filtered_packages
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    print(f"❌ Erro ao baixar wheels:")
                    print(result.stderr)
                    return []

            # Coletar wheels baixados
            wheel_files = list(dest_dir.glob("*.whl"))
            print(f"✓ {len(wheel_files)} wheel(s) baixado(s) (incluindo dependências)")

            return wheel_files

        except subprocess.TimeoutExpired:
            print(f"❌ Timeout ao baixar wheels (>5min)")
            return []
        except Exception as e:
            print(f"❌ Erro ao baixar wheels: {e}")
            import traceback
            traceback.print_exc()
            return []

    def add_packages(self, package_names: List[str]) -> bool:
        """
        Adiciona pacotes ao projeto (baixa wheels e salva no .assets)

        Args:
            package_names: Lista de nomes de pacotes

        Returns:
            bool: True se adicionou com sucesso
        """
        if not package_names:
            print("ℹ️  Nenhum pacote para adicionar")
            return True

        print(f"\n{'='*60}")
        print(f"📦 ADICIONANDO DEPENDÊNCIAS AO PROJETO")
        print(f"{'='*60}")
        print(f"Pacotes: {', '.join(package_names)}")
        print()

        try:
            # Carregar grafo existente
            graph_data = self.project.load_graph()
            if graph_data is None:
                print(f"❌ Não foi possível carregar projeto")
                return False

            # Obter blacklist do metadata (se existir)
            blacklist = graph_data.get('project_metadata', {}).get('blacklist', [])
            if blacklist:
                print(f"🚫 Blacklist do projeto: {', '.join(blacklist)}")

            # Baixar wheels em diretório temporário
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                wheel_files = self.download_wheels(package_names, temp_path, blacklist)

                if not wheel_files:
                    print(f"⚠️  Nenhum wheel baixado")
                    return False

                # Salvar projeto com novos wheels
                success = self.project.save_graph(graph_data, wheel_files)

                if success:
                    print()
                    print(f"{'='*60}")
                    print(f"✓ DEPENDÊNCIAS ADICIONADAS COM SUCESSO")
                    print(f"{'='*60}")
                    print(f"Wheels incluídos no projeto:")
                    for whl in wheel_files:
                        print(f"  • {whl.name}")
                    print()

                return success

        except Exception as e:
            print(f"❌ Erro ao adicionar pacotes: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_installed_wheels(self) -> List[str]:
        """
        Lista wheels instalados no projeto

        Returns:
            list: Lista de nomes de wheels
        """
        return self.project.list_wheels()

    def check_and_prompt_install(self, graph_data: dict) -> Optional[List[str]]:
        """
        Verifica dependências faltando e retorna lista de pacotes necessários

        Args:
            graph_data: Dados do grafo

        Returns:
            list: Lista de pacotes faltando ou None se tudo OK
        """
        missing = self.get_missing_packages(graph_data)

        if not missing:
            print("✓ Todas as dependências estão disponíveis")
            return None

        print()
        print(f"{'='*60}")
        print(f"⚠️  DEPENDÊNCIAS FALTANDO")
        print(f"{'='*60}")
        print(f"Pacotes necessários: {', '.join(sorted(missing))}")
        print()
        print(f"Para adicionar as dependências ao projeto, use:")
        print(f"  Menu > Manage Dependencies")
        print()
        print(f"Ou via linha de comando:")
        print(f"  python -m src.cli add-deps {self.project.project_path} {' '.join(sorted(missing))}")
        print(f"{'='*60}")
        print()

        return sorted(missing)


def add_dependencies_to_project(project_path: str, package_names: List[str]) -> bool:
    """
    Helper function para adicionar dependências a um projeto

    Args:
        project_path: Caminho do arquivo .assets
        package_names: Lista de nomes de pacotes

    Returns:
        bool: True se adicionou com sucesso
    """
    manager = DependencyManager(project_path)
    return manager.add_packages(package_names)


def check_project_dependencies(project_path: str, graph_data: dict) -> Optional[List[str]]:
    """
    Helper function para verificar dependências de um projeto

    Args:
        project_path: Caminho do arquivo .assets
        graph_data: Dados do grafo

    Returns:
        list: Lista de pacotes faltando ou None se tudo OK
    """
    manager = DependencyManager(project_path)
    return manager.check_and_prompt_install(graph_data)

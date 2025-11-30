#!/usr/bin/env python3
"""
project_dependencies.py - Gerenciador de dependências por projeto
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Set


class ProjectDependencyManager:
    """Gerencia dependências Python por projeto .assets"""

    def __init__(self, project_path: Path, graph_data: dict = None):
        """
        Args:
            project_path: Caminho do arquivo .assets
            graph_data: Dados do grafo (para ler/salvar metadata)
        """
        self.project_path = Path(project_path)
        self.project_dir = self.project_path.parent
        self.graph_data = graph_data or {}

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
            'requests': 'requests',
            'fredapi': 'fredapi',
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
                    module = line.split()[1].split('.')[0]
                    imports.add(module)

                # from xxx import yyy
                elif line.startswith("from "):
                    module = line.split()[1].split('.')[0]
                    imports.add(module)

        # Mapear para nomes de pacotes
        packages = set()
        for imp in imports:
            package = import_map.get(imp, imp)

            # Ignorar built-ins
            if package not in ['os', 'sys', 'json', 'math', 'time', 'datetime',
                              'pathlib', 'itertools', 'functools', 'collections']:
                packages.add(package)

        return packages

    def save_requirements(self, packages: Set[str]):
        """Salva requirements nos metadados do .assets"""
        if "project_metadata" not in self.graph_data:
            self.graph_data["project_metadata"] = {}

        self.graph_data["project_metadata"]["requirements"] = sorted(list(packages))
        print(f"✓ Requirements salvos nos metadados do projeto: {sorted(packages)}")

    def load_requirements(self) -> Set[str]:
        """Carrega requirements dos metadados do .assets"""
        metadata = self.graph_data.get("project_metadata", {})
        requirements = metadata.get("requirements", [])
        return set(requirements)

    def install_packages(self, packages: Set[str], callback=None) -> bool:
        """
        Instala pacotes usando pip (dentro do Flatpak) em background.

        Args:
            packages: Set de nomes de pacotes
            callback: Função chamada com (success: bool) quando terminar

        Returns:
            bool: True se iniciou instalação
        """
        if not packages:
            print("✓ Nenhum pacote adicional necessário")
            if callback:
                callback(True)
            return True

        print(f"📦 Instalando pacotes em background: {', '.join(sorted(packages))}")
        print(f"   Isso pode levar alguns minutos...")

        def install_worker():
            """Worker thread para instalar pacotes"""
            try:
                # Instalar com pip
                cmd = [
                    sys.executable, '-m', 'pip', 'install',
                    '--user',  # Instalar em ~/.local
                    '--no-cache-dir',
                    '--quiet',  # Menos output
                    *packages
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

                if result.returncode == 0:
                    print(f"✓ Pacotes instalados com sucesso: {', '.join(sorted(packages))}")
                    if callback:
                        callback(True)
                    return True
                else:
                    print(f"❌ Erro ao instalar pacotes:")
                    print(result.stderr)
                    if callback:
                        callback(False)
                    return False

            except subprocess.TimeoutExpired:
                print("❌ Timeout ao instalar pacotes (>10min)")
                if callback:
                    callback(False)
                return False
            except Exception as e:
                print(f"❌ Erro ao instalar: {e}")
                import traceback
                traceback.print_exc()
                if callback:
                    callback(False)
                return False

        # Executar em thread separada para não bloquear UI
        import threading
        thread = threading.Thread(target=install_worker, daemon=True)
        thread.start()

        return True

    def check_and_install(self, graph_data: dict, auto_install: bool = True) -> bool:
        """
        Verifica dependências e instala se necessário.

        Args:
            graph_data: Dados do grafo
            auto_install: Se True, instala automaticamente

        Returns:
            bool: True se todas as dependências estão disponíveis
        """
        # Detectar pacotes usados
        required = self.scan_imports(graph_data)

        if not required:
            print("✓ Nenhuma dependência adicional detectada")
            return True

        # Verificar o que já está instalado
        installed = set()
        for package in required:
            try:
                __import__(package)
                installed.add(package)
            except ImportError:
                pass

        missing = required - installed

        if not missing:
            print(f"✓ Todas as dependências já instaladas: {', '.join(sorted(required))}")
            return True

        print(f"⚠️  Dependências faltando: {', '.join(sorted(missing))}")

        # Salvar requirements nos metadados
        self.save_requirements(required)

        # Mostrar comando para instalação manual
        print(f"\n{'='*60}")
        print(f"⚠️  DEPENDÊNCIAS FALTANDO")
        print(f"{'='*60}")
        print(f"Pacotes necessários: {', '.join(sorted(missing))}")
        print(f"\nPara instalar, execute no terminal:")
        print(f"\n  flatpak run --command=sh com.github.sheep.farm.assets -c \\")
        print(f"    'pip3 install --user {' '.join(sorted(missing))}'")
        print(f"\nOu se estiver executando localmente:")
        print(f"\n  pip3 install --user {' '.join(sorted(missing))}")
        print(f"{'='*60}\n")

        return False


def check_project_dependencies(project_path: str, graph_data: dict, show_toast=None) -> dict:
    """
    Função helper para verificar dependências de um projeto.

    Args:
        project_path: Caminho do arquivo .assets
        graph_data: Dados do grafo desserializados
        show_toast: Função callback para mostrar notificação (opcional)

    Returns:
        dict: graph_data atualizado com metadados de requirements
    """
    manager = ProjectDependencyManager(project_path, graph_data)

    # Callback quando instalação terminar
    def on_install_complete(success):
        if success and show_toast:
            show_toast("✓ Dependências instaladas com sucesso!")
        elif not success and show_toast:
            show_toast("❌ Erro ao instalar dependências - veja o terminal")

    manager.check_and_install(graph_data, auto_install=True)

    # Retornar graph_data atualizado
    return graph_data

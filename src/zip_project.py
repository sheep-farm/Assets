#!/usr/bin/env python3
"""
zip_project.py - Gerenciador de projetos .assets como arquivos ZIP

Estrutura do arquivo .assets (ZIP):
  graph.json          - Dados do grafo (nós, conexões, metadados)
  wheels/             - Pasta com arquivos .whl das dependências
    package-1.0-py3-none-any.whl
    another-2.5-py3-none-any.whl
"""

import json
import zipfile
import tempfile
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, List, Set
import subprocess


class AssetsProject:
    """Gerencia projeto .assets como arquivo ZIP com wheels isolados"""

    def __init__(self, project_path: str):
        """
        Args:
            project_path: Caminho do arquivo .assets
        """
        self.project_path = Path(project_path)
        self.project_name = self.project_path.stem

        # Diretório temporário para extrair wheels (isolado por projeto)
        self.temp_dir = None
        self.wheels_dir = None

    def __enter__(self):
        """Context manager - extrai wheels ao entrar"""
        self.setup_isolated_environment()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - limpa ambiente ao sair"""
        self.cleanup_isolated_environment()

    def setup_isolated_environment(self):
        """Cria ambiente isolado e carrega wheels no sys.path"""
        import zipfile as zf_module

        # Criar diretório temporário único para este projeto
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"assets_{self.project_name}_"))
        self.wheels_dir = self.temp_dir / "wheels"
        self.wheels_dir.mkdir(parents=True, exist_ok=True)

        print(f"🔧 Configurando ambiente isolado: {self.temp_dir}")
        print(f"   Arquivo: {self.project_path}")
        print(f"   Existe: {self.project_path.exists()}")
        print(f"   É ZIP: {zf_module.is_zipfile(self.project_path) if self.project_path.exists() else False}")

        # Extrair wheels do ZIP
        if self.project_path.exists() and zf_module.is_zipfile(self.project_path):
            with zf_module.ZipFile(self.project_path, 'r') as zf:
                all_files = zf.namelist()
                print(f"   Arquivos no ZIP: {len(all_files)}")
                wheels_in_zip = [f for f in all_files if f.startswith('wheels/') and f.endswith('.whl')]
                print(f"   Wheels no ZIP: {len(wheels_in_zip)}")

                # Extrair apenas a pasta wheels/
                for member in zf.namelist():
                    if member.startswith('wheels/') and member.endswith('.whl'):
                        wheel_name = Path(member).name
                        wheel_path = self.wheels_dir / wheel_name

                        with zf.open(member) as source:
                            with open(wheel_path, 'wb') as target:
                                shutil.copyfileobj(source, target)

                        print(f"  📦 Extraído: {wheel_name}")

        # Desempacotar wheels (necessário para extensões C compiladas)
        wheel_files = list(self.wheels_dir.glob("*.whl"))

        if wheel_files:
            print(f"📚 Desempacotando {len(wheel_files)} wheel(s)...")

            # Criar diretório para pacotes desempacotados
            site_packages = self.temp_dir / "site-packages"
            site_packages.mkdir(exist_ok=True)

            for wheel_path in wheel_files:
                # Desempacotar wheel
                with zf_module.ZipFile(wheel_path, 'r') as whl:
                    whl.extractall(site_packages)
                print(f"  ✓ {wheel_path.name}")

            # Adicionar site-packages ao sys.path (no INÍCIO)
            site_packages_str = str(site_packages.resolve())
            if site_packages_str not in sys.path:
                sys.path.insert(0, site_packages_str)
                print(f"✓ Site-packages adicionado ao sys.path: {site_packages_str}")
        else:
            print("ℹ️  Nenhum wheel encontrado no projeto")

    def cleanup_isolated_environment(self):
        """Remove ambiente isolado e limpa sys.path"""
        if self.temp_dir and self.temp_dir.exists():
            # Remover site-packages do sys.path
            site_packages = self.temp_dir / "site-packages"
            site_packages_str = str(site_packages.resolve())
            if site_packages_str in sys.path:
                sys.path.remove(site_packages_str)

            # Remover diretório temporário
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"🧹 Ambiente isolado limpo: {self.temp_dir}")

    def load_graph(self) -> Optional[Dict]:
        """
        Carrega graph.json do arquivo .assets

        Returns:
            dict: Dados do grafo ou None se erro
        """
        try:
            if not self.project_path.exists():
                print(f"❌ Arquivo não encontrado: {self.project_path}")
                return None

            if not zipfile.is_zipfile(self.project_path):
                print(f"❌ Arquivo não é um ZIP válido: {self.project_path}")
                return None

            with zipfile.ZipFile(self.project_path, 'r') as zf:
                # Ler graph.json
                if 'graph.json' not in zf.namelist():
                    print(f"❌ graph.json não encontrado no arquivo .assets")
                    return None

                with zf.open('graph.json') as f:
                    graph_data = json.load(f)

            print(f"✓ Grafo carregado: {self.project_path}")
            print(f"  - {len(graph_data.get('nodes', []))} nós")
            print(f"  - {len(graph_data.get('connections', []))} conexões")

            return graph_data

        except Exception as e:
            print(f"❌ Erro ao carregar projeto: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_graph(self, graph_data: Dict, wheels_to_include: Optional[List[Path]] = None) -> bool:
        """
        Salva graph.json e wheels no arquivo .assets

        Args:
            graph_data: Dados do grafo
            wheels_to_include: Lista de caminhos de wheels para incluir

        Returns:
            bool: True se salvou com sucesso
        """
        try:
            print(f"💾 Salvando projeto:")
            print(f"   Caminho: {self.project_path}")
            print(f"   Wheels a incluir: {len(wheels_to_include) if wheels_to_include else 0}")

            # Criar arquivo ZIP
            with zipfile.ZipFile(self.project_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Adicionar graph.json
                graph_json = json.dumps(graph_data, indent=2, ensure_ascii=False)
                zf.writestr('graph.json', graph_json)
                print(f"  ✓ graph.json adicionado")

                # Adicionar wheels
                if wheels_to_include:
                    for wheel_path in wheels_to_include:
                        if wheel_path.exists() and wheel_path.suffix == '.whl':
                            arcname = f"wheels/{wheel_path.name}"
                            zf.write(wheel_path, arcname)
                            print(f"  ✓ {wheel_path.name} adicionado")
                        else:
                            print(f"  ⚠️  Wheel não encontrado: {wheel_path}")

            # Verificar o que foi salvo
            with zipfile.ZipFile(self.project_path, 'r') as zf:
                all_files = zf.namelist()
                wheels_saved = [f for f in all_files if f.startswith('wheels/')]
                print(f"✓ Projeto salvo: {self.project_path}")
                print(f"   Total de arquivos no ZIP: {len(all_files)}")
                print(f"   Wheels salvos: {len(wheels_saved)}")

            return True

        except Exception as e:
            print(f"❌ Erro ao salvar projeto: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_wheels(self, package_names: List[str]) -> bool:
        """
        Baixa wheels e adiciona ao projeto .assets

        Args:
            package_names: Lista de nomes de pacotes (ex: ['pandas', 'numpy'])

        Returns:
            bool: True se adicionou com sucesso
        """
        try:
            if not package_names:
                print("ℹ️  Nenhum pacote para adicionar")
                return True

            print(f"📦 Baixando wheels: {', '.join(package_names)}")

            # Criar diretório temporário para download
            with tempfile.TemporaryDirectory() as download_dir:
                download_path = Path(download_dir)

                # Baixar wheels usando pip
                cmd = [
                    sys.executable, '-m', 'pip', 'download',
                    '--dest', str(download_path),
                    '--only-binary', ':all:',  # Apenas wheels
                    '--python-version', '3.11',  # Versão do Python no Flatpak
                    '--platform', 'manylinux2014_x86_64',  # Plataforma Linux
                    '--no-deps',  # Sem dependências (usuário deve adicionar manualmente)
                    *package_names
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    print(f"❌ Erro ao baixar wheels:")
                    print(result.stderr)
                    return False

                # Coletar wheels baixados
                wheel_files = list(download_path.glob("*.whl"))

                if not wheel_files:
                    print(f"⚠️  Nenhum wheel baixado")
                    return False

                print(f"✓ {len(wheel_files)} wheel(s) baixado(s)")

                # Carregar grafo existente
                graph_data = self.load_graph()
                if graph_data is None:
                    print(f"❌ Não foi possível carregar grafo existente")
                    return False

                # Salvar com novos wheels
                return self.save_graph(graph_data, wheel_files)

        except Exception as e:
            print(f"❌ Erro ao adicionar wheels: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_wheels(self) -> List[str]:
        """
        Lista wheels incluídos no projeto

        Returns:
            list: Lista de nomes de wheels
        """
        try:
            if not self.project_path.exists() or not zipfile.is_zipfile(self.project_path):
                return []

            with zipfile.ZipFile(self.project_path, 'r') as zf:
                wheels = [
                    Path(member).name
                    for member in zf.namelist()
                    if member.startswith('wheels/') and member.endswith('.whl')
                ]

            return sorted(wheels)

        except Exception:
            return []

    def get_installed_packages(self) -> Set[str]:
        """
        Retorna set de pacotes disponíveis no ambiente isolado

        Returns:
            set: Nomes de pacotes disponíveis
        """
        packages = set()

        # Verificar o que está disponível nos wheels
        if self.wheels_dir:
            for wheel_path in self.wheels_dir.glob("*.whl"):
                # Extrair nome do pacote do wheel
                # Formato: package_name-version-py3-none-any.whl
                package_name = wheel_path.name.split('-')[0].lower().replace('_', '-')
                packages.add(package_name)

        return packages


def create_new_project(project_path: str, graph_data: Dict) -> bool:
    """
    Cria novo projeto .assets

    Args:
        project_path: Caminho do arquivo .assets
        graph_data: Dados do grafo

    Returns:
        bool: True se criou com sucesso
    """
    project = AssetsProject(project_path)
    return project.save_graph(graph_data)


def migrate_old_project(old_json_path: str, new_assets_path: str) -> bool:
    """
    Migra projeto antigo (.assets JSON) para novo formato (.assets ZIP)

    Args:
        old_json_path: Caminho do arquivo JSON antigo
        new_assets_path: Caminho do novo arquivo .assets

    Returns:
        bool: True se migrou com sucesso
    """
    try:
        print(f"🔄 Migrando projeto: {old_json_path} → {new_assets_path}")

        # Carregar JSON antigo
        with open(old_json_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)

        # Criar novo projeto
        project = AssetsProject(new_assets_path)
        success = project.save_graph(graph_data)

        if success:
            print(f"✓ Projeto migrado com sucesso!")
            print(f"  Arquivo antigo: {old_json_path}")
            print(f"  Novo arquivo: {new_assets_path}")

        return success

    except Exception as e:
        print(f"❌ Erro ao migrar projeto: {e}")
        import traceback
        traceback.print_exc()
        return False

#!/usr/bin/env python3
"""
system_venv.py - Gerenciador de ambientes virtuais usando Python do sistema

Cria e gerencia venvs isolados por projeto em ~/.local/share/assets/venvs/
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, List


class SystemVenv:
    """Gerencia venv usando Python do sistema host"""

    VENV_BASE_DIR = Path.home() / ".local" / "share" / "assets" / "venvs"

    def __init__(self, project_name: str):
        """
        Args:
            project_name: Nome do projeto (usado como nome do venv)
        """
        self.project_name = project_name
        self.venv_path = self.VENV_BASE_DIR / project_name
        self.python_bin = self.venv_path / "bin" / "python"
        self.pip_bin = self.venv_path / "bin" / "pip"

        # Detectar se está rodando em Flatpak
        self.in_flatpak = Path("/.flatpak-info").exists()
        if self.in_flatpak:
            print("🐋 Detectado: Rodando dentro do Flatpak")
            print("   Comandos serão executados no host via flatpak-spawn")

    def _run_host_command(self, cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
        """
        Executa comando no host (com flatpak-spawn se necessário)

        Args:
            cmd: Comando a executar
            **kwargs: Argumentos para subprocess.run()

        Returns:
            CompletedProcess
        """
        if self.in_flatpak:
            # Prefixar com flatpak-spawn --host
            cmd = ["flatpak-spawn", "--host"] + cmd

        return subprocess.run(cmd, **kwargs)

    def exists(self) -> bool:
        """Verifica se o venv já existe"""
        return self.venv_path.exists() and self.python_bin.exists()

    def create(self) -> bool:
        """
        Cria um novo venv usando Python do sistema

        Returns:
            bool: True se criou com sucesso
        """
        try:
            # Criar diretório base se não existir
            self.VENV_BASE_DIR.mkdir(parents=True, exist_ok=True)

            print(f"\n{'='*60}")
            print(f"🐍 CRIANDO VENV COM PYTHON DO SISTEMA")
            print(f"{'='*60}")
            print(f"Projeto: {self.project_name}")
            print(f"Localização: {self.venv_path}")

            # Tentar encontrar python3 no sistema
            python_cmd = self._find_system_python()
            if not python_cmd:
                print(f"❌ Python não encontrado no sistema")
                print(f"\nInstale Python 3.8+ no sistema:")
                print(f"  sudo apt install python3 python3-venv")
                return False

            print(f"Python do sistema: {python_cmd}")

            # Criar venv com --copies para garantir que pip seja copiado
            print(f"📦 Criando venv...")
            result = self._run_host_command(
                [python_cmd, "-m", "venv", "--copies", str(self.venv_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print(f"❌ Erro ao criar venv:")
                print(result.stderr)
                return False

            # Verificar se pip existe
            if not self.pip_bin.exists():
                print(f"⚠️  pip não encontrado, instalando via ensurepip...")
                result = self._run_host_command(
                    [str(self.python_bin), "-m", "ensurepip", "--upgrade"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode != 0:
                    print(f"❌ Erro ao instalar pip:")
                    print(result.stderr)
                    return False

            # Atualizar pip
            print(f"📦 Atualizando pip...")
            result = self._run_host_command(
                [str(self.pip_bin), "install", "--upgrade", "pip"],
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                print(f"⚠️  Erro ao atualizar pip (não crítico)")
                print(result.stderr)

            print(f"✓ Venv criado com sucesso!")
            print(f"{'='*60}\n")
            return True

        except Exception as e:
            print(f"❌ Erro ao criar venv: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _find_system_python(self) -> Optional[str]:
        """
        Procura Python no sistema (fora do Flatpak)

        Returns:
            str: Caminho do python ou None
        """
        # Caminhos comuns de Python no host
        common_paths = [
            "/usr/bin/python3",
            "/usr/bin/python3.12",
            "/usr/bin/python3.11",
            "/usr/bin/python3.10",
            "/bin/python3",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        # Tentar via flatpak-spawn
        try:
            result = subprocess.run(
                ["flatpak-spawn", "--host", "which", "python3"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        return None

    def install_packages(self, packages: List[str]) -> bool:
        """
        Instala pacotes no venv

        Args:
            packages: Lista de pacotes (ex: ['pandas', 'numpy==1.24.0'])

        Returns:
            bool: True se instalou com sucesso
        """
        if not self.exists():
            print(f"❌ Venv não existe. Crie primeiro com create()")
            return False

        if not packages:
            print(f"ℹ️  Nenhum pacote para instalar")
            return True

        try:
            print(f"\n{'='*60}")
            print(f"📦 INSTALANDO PACOTES NO VENV")
            print(f"{'='*60}")
            print(f"Pacotes: {', '.join(packages)}")

            result = self._run_host_command(
                [str(self.pip_bin), "install", *packages],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                print(f"❌ Erro ao instalar pacotes:")
                print(result.stderr)
                return False

            print(f"✓ Pacotes instalados com sucesso!")
            print(f"{'='*60}\n")
            return True

        except subprocess.TimeoutExpired:
            print(f"❌ Timeout ao instalar pacotes (>5min)")
            return False
        except Exception as e:
            print(f"❌ Erro ao instalar pacotes: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_code(self, code: str, timeout: int = 30) -> tuple[bool, str, str]:
        """
        Executa código Python no venv

        Args:
            code: Código Python para executar
            timeout: Timeout em segundos

        Returns:
            tuple: (success, stdout, stderr)
        """
        if not self.exists():
            return False, "", "Venv não existe"

        try:
            # Escrever em arquivo temporário para evitar E2BIG (argumento muito longo)
            # IMPORTANTE: Usar diretório acessível pelo host (não /tmp do Flatpak)
            import tempfile
            import os

            # Usar diretório do venv (sempre acessível)
            temp_dir = self.venv_path / "tmp"
            temp_dir.mkdir(exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                dir=str(temp_dir)
            ) as f:
                f.write(code)
                temp_script = f.name

            try:
                # Executar script via python do venv
                result = self._run_host_command(
                    [str(self.python_bin), temp_script],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                success = result.returncode == 0
                return success, result.stdout, result.stderr

            finally:
                # Limpar arquivo temporário
                try:
                    os.unlink(temp_script)
                except:
                    pass

        except subprocess.TimeoutExpired:
            return False, "", f"Timeout ({timeout}s)"
        except Exception as e:
            return False, "", str(e)

    def list_packages(self) -> List[str]:
        """
        Lista pacotes instalados no venv

        Returns:
            list: Lista de pacotes no formato "nome==versão"
        """
        if not self.exists():
            return []

        try:
            result = self._run_host_command(
                [str(self.pip_bin), "freeze"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip().split('\n')
            return []

        except:
            return []

    def delete(self) -> bool:
        """
        Remove o venv completamente

        Returns:
            bool: True se removeu com sucesso
        """
        try:
            if self.venv_path.exists():
                import shutil
                shutil.rmtree(self.venv_path)
                print(f"✓ Venv removido: {self.venv_path}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erro ao remover venv: {e}")
            return False


def setup_project_venv(project_name: str, requirements: List[str]) -> Optional[SystemVenv]:
    """
    Configura venv para um projeto (cria se necessário e instala dependências)

    Args:
        project_name: Nome do projeto
        requirements: Lista de pacotes necessários

    Returns:
        SystemVenv: Instância do venv ou None se falhou
    """
    venv = SystemVenv(project_name)

    # Criar venv se não existir
    if not venv.exists():
        if not venv.create():
            return None

    # Instalar pacotes necessários
    if requirements:
        # Verificar quais pacotes já estão instalados
        installed = venv.list_packages()
        installed_names = {pkg.split('==')[0].lower() for pkg in installed}

        # Filtrar apenas pacotes que faltam
        missing = [
            pkg for pkg in requirements
            if pkg.split('==')[0].lower() not in installed_names
        ]

        if missing:
            print(f"📦 Pacotes faltando: {', '.join(missing)}")
            if not venv.install_packages(missing):
                return None
        else:
            print(f"✓ Todos os pacotes já estão instalados")

    return venv

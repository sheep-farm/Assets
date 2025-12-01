"""
project_tab.py - Encapsula um projeto (aba) completo

Gerencia ambiente isolado de dependências (wheels) por projeto
"""

from gi.repository import Gtk, Adw
from pathlib import Path

from .canvas import AssetsCanvas
from .output_panel import OutputPanel


class ProjectTab:
    """Representa uma aba de projeto com canvas, output e estado"""

    def __init__(self):
        # Estado do arquivo
        self.current_file = None
        self.is_modified = False

        # Ambiente isolado de dependências
        self.isolated_env = None  # Instância de AssetsProject (modo flatpak) ou SystemVenv (modo system)
        self.project_metadata = None  # Metadados do projeto
        self.python_mode = "flatpak"  # "flatpak" ou "system"
        self.environment_ready = False  # Se ambiente está pronto para execução

        # Container principal - box vertical com toolbar + paned
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_container.set_vexpand(True)
        self.main_container.set_hexpand(True)

        # Criar canvas
        self.canvas = AssetsCanvas()
        # Canvas precisa referenciar o projeto para saber o python_mode
        self.canvas.project_tab = self

        # Colocar canvas dentro de ScrolledWindow
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_child(self.canvas)

        # Criar output panel
        self.output_panel = OutputPanel()
        self.output_panel.set_vexpand(True)
        self.output_panel.set_hexpand(True)

        # Criar paned para canvas + output
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.main_paned.set_vexpand(True)
        self.main_paned.set_hexpand(True)
        self.main_paned.set_start_child(self.scrolled_window)
        self.main_paned.set_end_child(self.output_panel)
        self.main_paned.set_resize_start_child(True)
        self.main_paned.set_resize_end_child(False)
        self.main_paned.set_shrink_start_child(False)
        self.main_paned.set_shrink_end_child(False)
        self.main_paned.set_position(400)

        # Adicionar paned ao container
        self.main_container.append(self.main_paned)

    def get_widget(self):
        """Retorna o widget principal da aba"""
        return self.main_container

    def get_title(self):
        """Retorna o título para a aba"""
        if self.current_file:
            return Path(self.current_file).stem
        return "Untitled"

    def get_tooltip(self):
        """Retorna tooltip com caminho completo"""
        if self.current_file:
            return str(self.current_file)
        return "New file"

    def mark_modified(self, modified=True):
        """Marca o projeto como modificado"""
        self.is_modified = modified

    def needs_save(self):
        """Verifica se precisa salvar"""
        return self.is_modified and len(self.canvas.nodes) > 0

    def setup_isolated_environment(self, project_path: str, graph_data: dict = None, on_ready_callback=None):
        """
        Configura ambiente isolado de dependências para este projeto

        Args:
            project_path: Caminho do arquivo .assets
            graph_data: Dados do grafo (opcional, para ler python_mode)
            on_ready_callback: Callback chamado quando ambiente estiver pronto
        """
        # Marcar ambiente como não-pronto durante setup
        self.environment_ready = False

        # Limpar ambiente anterior se existir
        self.cleanup_isolated_environment()

        # Determinar modo Python
        if graph_data:
            metadata = graph_data.get('project_metadata', {})
            self.python_mode = metadata.get('python_mode', 'flatpak')
            self.project_metadata = metadata
        else:
            self.python_mode = 'flatpak'

        project_name = Path(project_path).stem

        if self.python_mode == 'system':
            # Modo System Python - usar venv do sistema
            from .system_venv import setup_project_venv
            import threading
            from gi.repository import GLib

            print(f"\n🐍 Modo: System Python (venv)")
            requirements = self.project_metadata.get('requirements', [])

            # Executar setup em thread para não travar a UI
            def setup_venv_background():
                venv = setup_project_venv(project_name, requirements)

                # Atualizar no main thread
                def update_env():
                    self.isolated_env = venv
                    self.environment_ready = True  # Marcar como pronto
                    if venv:
                        print(f"✓ Venv configurado para: {project_name}")
                    else:
                        print(f"❌ Falha ao configurar venv")

                    # Chamar callback se fornecido
                    if on_ready_callback:
                        on_ready_callback(bool(venv))

                    return False  # Remove from idle

                GLib.idle_add(update_env)

            thread = threading.Thread(target=setup_venv_background, daemon=True)
            thread.start()

        else:
            # Modo Flatpak - usar wheels dentro do .assets
            from .zip_project import AssetsProject

            print(f"\n📦 Modo: Flatpak (wheels isolados)")

            self.isolated_env = AssetsProject(project_path)
            self.isolated_env.setup_isolated_environment()
            self.environment_ready = True  # Flatpak é síncrono, já está pronto

            print(f"✓ Ambiente isolado configurado para: {project_name}")

            # Chamar callback (flatpak é síncrono, já está pronto)
            if on_ready_callback:
                on_ready_callback(True)

    def cleanup_isolated_environment(self):
        """Limpa ambiente isolado de dependências"""
        if self.isolated_env:
            if self.python_mode == 'flatpak':
                self.isolated_env.cleanup_isolated_environment()
            # System venv persiste (não precisa limpar)
            self.isolated_env = None
            print(f"✓ Ambiente limpo")

    def __del__(self):
        """Destrutor - garante limpeza do ambiente"""
        self.cleanup_isolated_environment()

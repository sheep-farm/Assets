# window.py
#
# Copyright 2025 Flavio de Vasconcellos Corrêa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gtk, Gio, Gdk
import cairo
from pathlib import Path

from .canvas import AssetsCanvas
from .output_panel import OutputPanel
from .project_tab import ProjectTab

@Gtk.Template(resource_path='/com/github/sheep/farm/assets/window.ui')
class AssetsWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'AssetsWindow'

    # Template widgets
    sidebar_toggle = Gtk.Template.Child()
    run_button = Gtk.Template.Child()
    # result_toggle = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    split_view = Gtk.Template.Child()
    toolbar_box = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    favorites_toggle = Gtk.Template.Child()
    import_button = Gtk.Template.Child()
    export_button = Gtk.Template.Child()
    node_list = Gtk.Template.Child()
    #main_paned = Gtk.Template.Child()
    canvas_box = Gtk.Template.Child()
    # result_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # IMPORTANTE: Criar ações PRIMEIRO, antes de renderizar UI
        self._create_actions()

        # Clipboard global para copiar entre projetos (lista de nós)
        self.clipboard_nodes = []
        self.clipboard_connections = []  # Conexões entre nós copiados

        # Estado para controle do painel de resultado
        self.result_panel_visible = True
        self.result_panel_height = 200

        # Estado de população
        self._is_populating = False

        # Rastrear quais categorias estão expandidas (True = expandida, False = contraída)
        self._expanded_categories = {}

        # Conectar signals do Toolbar
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.favorites_toggle.connect("toggled", self._on_favorites_toggled)
        self.import_button.connect("clicked", self._on_import_library)
        self.export_button.connect("clicked", self._on_export_library)

        # Conectar signals dos botões principais
        self.run_button.connect("clicked", self._on_run_graph)
        self.run_button.set_can_focus(False)  # Botões não recebem foco
        self.sidebar_toggle.set_can_focus(False)
        # self.result_toggle.connect("toggled", self._on_result_toggle)

        # Criar botão de dependências programaticamente
        self._add_deps_button()

        # Popular lista inicial de nodes
        self._populate_node_list()

        # Criar TabView para múltiplos projetos
        self.tab_view = Adw.TabView()
        self.tab_view.set_vexpand(True)
        self.tab_view.set_hexpand(True)

        # Criar TabBar
        self.tab_bar = Adw.TabBar()
        self.tab_bar.set_view(self.tab_view)
        self.tab_bar.set_autohide(False)  # Sempre mostrar a barra

        # Adicionar TabBar e TabView ao canvas_box
        self.canvas_box.append(self.tab_bar)
        self.canvas_box.append(self.tab_view)

        # Conectar sinal de mudança de página
        self.tab_view.connect("notify::selected-page", self._on_tab_changed)

        # Criar primeira aba
        self._create_new_tab()

        # Inicializar referências para a primeira aba
        self._on_tab_changed(self.tab_view, None)

    def _add_deps_button(self):
        """Adiciona botão de gerenciar dependências"""
        print("🔧 _add_deps_button() called")

        # Apenas registrar atalho de teclado por enquanto
        app = self.get_application()
        if app:
            app.set_accels_for_action("win.manage-dependencies", ["<Ctrl>d"])
            print("✓ Keyboard shortcut Ctrl+D registered for dependencies")
            print("  Press Ctrl+D to open Dependencies Manager")
        else:
            print("⚠️  No app available for keyboard shortcut")

    def _auto_install_dependencies(self, project, filepath, graph_data):
        """Instala dependências listadas em project_metadata.requirements"""
        import threading
        from .dependency_manager import DependencyManager

        print("\n" + "="*60)
        print("📦 VERIFICANDO DEPENDÊNCIAS DO PROJETO")
        print("="*60)

        # Usar APENAS a lista de requirements do metadata
        required = set(graph_data.get('project_metadata', {}).get('requirements', []))

        if not required:
            print("ℹ️  Nenhuma dependência especificada em project_metadata.requirements")
            print("="*60 + "\n")
            return

        print(f"📋 Dependências requeridas: {', '.join(sorted(required))}")

        # Verificar o que está faltando
        missing = set()
        for package in required:
            try:
                module_name = package.replace('-', '_')
                __import__(module_name)
            except ImportError:
                missing.add(package)

        manager = DependencyManager(filepath)

        if not missing:
            print("✓ Todas as dependências estão disponíveis")
            print("="*60 + "\n")
            return

        print(f"⚠️  {len(missing)} pacote(s) faltando: {', '.join(sorted(missing))}")
        print(f"\n🔄 Instalando automaticamente...")
        print("="*60 + "\n")

        def install_worker():
            """Worker thread para instalar em background"""
            success = manager.add_packages(list(missing))

            if success:
                print("\n" + "="*60)
                print("✓ DEPENDÊNCIAS INSTALADAS COM SUCESSO")
                print("="*60)
                print("📝 Salvando projeto...")

                # NÃO PRECISA SALVAR AQUI!
                # O DependencyManager.add_packages() JÁ salvou o projeto com wheels
                # Apenas recarregar o ambiente
                from gi.repository import GLib
                def reload_only():
                    save_path = project.current_file

                    print("\n🔄 Recarregando ambiente do arquivo salvo (já contém wheels)...")
                    print(f"   Arquivo: {save_path}")

                    # Recarregar ambiente do arquivo SALVO
                    # Note: graph_data já foi alterado pelo add_packages, mas vamos recarregar
                    from .graph_io import GraphSerializer
                    reloaded_data = GraphSerializer.load_graph(save_path, check_dependencies=False)
                    if reloaded_data:
                        project.setup_isolated_environment(save_path, reloaded_data)
                    else:
                        project.setup_isolated_environment(save_path)

                    print("✓ Ambiente recarregado - pronto para executar!")
                    print("="*60 + "\n")

                    # Mostrar toast
                    toast = Adw.Toast.new(f"✓ {len(missing)} dependencies installed automatically")
                    self.toast_overlay.add_toast(toast)

                    return False

                GLib.idle_add(reload_only)

        thread = threading.Thread(target=install_worker, daemon=True)
        thread.start()

        # Note: Canvas will grab focus when clicked (see canvas.py on_mouse_pressed)
        # We don't grab focus on startup to avoid interfering with search entry

        # Connect close handler to cleanup
        self.connect("close-request", self._on_close_request)

    def _create_new_tab(self, title=None, file_path=None):
        """Cria uma nova aba de projeto"""
        # Criar projeto
        project = ProjectTab()

        if file_path:
            project.current_file = file_path

        # Criar página na TabView
        page = self.tab_view.append(project.get_widget())

        # Definir título da aba
        tab_title = title if title else project.get_title()
        page.set_title(tab_title)
        page.set_tooltip(project.get_tooltip())

        # Guardar referência ao projeto na página
        page.project = project

        # Conectar canvas actions para este projeto
        self._setup_canvas_actions_for_project(project)

        return project

    def _on_tab_changed(self, tab_view, param):
        """Chamado quando a aba ativa muda"""
        page = tab_view.get_selected_page()
        if page and hasattr(page, 'project'):
            # Atualizar referências de compatibilidade
            self.canvas = page.project.canvas
            self.output_panel = page.project.output_panel
            self.scrolled_window = page.project.scrolled_window
            self.current_file = page.project.current_file

    @property
    def current_tab(self):
        """Retorna a aba/projeto atual"""
        page = self.tab_view.get_selected_page()
        if page and hasattr(page, 'project'):
            return page.project
        return None

    def _on_paste_action(self, canvas):
        """Handler para ação de paste do menu de contexto"""
        # Verificar se há posição do menu de contexto salva
        if hasattr(canvas, 'context_menu_position') and canvas.context_menu_position:
            # Colar na posição do menu de contexto
            paste_x, paste_y = canvas.context_menu_position
            canvas._paste_node(paste_x, paste_y)
            canvas.context_menu_position = None  # Limpar
        else:
            # Colar com offset padrão (Ctrl+V)
            canvas._paste_node()

    def _setup_canvas_actions_for_project(self, project):
        """Setup actions for canvas context menu for a specific project"""
        canvas = project.canvas

        # Edit Code action
        edit_action = Gio.SimpleAction.new("edit-code", None)
        edit_action.connect("activate", lambda a, p: canvas.edit_node_code())
        canvas.action_group.add_action(edit_action)

        # Rename action
        rename_action = Gio.SimpleAction.new("rename", None)
        rename_action.connect("activate", lambda a, p: canvas.rename_node())
        canvas.action_group.add_action(rename_action)

        # Properties action
        props_action = Gio.SimpleAction.new("properties", None)
        props_action.connect("activate", lambda a, p: canvas.show_node_properties())
        canvas.action_group.add_action(props_action)

        # Save to Library action
        save_lib_action = Gio.SimpleAction.new("save-to-library", None)
        save_lib_action.connect("activate", lambda a, p: canvas.save_node_to_library())
        canvas.action_group.add_action(save_lib_action)

        # Delete action
        delete_action = Gio.SimpleAction.new("delete", None)
        delete_action.connect("activate", lambda a, p: canvas.delete_context_node())
        canvas.action_group.add_action(delete_action)

        # Clipboard actions
        copy_action = Gio.SimpleAction.new("copy", None)
        copy_action.connect("activate", lambda a, p: canvas._copy_focused_node())
        canvas.action_group.add_action(copy_action)

        cut_action = Gio.SimpleAction.new("cut", None)
        cut_action.connect("activate", lambda a, p: canvas._cut_context_node())
        canvas.action_group.add_action(cut_action)

        paste_action = Gio.SimpleAction.new("paste", None)
        paste_action.connect("activate", lambda a, p: self._on_paste_action(canvas))
        canvas.action_group.add_action(paste_action)

        # Alignment actions
        align_left = Gio.SimpleAction.new("align-left", None)
        align_left.connect("activate", lambda a, p: canvas.align_selected_nodes("left"))
        canvas.action_group.add_action(align_left)

        align_center_h = Gio.SimpleAction.new("align-center-h", None)
        align_center_h.connect("activate", lambda a, p: canvas.align_selected_nodes("center-h"))
        canvas.action_group.add_action(align_center_h)

        align_right = Gio.SimpleAction.new("align-right", None)
        align_right.connect("activate", lambda a, p: canvas.align_selected_nodes("right"))
        canvas.action_group.add_action(align_right)

        align_top = Gio.SimpleAction.new("align-top", None)
        align_top.connect("activate", lambda a, p: canvas.align_selected_nodes("top"))
        canvas.action_group.add_action(align_top)

        align_center_v = Gio.SimpleAction.new("align-center-v", None)
        align_center_v.connect("activate", lambda a, p: canvas.align_selected_nodes("center-v"))
        canvas.action_group.add_action(align_center_v)

        align_bottom = Gio.SimpleAction.new("align-bottom", None)
        align_bottom.connect("activate", lambda a, p: canvas.align_selected_nodes("bottom"))
        canvas.action_group.add_action(align_bottom)

        # Distribution actions
        distribute_h = Gio.SimpleAction.new("distribute-h", None)
        distribute_h.connect("activate", lambda a, p: canvas.distribute_selected_nodes("horizontal"))
        canvas.action_group.add_action(distribute_h)

        distribute_v = Gio.SimpleAction.new("distribute-v", None)
        distribute_v.connect("activate", lambda a, p: canvas.distribute_selected_nodes("vertical"))
        canvas.action_group.add_action(distribute_v)

        # Connect canvas signal to update node list when library changes
        # self.canvas.connect("node-saved-to-library", lambda c: self._populate_node_list())

    def _create_actions(self):
        """Create window actions"""
        # New
        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new)
        self.add_action(new_action)

        # Open
        open_action = Gio.SimpleAction.new("open", None)
        open_action.connect("activate", self.on_open)
        self.add_action(open_action)

        # Save
        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.on_save)
        self.add_action(save_action)

        # Save As
        save_as_action = Gio.SimpleAction.new("save-as", None)
        save_as_action.connect("activate", self._on_save_as)
        self.add_action(save_as_action)

        # Close Tab
        close_tab_action = Gio.SimpleAction.new("close-tab", None)
        close_tab_action.connect("activate", self.on_close_tab)
        self.add_action(close_tab_action)

        # Project Settings
        project_settings_action = Gio.SimpleAction.new("project-settings", None)
        project_settings_action.connect("activate", self.on_project_settings)
        self.add_action(project_settings_action)

        # Manage Dependencies
        manage_deps_action = Gio.SimpleAction.new("manage-dependencies", None)
        manage_deps_action.connect("activate", self.on_manage_dependencies)
        self.add_action(manage_deps_action)

        # Configurar atalhos de teclado
        app = self.get_application()
        if app:
            app.set_accels_for_action("win.new", ["<Ctrl>n"])
            app.set_accels_for_action("win.save", ["<Ctrl>s"])
            app.set_accels_for_action("win.close-tab", ["<Ctrl>w"])
            app.set_accels_for_action("win.project-settings", ["<Ctrl>comma"])


    def on_new(self, action, param):
        """Handle New action - creates a new tab"""
        self._create_new_tab()
        print("✓ New graph created in new tab")

    def on_close_tab(self, action, param):
        """Handle Close Tab action - fecha a aba atual"""
        current_page = self.tab_view.get_selected_page()
        if current_page:
            # Limpar estado do projeto antes de fechar
            if hasattr(current_page, 'project'):
                project = current_page.project

                # Limpar output_values de todos os nós
                for node in project.canvas.nodes:
                    node.output_values = {}

                # Fechar matplotlib figures se houver
                try:
                    import matplotlib.pyplot as plt
                    plt.close('all')
                except:
                    pass

            # Se só tem uma aba, cria uma nova antes de fechar
            if self.tab_view.get_n_pages() == 1:
                self._create_new_tab()

            # Fecha a aba atual
            self.tab_view.close_page(current_page)
            print("✓ Tab closed")

    def on_project_settings(self, action, param):
        """Handle Project Settings action - abre dialog de metadados"""
        from .project_settings_dialog import ProjectSettingsDialog

        project = self.current_tab
        if not project:
            print("⚠️  No project open")
            return

        # Obter metadados atuais (ou criar padrão)
        metadata = getattr(project, 'project_metadata', {
            "requirements": [],
            "python_mode": "flatpak",
            "author": "",
            "description": "",
            "created_at": None,
            "modified_at": None,
            "tags": [],
            "version": "1.0.0"
        })

        # Criar dialog
        dialog = ProjectSettingsDialog(self, metadata)

        # Passar estatísticas do projeto
        dialog.set_statistics(
            len(project.canvas.nodes),
            len(project.canvas.connections)
        )

        # Callback ao aplicar
        def on_metadata_updated(new_metadata):
            old_python_mode = project.project_metadata.get('python_mode', 'flatpak') if hasattr(project, 'project_metadata') else 'flatpak'
            new_python_mode = new_metadata.get('python_mode', 'flatpak')

            project.project_metadata = new_metadata
            print(f"✓ Project metadata updated")
            print(f"  Python Mode: {new_python_mode}")
            print(f"  Author: {new_metadata.get('author', 'N/A')}")
            print(f"  Description: {new_metadata.get('description', 'N/A')}")
            print(f"  Requirements: {', '.join(new_metadata.get('requirements', []))}")

            # Salvar metadados no arquivo .assets
            if project.current_file:
                from .graph_io import GraphSerializer
                GraphSerializer.save_graph(
                    project.canvas.nodes,
                    project.canvas.connections,
                    project.current_file,
                    view_state=None,
                    project_metadata=new_metadata
                )
                print(f"✓ Metadata saved to {project.current_file}")

                # Recarregar graph_data para pegar metadados atualizados
                graph_data = GraphSerializer.load_graph(project.current_file, check_dependencies=False)

                # Sempre recarregar ambiente (garante que requirements e python_mode estão sincronizados)
                print(f"🔄 Reloading isolated environment...")
                print(f"   Python mode: {new_python_mode}")
                print(f"   Requirements: {new_metadata.get('requirements', [])}")
                project.setup_isolated_environment(project.current_file, graph_data)

                # Se python_mode mudou, mostrar toast
                if old_python_mode != new_python_mode:
                    toast = Adw.Toast.new(f"Switched to {new_python_mode} mode")
                    self.toast_overlay.add_toast(toast)
                else:
                    toast = Adw.Toast.new("Project settings updated")
                    self.toast_overlay.add_toast(toast)

        dialog.on_apply_callback = on_metadata_updated
        dialog.present()

    def on_manage_dependencies(self, action, param):
        """Handle Manage Dependencies action - abre dialog de dependências"""
        from .dependencies_dialog import DependenciesDialog

        project = self.current_tab
        if not project:
            toast = Adw.Toast.new("No project open")
            self.toast_overlay.add_toast(toast)
            return

        if not project.current_file:
            toast = Adw.Toast.new("Save the project before managing dependencies")
            self.toast_overlay.add_toast(toast)
            return

        # Criar e mostrar dialog
        dialog = DependenciesDialog(self, project)
        dialog.present()

    def on_open(self, action, param):
        """Handle Open action"""
        from .graph_io import GraphSerializer

        dialog = Gtk.FileDialog()
        dialog.set_title("Open Graph")

        # Filter for .assets files
        filter_assets = Gtk.FileFilter()
        filter_assets.set_name("Assets Files (*.assets)")
        filter_assets.add_pattern("*.assets")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_assets)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_open_finish)

    def _on_open_finish(self, dialog, result):
        """Callback for open dialog"""
        try:
            file = dialog.open_finish(result)
            if file:
                from .graph_io import GraphSerializer
                from .node import Node
                from pathlib import Path
                filepath = file.get_path()

                # Load graph data (returns dict with raw data)
                graph_data = GraphSerializer.load_graph(filepath)

                if graph_data is not None:
                    # Deserialize nodes
                    nodes = []
                    node_id_map = {}

                    for node_data in graph_data.get("nodes", []):
                        node = Node.from_dict(node_data)
                        nodes.append(node)
                        node_id_map[node.id] = node

                    # Deserialize connections
                    connections = []
                    for conn_data in graph_data.get("connections", []):
                        src_id = conn_data["source_node_id"]
                        dst_id = conn_data["target_node_id"]

                        if src_id in node_id_map and dst_id in node_id_map:
                            connection = (
                                node_id_map[src_id],
                                conn_data["source_port"],
                                node_id_map[dst_id],
                                conn_data["target_port"]
                            )
                            connections.append(connection)
                        else:
                            print(f"⚠️  Invalid connection ignored: {src_id} -> {dst_id}")

                    # Decidir se cria nova aba ou usa a atual
                    current_tab = self.current_tab
                    if current_tab and len(current_tab.canvas.nodes) == 0 and not current_tab.current_file:
                        # Aba atual está vazia, usar ela
                        project = current_tab
                    else:
                        # Criar nova aba
                        filename = Path(filepath).stem
                        project = self._create_new_tab(title=filename, file_path=filepath)
                        # Selecionar a nova aba
                        page = self.tab_view.get_selected_page()
                        n_pages = self.tab_view.get_n_pages()
                        if n_pages > 0:
                            new_page = self.tab_view.get_nth_page(n_pages - 1)
                            self.tab_view.set_selected_page(new_page)

                    # Toast inicial
                    loading_toast = Adw.Toast.new("⏳ Setting up Python environment...")
                    loading_toast.set_timeout(0)  # Infinite até terminar
                    self.toast_overlay.add_toast(loading_toast)

                    # Configurar ambiente isolado ANTES de carregar os nós
                    def on_env_ready(success):
                        loading_toast.dismiss()
                        if success:
                            ready_toast = Adw.Toast.new("✓ Environment ready!")
                            ready_toast.set_timeout(2)
                            self.toast_overlay.add_toast(ready_toast)
                        else:
                            error_toast = Adw.Toast.new("❌ Failed to setup environment")
                            error_toast.set_timeout(3)
                            self.toast_overlay.add_toast(error_toast)

                    project.setup_isolated_environment(filepath, graph_data, on_env_ready)

                    # Update canvas do projeto
                    project.canvas.nodes = nodes
                    project.canvas.connections = connections
                    project.current_file = filepath

                    # Carregar metadados do projeto
                    project.metadata = graph_data.get("project_metadata", {
                        "requirements": [],
                        "author": "",
                        "description": "",
                        "created_at": None,
                        "modified_at": None,
                        "tags": [],
                        "version": "1.0.0"
                    })

                    # Verificar e instalar dependências automaticamente
                    self._auto_install_dependencies(project, filepath, graph_data)

                    # Pre-calculate port positions for all nodes
                    # This ensures connections can be drawn immediately
                    for node in nodes:
                        node._calculate_port_positions()

                    # Update canvas size based on nodes and zoom
                    project.canvas._update_canvas_size()

                    # SEMPRE centralizar o grafo ao abrir, independente do zoom/pan salvos
                    from gi.repository import GLib
                    def center_graph():
                        project.canvas.center_view_on_graph()
                        return False
                    GLib.timeout_add(100, center_graph)

                    project.canvas.queue_draw()

                    # Atualizar título da aba
                    current_page = self.tab_view.get_selected_page()
                    if current_page:
                        current_page.set_title(project.get_title())
                        current_page.set_tooltip(project.get_tooltip())

                    print(f"✓ Graph loaded: {filepath}")
                    print(f"  - {len(nodes)} nodes")
                    print(f"  - {len(connections)} connections")
                else:
                    print(f"❌ Failed to load: {filepath}")
                    toast = Adw.Toast.new(f"Failed to load: {filepath}")
                    self.toast_overlay.add_toast(toast)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"❌ Error opening: {e}")
                import traceback
                traceback.print_exc()
                toast = Adw.Toast.new(f"Error opening file: {e}")
                self.toast_overlay.add_toast(toast)

    def on_save(self, action, param):
        """Handle Save action - salva a aba atual"""
        project = self.current_tab
        if not project:
            return

        if project.current_file:
            self._save_to_file(project.current_file)
        else:
            self._on_save_as(action, param)

    def _on_save_as(self, action, param):
        """Handle Save As action"""
        from .graph_io import get_default_save_directory

        dialog = Gtk.FileDialog()
        dialog.set_title("Save Graph")
        dialog.set_initial_name("graph.assets")

        # Set initial folder
        default_dir = get_default_save_directory()
        if default_dir.exists():
            folder = Gio.File.new_for_path(str(default_dir))
            dialog.set_initial_folder(folder)

        dialog.save(self, None, self._on_save_finish)

    def _on_save_finish(self, dialog, result):
        """Callback for save dialog"""
        try:
            file = dialog.save_finish(result)
            if file:
                filepath = file.get_path()

                # Ensure .assets extension
                if not filepath.endswith('.assets'):
                    filepath += '.assets'

                self._save_to_file(filepath)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"❌ Error saving: {e}")

    def _save_to_file(self, filepath):
        """Save graph to file - salva o projeto da aba atual"""
        from .graph_io import GraphSerializer
        from pathlib import Path

        project = self.current_tab
        if not project:
            return

        # Capturar estado visual atual do projeto
        hadj = project.scrolled_window.get_hadjustment()
        vadj = project.scrolled_window.get_vadjustment()

        view_state = {
            "zoom": project.canvas.zoom_level,
            "scroll_x": hadj.get_value() if hadj else 0,
            "scroll_y": vadj.get_value() if vadj else 0
        }

        # Obter metadados do projeto (se existir)
        project_metadata = getattr(project, 'metadata', None)

        success = GraphSerializer.save_graph(
            project.canvas.nodes,
            project.canvas.connections,
            filepath,
            view_state,
            project_metadata
        )

        if success:
            project.current_file = filepath

            # Atualizar título da aba
            current_page = self.tab_view.get_selected_page()
            if current_page:
                current_page.set_title(project.get_title())
                current_page.set_tooltip(project.get_tooltip())

            print(f"✓ Saved: {filepath}")


    def _populate_node_list(self, nodes=None):
        """Populate node list in sidebar"""
        if self._is_populating:
            return

        self._is_populating = True

        try:
            from .node_library import get_all_categories, get_nodes_in_category, get_category_icon

            # Clear existing rows
            while True:
                row = self.node_list.get_row_at_index(0)
                if row is None:
                    break
                self.node_list.remove(row)

            if nodes is None:
                # Normal mode: show by categories with expand/collapse
                for category in get_all_categories():
                    icon = get_category_icon(category)

                    # Inicializar estado da categoria se não existir (contraída por padrão)
                    if category not in self._expanded_categories:
                        self._expanded_categories[category] = False

                    is_expanded = self._expanded_categories[category]
                    expand_icon = "−" if is_expanded else "+"

                    # Category header (clicável para expandir/contrair)
                    header_button = Gtk.Button()
                    header_button.set_has_frame(False)
                    header_button.set_halign(Gtk.Align.START)
                    header_label = Gtk.Label()
                    header_label.set_markup(f"<b>{expand_icon} {icon} {category}</b>")
                    header_label.set_xalign(0)
                    header_button.set_child(header_label)
                    header_button.connect("clicked", self._on_category_toggle, category)

                    header_button.set_margin_top(6)
                    header_button.set_margin_bottom(3)
                    header_button.set_margin_start(3)

                    header_row = Gtk.ListBoxRow()
                    header_row.set_child(header_button)
                    header_row.set_selectable(False)
                    header_row.set_activatable(False)
                    self.node_list.append(header_row)

                    # Nodes in category (somente se expandida)
                    if is_expanded:
                        category_nodes = get_nodes_in_category(category)
                        for node_template in category_nodes:
                            self._create_node_row(node_template)
            else:
                # Search/filter mode: show specific nodes
                if not nodes:
                    no_results = Gtk.Label(label="No nodes found")
                    no_results.set_margin_top(20)
                    no_results.set_margin_bottom(20)
                    row = Gtk.ListBoxRow()
                    row.set_child(no_results)
                    row.set_selectable(False)
                    row.set_activatable(False)
                    self.node_list.append(row)
                else:
                    for node_template in nodes:
                        self._create_node_row(node_template, show_category=True)
        finally:
            self._is_populating = False

    def _create_node_row(self, node_template, show_category=False):
        """Create a row for a node template"""
        from .node_library import _get_library

        library = _get_library()

        # Horizontal box for button + favorite star
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        # Node button
        node_label = node_template["name"]
        if show_category and "_category" in node_template:
            node_label = f"[{node_template['_category']}] {node_label}"

        node_button = Gtk.Button(label=node_label)
        node_button.set_has_frame(False)
        node_button.set_halign(Gtk.Align.START)
        node_button.set_hexpand(True)

        # Tooltip with description and tags
        tooltip = node_template.get("description", "")
        if "tags" in node_template and node_template["tags"]:
            tooltip += f"\n\nTags: {', '.join(node_template['tags'])}"
        node_button.set_tooltip_text(tooltip)

        node_button.connect("clicked", self._on_node_template_clicked, node_template)
        hbox.append(node_button)

        # Favorite button
        is_fav = library.is_favorite(node_template["name"])
        fav_button = Gtk.Button()
        fav_button.set_icon_name("starred-symbolic" if is_fav else "non-starred-symbolic")
        fav_button.set_has_frame(False)
        fav_button.set_tooltip_text("Toggle favorite")
        fav_button.connect("clicked", self._on_toggle_favorite, node_template["name"])
        hbox.append(fav_button)

        row = Gtk.ListBoxRow()
        row.set_child(hbox)
        row.set_activatable(False)
        self.node_list.append(row)

    def _on_category_toggle(self, button, category):
        """Toggle expand/collapse de uma categoria"""
        # Alternar estado
        self._expanded_categories[category] = not self._expanded_categories.get(category, False)

        # Repopular lista para mostrar/ocultar nós
        self._populate_node_list()

    def _on_node_template_clicked(self, button, template):
        """When clicking a node template in the library"""
        from .node_library import create_node_from_template

        # Pegar canvas da aba atual
        if not self.current_tab:
            return

        canvas = self.current_tab.canvas

        # Create node at center of visible canvas
        center_x = (400 - canvas.pan_offset_x) / canvas.zoom_level
        center_y = (300 - canvas.pan_offset_y) / canvas.zoom_level

        new_node = create_node_from_template(template, center_x, center_y)
        canvas.nodes.append(new_node)

        # Select the new node
        for node in canvas.nodes:
            node.set_selected(False)
        new_node.set_selected(True)
        canvas.focused_node_index = len(canvas.nodes) - 1

        # Update canvas size
        canvas._update_canvas_size()

        canvas.queue_draw()

        # Return focus to canvas for keyboard shortcuts
        canvas.grab_focus()

    def _on_search_changed(self, search_entry):
        """Search nodes as user types"""
        query = search_entry.get_text().strip()

        from .node_library import _get_library
        library = _get_library()

        if query:
            self.favorites_toggle.set_active(False)
            results = library.search_nodes(query)
            self._populate_node_list(results)
        else:
            self._populate_node_list()

    def _on_favorites_toggled(self, button):
        """Toggle favorites filter"""
        from .node_library import _get_library

        library = _get_library()

        if button.get_active():
            # Clear search
            self.search_entry.set_text("")
            favorites = library.get_favorites()
            self._populate_node_list(favorites)
        else:
            self._populate_node_list()

    def _on_toggle_favorite(self, button, node_name):
        """Toggle favorite status of a node"""
        from .node_library import _get_library

        library = _get_library()
        library.toggle_favorite(node_name)

        # Update UI
        if self.favorites_toggle.get_active():
            # If in favorites mode, update list
            favorites = library.get_favorites()
            self._populate_node_list(favorites)
        elif self.search_entry.get_text().strip():
            # If searching, redo search
            self._on_search_changed(self.search_entry)
        else:
            # Recreate normal list
            self._populate_node_list()

    def _on_import_library(self, button):
        """Import node library from file"""
        print("Import library clicked")
        # TODO: Implement import dialog

    def _on_export_library(self, button):
        """Export node library to file"""
        print("Export library clicked")
        # TODO: Implement export dialog

    def _on_run_graph(self, button):
        """When clicking Run button - execute graph in background"""
        import threading

        # Pegar o projeto/canvas da aba atual
        current_project = self.current_tab
        if not current_project:
            print("❌ No active project")
            return

        # Verificar se ambiente está pronto
        if not current_project.environment_ready:
            toast = Adw.Toast.new("⏳ Environment is still loading, please wait...")
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)
            return

        # Disable button during execution
        button.set_sensitive(False)

        def run_in_background():
            # Execute the graph da aba atual
            success = current_project.canvas.execute_graph()

            # Re-enable button on main thread
            from gi.repository import GLib
            def finish():
                button.set_sensitive(True)
                if success:
                    print("=" * 60)
                    print("✅ EXECUTION COMPLETED SUCCESSFULLY")
                    print("=" * 60 + "\n")
                else:
                    print("=" * 60)
                    print("❌ EXECUTION FAILED")
                    print("=" * 60 + "\n")
                return False  # Remove from idle queue

            GLib.idle_add(finish)

        # Start thread
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()

    def _on_result_toggle(self, button):
        """Toggle visibility of result area"""
        if button.get_active():
            self.result_box.set_visible(True)
        else:
            self.result_box.set_visible(False)

    def _recreate_library_panel(self):
        """Recreate library panel (after adding new nodes)"""
        # Just repopulate the list
        self._populate_node_list()
        print("✓ Library updated")

    def _on_close_request(self, window):
        """Cleanup before closing"""
        try:
            # Close all matplotlib figures
            import matplotlib.pyplot as plt
            plt.close('all')
        except:
            pass

        # Allow window to close
        return False  # False = allow close, True = prevent close

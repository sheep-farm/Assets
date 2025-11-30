#!/usr/bin/env python3
"""
dependencies_dialog.py - Dialog para gerenciar dependências do projeto
"""

from gi.repository import Gtk, Adw, GLib
import threading
from pathlib import Path


class DependenciesDialog(Adw.Window):
    """Dialog para gerenciar dependências de um projeto"""

    def __init__(self, parent, project_tab):
        super().__init__()

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 500)
        self.set_title("Manage Project Dependencies")

        self.project_tab = project_tab
        self.parent_window = parent

        # Toast overlay para notificações
        self.toast_overlay = Adw.ToastOverlay()

        # Header bar
        header = Adw.HeaderBar()

        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)

        # Main content
        content = self._create_content()
        toolbar_view.set_content(content)

        self.toast_overlay.set_child(toolbar_view)
        self.set_content(self.toast_overlay)

        # Carregar estado inicial
        self._refresh_state()

    def _create_content(self):
        """Cria o conteúdo principal do dialog"""

        # Box principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)

        # Grupo: Projeto atual
        project_group = Adw.PreferencesGroup()
        project_group.set_title("Current Project")

        project_name = self.project_tab.get_title() if self.project_tab.current_file else "Untitled"
        self.project_label = Gtk.Label(label=project_name)
        self.project_label.set_halign(Gtk.Align.START)

        project_row = Adw.ActionRow()
        project_row.set_title("Project")
        project_row.add_suffix(self.project_label)
        project_group.add(project_row)

        main_box.append(project_group)

        # Grupo: Dependências detectadas
        detected_group = Adw.PreferencesGroup()
        detected_group.set_title("Required Packages")
        detected_group.set_description("Packages detected in node code")

        # Lista de pacotes detectados
        self.detected_list = Gtk.ListBox()
        self.detected_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.detected_list.add_css_class("boxed-list")

        detected_group.add(self.detected_list)
        main_box.append(detected_group)

        # Grupo: Wheels instalados
        installed_group = Adw.PreferencesGroup()
        installed_group.set_title("Installed Wheels")
        installed_group.set_description("Dependency wheels included in this project")

        # Lista de wheels
        self.wheels_list = Gtk.ListBox()
        self.wheels_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.wheels_list.add_css_class("boxed-list")

        installed_group.add(self.wheels_list)
        main_box.append(installed_group)

        # Botão de ação
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_top(12)

        self.install_button = Gtk.Button(label="Install Missing Dependencies")
        self.install_button.add_css_class("suggested-action")
        self.install_button.add_css_class("pill")
        self.install_button.connect("clicked", self._on_install_clicked)

        action_box.append(self.install_button)
        main_box.append(action_box)

        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(main_box)

        return scrolled

    def _refresh_state(self):
        """Atualiza o estado das listas"""
        if not self.project_tab.current_file:
            self._show_message("No project file. Save the project first.")
            return

        from .zip_project import AssetsProject
        from .dependency_manager import DependencyManager

        # Carregar projeto
        project = AssetsProject(self.project_tab.current_file)
        graph_data = project.load_graph()

        if not graph_data:
            self._show_message("Failed to load project")
            return

        # Detectar dependências
        manager = DependencyManager(self.project_tab.current_file)
        required = manager.scan_imports(graph_data)
        missing = manager.get_missing_packages(graph_data)

        # Wheels instalados
        wheels = project.list_wheels()

        # Atualizar lista de pacotes detectados
        self._clear_list(self.detected_list)

        if required:
            for package in sorted(required):
                row = Adw.ActionRow()
                row.set_title(package)

                # Indicador de status
                if package in missing:
                    icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
                    icon.set_tooltip_text("Missing")
                    row.add_prefix(icon)
                else:
                    icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                    icon.set_tooltip_text("Available")
                    row.add_prefix(icon)

                self.detected_list.append(row)
        else:
            placeholder = Gtk.Label(label="No external packages detected")
            placeholder.set_margin_top(12)
            placeholder.set_margin_bottom(12)
            placeholder.add_css_class("dim-label")
            self.detected_list.append(placeholder)

        # Atualizar lista de wheels
        self._clear_list(self.wheels_list)

        if wheels:
            for wheel in wheels:
                row = Adw.ActionRow()
                row.set_title(wheel)

                icon = Gtk.Image.new_from_icon_name("package-x-generic-symbolic")
                row.add_prefix(icon)

                self.wheels_list.append(row)
        else:
            placeholder = Gtk.Label(label="No wheels installed")
            placeholder.set_margin_top(12)
            placeholder.set_margin_bottom(12)
            placeholder.add_css_class("dim-label")
            self.wheels_list.append(placeholder)

        # Atualizar botão
        if missing:
            self.install_button.set_label(f"Install {len(missing)} Missing Package(s)")
            self.install_button.set_sensitive(True)
        else:
            self.install_button.set_label("All Dependencies Installed")
            self.install_button.set_sensitive(False)

    def _clear_list(self, list_box):
        """Limpa todos os widgets de uma listbox"""
        while True:
            row = list_box.get_first_child()
            if row is None:
                break
            list_box.remove(row)

    def _on_install_clicked(self, button):
        """Instala dependências faltando"""
        if not self.project_tab.current_file:
            return

        from .dependency_manager import DependencyManager
        from .zip_project import AssetsProject

        # Desabilitar botão durante instalação
        button.set_sensitive(False)
        button.set_label("Installing...")

        # Carregar projeto
        project = AssetsProject(self.project_tab.current_file)
        graph_data = project.load_graph()

        if not graph_data:
            self._show_message("Failed to load project")
            button.set_sensitive(True)
            return

        # Detectar dependências faltando
        manager = DependencyManager(self.project_tab.current_file)
        missing = manager.get_missing_packages(graph_data)

        if not missing:
            self._show_message("No missing dependencies")
            button.set_sensitive(True)
            return

        # Instalar em background
        def install_worker():
            success = manager.add_packages(list(missing))

            # Atualizar UI na thread principal
            GLib.idle_add(lambda: self._on_install_complete(success))

        thread = threading.Thread(target=install_worker, daemon=True)
        thread.start()

    def _on_install_complete(self, success):
        """Callback quando instalação termina"""
        if success:
            self._show_message("✓ Dependencies installed successfully!")

            # IMPORTANTE: Salvar o projeto para persistir os wheels no .assets
            if self.project_tab.current_file:
                print("\n📝 Salvando projeto com novos wheels...")
                from .graph_io import GraphSerializer

                # Capturar estado visual
                hadj = self.project_tab.scrolled_window.get_hadjustment()
                vadj = self.project_tab.scrolled_window.get_vadjustment()

                view_state = {
                    "zoom": self.project_tab.canvas.zoom_level,
                    "scroll_x": hadj.get_value() if hadj else 0,
                    "scroll_y": vadj.get_value() if vadj else 0
                }

                # Salvar projeto
                GraphSerializer.save_graph(
                    self.project_tab.canvas.nodes,
                    self.project_tab.canvas.connections,
                    self.project_tab.current_file,
                    view_state,
                    getattr(self.project_tab, 'metadata', None)
                )

                print("✓ Projeto salvo com wheels incluídos")

            # Reconfigurar ambiente isolado com novos wheels
            if self.project_tab.current_file:
                print("🔄 Recarregando ambiente isolado...")
                self.project_tab.setup_isolated_environment(self.project_tab.current_file)
                print("✓ Ambiente recarregado")

            # Atualizar listas
            self._refresh_state()
        else:
            self._show_message("❌ Failed to install dependencies")
            self.install_button.set_sensitive(True)
            self.install_button.set_label("Retry Installation")

        return False  # Remove from idle queue

    def _show_message(self, message):
        """Mostra mensagem como toast"""
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

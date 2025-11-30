#!/usr/bin/env python3
"""
project_settings_dialog.py - Dialog para editar metadados do projeto
"""

import gi
from gi.repository import Gtk, Adw
from datetime import datetime


class ProjectSettingsDialog(Adw.PreferencesWindow):
    """Dialog Adwaita para editar metadados do projeto (.assets)"""

    def __init__(self, parent, project_metadata: dict = None):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 500)
        self.set_search_enabled(False)

        self.metadata = project_metadata or {}

        # Criar páginas
        self._create_general_page()
        self._create_dependencies_page()
        self._create_info_page()

        # Botão Apply no close
        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, window):
        """Chamado ao fechar janela"""
        if hasattr(self, 'on_apply_callback'):
            self.on_apply_callback(self.get_metadata())
        return False  # Permite fechar

    def _create_general_page(self):
        """Cria página de informações gerais"""
        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("emblem-system-symbolic")

        # Group: Project Info
        group = Adw.PreferencesGroup()
        group.set_title("Project Information")
        group.set_description("Basic information about this project")

        # Python Mode (ComboRow)
        python_mode_row = Adw.ComboRow()
        python_mode_row.set_title("Python Execution Mode")
        python_mode_row.set_subtitle("How to execute Python code in this project")

        # Criar modelo de strings
        mode_model = Gtk.StringList()
        mode_model.append("Flatpak (wheels in .assets)")
        mode_model.append("System (venv in ~/.local/share/assets/venvs/)")

        python_mode_row.set_model(mode_model)

        # Selecionar modo atual
        current_mode = self.metadata.get("python_mode", "flatpak")
        python_mode_row.set_selected(0 if current_mode == "flatpak" else 1)

        self.python_mode_combo = python_mode_row
        group.add(python_mode_row)

        # Autor
        author_row = Adw.EntryRow()
        author_row.set_title("Author")
        author_row.set_text(self.metadata.get("author", ""))
        self.author_entry = author_row
        group.add(author_row)

        # Descrição
        desc_row = Adw.EntryRow()
        desc_row.set_title("Description")
        desc_row.set_text(self.metadata.get("description", ""))
        self.desc_entry = desc_row
        group.add(desc_row)

        # Versão
        version_row = Adw.EntryRow()
        version_row.set_title("Version")
        version_row.set_text(self.metadata.get("version", "1.0.0"))
        self.version_entry = version_row
        group.add(version_row)

        # Tags (com ActionRow wrapper para subtitle)
        tags_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        tags_row = Adw.EntryRow()
        tags_row.set_title("Tags")
        tags_row.set_text(", ".join(self.metadata.get("tags", [])))
        self.tags_entry = tags_row

        # Label explicativa abaixo
        tags_label = Gtk.Label()
        tags_label.set_markup("<small>Comma-separated tags for organization</small>")
        tags_label.set_halign(Gtk.Align.START)
        tags_label.set_margin_start(12)
        tags_label.set_margin_top(2)
        tags_label.add_css_class("dim-label")

        group.add(tags_row)

        page.add(group)
        self.add(page)

    def _create_dependencies_page(self):
        """Cria página de dependências"""
        page = Adw.PreferencesPage()
        page.set_title("Dependencies")
        page.set_icon_name("application-x-executable-symbolic")

        # Group: Python Packages
        group = Adw.PreferencesGroup()
        group.set_title("Python Dependencies")
        group.set_description("Packages required by this project (auto-detected)")

        # Lista de requirements (read-only com botão de refresh)
        requirements = self.metadata.get("requirements", [])

        if requirements:
            for pkg in requirements:
                row = Adw.ActionRow()
                row.set_title(pkg)
                row.set_subtitle("Auto-detected from code")

                # Ícone de pacote
                icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
                row.add_prefix(icon)

                group.add(row)
        else:
            # Mensagem se não houver dependências
            row = Adw.ActionRow()
            row.set_title("No dependencies detected")
            row.set_subtitle("Dependencies are automatically detected from node code")
            group.add(row)

        page.add(group)

        # Group: Manual Override
        override_group = Adw.PreferencesGroup()
        override_group.set_title("Manual Override")
        override_group.set_description("Add dependencies not auto-detected")

        manual_row = Adw.EntryRow()
        manual_row.set_title("Additional Packages")
        manual_row.set_text(", ".join(self.metadata.get("manual_requirements", [])))
        self.manual_req_entry = manual_row
        override_group.add(manual_row)

        # Label explicativa
        manual_label = Gtk.Label()
        manual_label.set_markup("<small>Comma-separated package names (e.g., scipy, yfinance)</small>")
        manual_label.set_halign(Gtk.Align.START)
        manual_label.set_margin_start(12)
        manual_label.set_margin_top(2)
        manual_label.add_css_class("dim-label")

        page.add(override_group)
        self.add(page)

    def _create_info_page(self):
        """Cria página de informações técnicas"""
        page = Adw.PreferencesPage()
        page.set_title("Info")
        page.set_icon_name("info-symbolic")

        # Group: Timestamps
        time_group = Adw.PreferencesGroup()
        time_group.set_title("Timestamps")

        created = self.metadata.get("created_at")
        if created:
            created_row = Adw.ActionRow()
            created_row.set_title("Created")
            created_row.set_subtitle(self._format_timestamp(created))
            time_group.add(created_row)

        modified = self.metadata.get("modified_at")
        if modified:
            modified_row = Adw.ActionRow()
            modified_row.set_title("Last Modified")
            modified_row.set_subtitle(self._format_timestamp(modified))
            time_group.add(modified_row)

        if created or modified:
            page.add(time_group)

        # Group: Statistics
        stats_group = Adw.PreferencesGroup()
        stats_group.set_title("Project Statistics")

        # Número de nós (será preenchido externamente)
        if hasattr(self, 'node_count'):
            nodes_row = Adw.ActionRow()
            nodes_row.set_title("Total Nodes")
            nodes_row.set_subtitle(str(self.node_count))
            stats_group.add(nodes_row)

        if hasattr(self, 'connection_count'):
            conn_row = Adw.ActionRow()
            conn_row.set_title("Total Connections")
            conn_row.set_subtitle(str(self.connection_count))
            stats_group.add(conn_row)

        page.add(stats_group)

        # Group: Advanced
        advanced_group = Adw.PreferencesGroup()
        advanced_group.set_title("Advanced")

        # Editor de metadados raw (JSON)
        expand_row = Adw.ExpanderRow()
        expand_row.set_title("Raw Metadata (JSON)")
        expand_row.set_subtitle("Advanced: Edit metadata as JSON")

        # TextView para JSON
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_margin_top(6)
        scrolled.set_margin_bottom(6)
        scrolled.set_margin_start(6)
        scrolled.set_margin_end(6)

        self.json_view = Gtk.TextView()
        self.json_view.set_monospace(True)
        self.json_view.set_wrap_mode(Gtk.WrapMode.WORD)

        import json
        json_text = json.dumps(self.metadata, indent=2, ensure_ascii=False)
        self.json_view.get_buffer().set_text(json_text)

        scrolled.set_child(self.json_view)
        expand_row.add_row(Adw.PreferencesRow(child=scrolled))

        advanced_group.add(expand_row)
        page.add(advanced_group)

        self.add(page)

    def _format_timestamp(self, timestamp_str: str) -> str:
        """Formata timestamp ISO para exibição"""
        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
        return timestamp_str or "Unknown"

    def get_metadata(self) -> dict:
        """Retorna metadados editados"""
        import json

        # Parse tags
        tags_text = self.tags_entry.get_text().strip()
        tags = [t.strip() for t in tags_text.split(',') if t.strip()]

        # Parse manual requirements
        manual_text = self.manual_req_entry.get_text().strip()
        manual_req = [t.strip() for t in manual_text.split(',') if t.strip()]

        # Tentar parsear JSON do editor raw (se foi modificado)
        try:
            buffer = self.json_view.get_buffer()
            start = buffer.get_start_iter()
            end = buffer.get_end_iter()
            json_text = buffer.get_text(start, end, False)
            raw_metadata = json.loads(json_text)
        except:
            raw_metadata = {}

        # Mesclar: campos do form têm prioridade
        metadata = {**raw_metadata, **self.metadata}

        metadata.update({
            "author": self.author_entry.get_text().strip(),
            "description": self.desc_entry.get_text().strip(),
            "version": self.version_entry.get_text().strip(),
            "tags": tags,
            "manual_requirements": manual_req,
            "modified_at": datetime.now().isoformat() + "Z"
        })

        # Manter requirements auto-detectados
        if "requirements" not in metadata:
            metadata["requirements"] = []

        # Adicionar manual requirements aos requirements
        all_requirements = set(metadata["requirements"]) | set(manual_req)
        metadata["requirements"] = sorted(list(all_requirements))

        # Manter created_at se existir
        if "created_at" not in metadata or not metadata["created_at"]:
            metadata["created_at"] = datetime.now().isoformat() + "Z"

        return metadata

    def set_statistics(self, node_count: int, connection_count: int):
        """Define estatísticas do projeto (chamado externamente)"""
        self.node_count = node_count
        self.connection_count = connection_count

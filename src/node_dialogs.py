#!/usr/bin/env python3
"""
node_dialogs.py - Dialogs para edição de nós (Adwaita-style)
"""

import gi
from gi.repository import Gtk, Adw, Gio, GtkSource, Gdk


class CodeEditorDialog(Adw.Window):
    """Dialog Adwaita para editar código Python do nó"""

    def __init__(self, parent, node):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)

        # Maximizar a janela
        self.maximize()

        self.node = node

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Adwaita HeaderBar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=f"Edit Code: {node.title}", subtitle="Python Code Editor"))

        # Botão Cancel
        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.add_css_class("flat")
        cancel_button.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_button)

        # Botão Apply (suggested action)
        apply_button = Gtk.Button(label="Apply")
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", self._on_apply)
        header.pack_end(apply_button)

        main_box.append(header)

        # Content area com ToolbarView
        toolbar_view = Adw.ToolbarView()

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.set_spacing(6)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        # Info banner
        banner = Adw.Banner(title="Return values as tuple: return (output1, output2, ...)")
        banner.set_revealed(True)
        banner.add_css_class("inline")
        content.append(banner)

        # Editor de código com GtkSourceView
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.add_css_class("card")

        # SourceView com syntax highlighting
        self.text_view = GtkSource.View()
        self.text_buffer = self.text_view.get_buffer()

        # Configurações do editor
        self.text_view.set_show_line_numbers(True)
        self.text_view.set_highlight_current_line(True)
        self.text_view.set_auto_indent(True)
        self.text_view.set_indent_on_tab(True)
        self.text_view.set_tab_width(4)
        self.text_view.set_insert_spaces_instead_of_tabs(True)
        self.text_view.set_monospace(True)
        self.text_view.set_top_margin(12)
        self.text_view.set_bottom_margin(12)
        self.text_view.set_left_margin(12)
        self.text_view.set_right_margin(12)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)

        # Configurar linguagem Python
        lang_manager = GtkSource.LanguageManager.get_default()
        python_lang = lang_manager.get_language('python3')
        self.text_buffer.set_language(python_lang)

        # Configurar style scheme
        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme = style_manager.get_scheme('Adwaita-dark')
        if scheme is None:
            scheme = style_manager.get_scheme('classic')
        if scheme:
            self.text_buffer.set_style_scheme(scheme)

        # Definir código atual
        self.text_buffer.set_text(node.code)

        scrolled.set_child(self.text_view)
        content.append(scrolled)

        toolbar_view.set_content(content)
        main_box.append(toolbar_view)

        self.set_content(main_box)

        # Configurar atalhos de teclado
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Dar foco ao editor
        self.text_view.grab_focus()

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Callback para teclas pressionadas"""
        # ESC: Fechar sem aplicar
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True

        # Ctrl+S: Aplicar e fechar
        if keyval == Gdk.KEY_s or keyval == Gdk.KEY_S:
            if state & Gdk.ModifierType.CONTROL_MASK:
                self._on_apply(None)
                return True

        return False

    def _on_apply(self, button):
        """Callback do botão Apply"""
        # Emitir sinal customizado ou chamar callback
        if hasattr(self, 'on_apply_callback'):
            self.on_apply_callback(self.get_code())
        self.close()

    def get_code(self):
        """Retorna o código editado"""
        start = self.text_buffer.get_start_iter()
        end = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(start, end, False)


class RenameNodeDialog(Adw.MessageDialog):
    """Dialog Adwaita para renomear nó"""

    def __init__(self, parent, node):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)

        self.node = node

        self.set_heading("Rename Node")
        self.set_body("Enter a new name for this node")

        # Entry dentro do dialog
        self.entry = Gtk.Entry()
        self.entry.set_text(node.title)
        self.entry.set_hexpand(True)
        self.entry.set_margin_top(12)
        self.entry.set_margin_bottom(12)
        self.entry.set_margin_start(12)
        self.entry.set_margin_end(12)
        self.entry.connect("activate", lambda e: self.response("rename"))

        self.set_extra_child(self.entry)

        # Botões
        self.add_response("cancel", "Cancel")
        self.add_response("rename", "Rename")
        self.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("rename")
        self.set_close_response("cancel")

        # Dar foco ao entry e selecionar texto
        self.entry.grab_focus()
        self.entry.select_region(0, -1)

    def get_name(self):
        """Retorna o novo nome"""
        return self.entry.get_text().strip()


class SaveToLibraryDialog(Adw.Window):
    """Dialog Adwaita para salvar nó na biblioteca"""

    def __init__(self, parent, node):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(450, 400)

        self.node = node

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # HeaderBar
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Save to Library", subtitle=f"Node: {node.title}"))

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.add_css_class("flat")
        cancel_button.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_button)

        save_button = Gtk.Button(label="Save")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save)
        header.pack_end(save_button)

        main_box.append(header)

        # Content com PreferencesGroup
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)

        # PreferencesGroup
        prefs_group = Adw.PreferencesGroup()
        prefs_group.set_title("Template Information")
        prefs_group.set_description("Save this node as a reusable template")

        # Nome do template (ActionRow com Entry)
        name_row = Adw.EntryRow()
        name_row.set_title("Template Name")
        name_row.set_text(node.title)
        self.name_entry = name_row
        prefs_group.add(name_row)

        # Categoria (usar categoria do nó se existir, senão "Custom")
        category_row = Adw.EntryRow()
        category_row.set_title("Category")
        category_row.set_text(node.category if node.category else "Custom")
        self.category_entry = category_row
        prefs_group.add(category_row)

        # Descrição
        desc_row = Adw.EntryRow()
        desc_row.set_title("Description")
        desc_row.set_text(f"Custom node: {node.title}")
        self.desc_entry = desc_row
        prefs_group.add(desc_row)

        # Visibilidade (ComboRow)
        visibility_row = Adw.ComboRow()
        visibility_row.set_title("Visibility")
        visibility_row.set_subtitle("Private: local only, Public: shareable")

        # Criar lista de opções
        visibility_list = Gtk.StringList()
        visibility_list.append("Private")
        visibility_list.append("Public")
        visibility_row.set_model(visibility_list)
        visibility_row.set_selected(0)  # Default: Private

        self.visibility_combo = visibility_row
        prefs_group.add(visibility_row)

        content_box.append(prefs_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(content_box)
        main_box.append(scrolled)

        self.set_content(main_box)

        # Dar foco ao nome
        name_row.grab_focus()

    def _on_save(self, button):
        """Callback do botão Save"""
        if hasattr(self, 'on_save_callback'):
            self.on_save_callback(self.get_info())
        self.close()

    def get_info(self):
        """Retorna informações do template"""
        visibility_index = self.visibility_combo.get_selected()
        visibility = "private" if visibility_index == 0 else "public"

        return {
            "name": self.name_entry.get_text().strip() or self.node.title,
            "category": self.category_entry.get_text().strip() or "My Nodes",
            "description": self.desc_entry.get_text().strip() or f"Custom node: {self.node.title}",
            "visibility": visibility
        }


class NodePropertiesDialog(Adw.PreferencesWindow):
    """Dialog Adwaita de propriedades do nó (estilo Settings)"""

    def __init__(self, parent, node):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 500)
        self.set_search_enabled(True)

        self.node = node

        # Criar páginas
        self._create_general_page()
        self._create_code_page()
        self._create_ports_page()
        self._create_info_page()

        # Botão Apply no header
        self.connect("close-request", self._on_close_request)

    def _on_close_request(self, window):
        """Chamado ao fechar janela"""
        # Aplicar mudanças automaticamente
        if hasattr(self, 'on_apply_callback'):
            self.on_apply_callback(self.get_properties())
        return False  # Permite fechar
    
    def _create_general_page(self):
        """Cria página de propriedades gerais com PreferencesGroup"""
        page = Adw.PreferencesPage()
        page.set_title("General")
        page.set_icon_name("emblem-system-symbolic")

        # Group: Node Settings
        group = Adw.PreferencesGroup()
        group.set_title("Node Settings")
        group.set_description("Basic node configuration")

        # Nome
        name_row = Adw.EntryRow()
        name_row.set_title("Name")
        name_row.set_text(self.node.title)
        self.name_entry = name_row
        group.add(name_row)

        # Número de inputs (SpinRow)
        inputs_row = Adw.SpinRow.new_with_range(0, 10, 1)
        inputs_row.set_title("Input Ports")
        inputs_row.set_subtitle("Number of input connections")
        inputs_row.set_value(self.node.num_inputs)
        self.inputs_spin = inputs_row
        group.add(inputs_row)

        # Número de outputs
        outputs_row = Adw.SpinRow.new_with_range(0, 10, 1)
        outputs_row.set_title("Output Ports")
        outputs_row.set_subtitle("Number of output connections")
        outputs_row.set_value(self.node.num_outputs)
        self.outputs_spin = outputs_row
        group.add(outputs_row)

        page.add(group)
        self.add(page)
    
    def _create_code_page(self):
        """Cria página de edição de código"""
        page = Adw.PreferencesPage()
        page.set_title("Code")
        page.set_icon_name("text-x-python-symbolic")

        group = Adw.PreferencesGroup()
        group.set_title("Python Code")
        group.set_description("Return values as tuple: return (output1, output2, ...)")

        # Editor em um box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(300)

        self.code_view = GtkSource.View()
        self.code_buffer = self.code_view.get_buffer()

        # Configurações do editor
        self.code_view.set_show_line_numbers(True)
        self.code_view.set_highlight_current_line(True)
        self.code_view.set_auto_indent(True)
        self.code_view.set_indent_on_tab(True)
        self.code_view.set_tab_width(4)
        self.code_view.set_insert_spaces_instead_of_tabs(True)
        self.code_view.set_monospace(True)
        self.code_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.code_view.set_top_margin(12)
        self.code_view.set_bottom_margin(12)
        self.code_view.set_left_margin(12)
        self.code_view.set_right_margin(12)

        # Configurar linguagem Python
        lang_manager = GtkSource.LanguageManager.get_default()
        python_lang = lang_manager.get_language('python3')
        self.code_buffer.set_language(python_lang)

        # Configurar style scheme
        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme = style_manager.get_scheme('Adwaita-dark')
        if scheme is None:
            scheme = style_manager.get_scheme('classic')
        if scheme:
            self.code_buffer.set_style_scheme(scheme)

        self.code_buffer.set_text(self.node.code)

        scrolled.set_child(self.code_view)
        box.append(scrolled)

        # Adicionar box como child do grupo usando ActionRow
        row = Adw.ActionRow()
        row.set_child(box)
        group.add(row)

        page.add(group)
        self.add(page)

    def _create_ports_page(self):
        """Cria página de configuração de portas e tipos"""
        page = Adw.PreferencesPage()
        page.set_title("Ports")
        page.set_icon_name("network-wired-symbolic")

        # Tipos disponíveis
        available_types = ['any', 'int', 'float', 'str', 'list', 'dict', 'dataframe', 'array', 'figure']

        # Group: Input Ports
        input_group = Adw.PreferencesGroup()
        input_group.set_title("Input Ports")
        input_group.set_description("Configure types for input ports")

        self.input_type_combos = []
        for i in range(self.node.num_inputs):
            row = Adw.ComboRow()
            row.set_title(f"Input Port {i}")

            # Criar string list com tipos
            string_list = Gtk.StringList()
            for t in available_types:
                string_list.append(t)
            row.set_model(string_list)

            # Selecionar tipo atual
            current_type = self.node.input_types[i] if i < len(self.node.input_types) else 'any'
            try:
                idx = available_types.index(current_type)
                row.set_selected(idx)
            except ValueError:
                row.set_selected(0)  # Default: any

            self.input_type_combos.append(row)
            input_group.add(row)

        page.add(input_group)

        # Group: Output Ports
        output_group = Adw.PreferencesGroup()
        output_group.set_title("Output Ports")
        output_group.set_description("Configure types for output ports")

        self.output_type_combos = []
        for i in range(self.node.num_outputs):
            row = Adw.ComboRow()
            row.set_title(f"Output Port {i}")

            # Criar string list com tipos
            string_list = Gtk.StringList()
            for t in available_types:
                string_list.append(t)
            row.set_model(string_list)

            # Selecionar tipo atual
            current_type = self.node.output_types[i] if i < len(self.node.output_types) else 'any'
            try:
                idx = available_types.index(current_type)
                row.set_selected(idx)
            except ValueError:
                row.set_selected(0)  # Default: any

            self.output_type_combos.append(row)
            output_group.add(row)

        page.add(output_group)

        self.add(page)
        self.available_types = available_types  # Guardar para get_properties

    def _create_info_page(self):
        """Cria página de informações e metadata"""
        page = Adw.PreferencesPage()
        page.set_title("Info")
        page.set_icon_name("info-symbolic")

        # Group: Node Info
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Node Information")

        id_row = Adw.ActionRow()
        id_row.set_title("Node ID")
        id_row.set_subtitle(str(self.node.id))
        info_group.add(id_row)

        pos_row = Adw.ActionRow()
        pos_row.set_title("Position")
        pos_row.set_subtitle(f"({self.node.x:.0f}, {self.node.y:.0f})")
        info_group.add(pos_row)

        page.add(info_group)

        # Group: Metadata
        meta_group = Adw.PreferencesGroup()
        meta_group.set_title("Metadata")
        meta_group.set_description("Professional node metadata for library")

        # Descrição
        desc_row = Adw.EntryRow()
        desc_row.set_title("Description")
        desc_row.set_text(self.node.description)
        self.desc_entry = desc_row
        meta_group.add(desc_row)

        # Autor
        author_row = Adw.EntryRow()
        author_row.set_title("Author")
        author_row.set_text(self.node.author)
        self.author_entry = author_row
        meta_group.add(author_row)

        # Versão
        version_row = Adw.EntryRow()
        version_row.set_title("Version")
        version_row.set_text(self.node.version)
        self.version_entry = version_row
        meta_group.add(version_row)

        # Tags
        tags_row = Adw.EntryRow()
        tags_row.set_title("Tags")
        tags_row.set_text(", ".join(self.node.tags))
        self.tags_entry = tags_row
        meta_group.add(tags_row)

        # Categoria
        category_row = Adw.EntryRow()
        category_row.set_title("Category")
        category_row.set_text(self.node.category)
        self.category_entry = category_row
        meta_group.add(category_row)

        page.add(meta_group)

        # Group: Library Settings
        library_group = Adw.PreferencesGroup()
        library_group.set_title("Library Settings")
        library_group.set_description("Configure how this node is saved in the library")

        # Visibilidade
        visibility_row = Adw.ComboRow()
        visibility_row.set_title("Visibility")
        visibility_row.set_subtitle("Private: local only, Public: shareable in repositories")

        # Criar lista de opções
        visibility_list = Gtk.StringList()
        visibility_list.append("Private")
        visibility_list.append("Public")
        visibility_row.set_model(visibility_list)

        # Selecionar visibilidade atual (default: private)
        current_visibility = getattr(self.node, 'visibility', 'private')
        visibility_row.set_selected(0 if current_visibility == 'private' else 1)

        self.visibility_combo = visibility_row
        library_group.add(visibility_row)

        page.add(library_group)

        # Group: Appearance
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title("Appearance")

        # Color picker usando ActionRow com custom child
        color_row = Adw.ActionRow()
        color_row.set_title("Custom Color")
        color_row.set_subtitle("Set a custom header color")

        self.color_button = Gtk.ColorButton()
        if self.node.custom_color:
            rgba = Gdk.RGBA()
            rgba.red, rgba.green, rgba.blue = self.node.custom_color
            rgba.alpha = 1.0
            self.color_button.set_rgba(rgba)

        color_row.add_suffix(self.color_button)
        appearance_group.add(color_row)

        page.add(appearance_group)

        # Group: Statistics (se houver)
        if self.node.total_executions > 0:
            stats_group = Adw.PreferencesGroup()
            stats_group.set_title("Statistics")

            exec_row = Adw.ActionRow()
            exec_row.set_title("Total Executions")
            exec_row.set_subtitle(str(self.node.total_executions))
            stats_group.add(exec_row)

            time_row = Adw.ActionRow()
            time_row.set_title("Last Execution Time")
            time_row.set_subtitle(f"{self.node.last_execution_time*1000:.1f}ms")
            stats_group.add(time_row)

            page.add(stats_group)

        self.add(page)
    
    def get_properties(self):
        """Retorna dicionário com as propriedades editadas"""
        # Pegar código
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        code = self.code_buffer.get_text(start, end, False)

        # Pegar cor customizada
        rgba = self.color_button.get_rgba()
        custom_color = (rgba.red, rgba.green, rgba.blue) if rgba else None

        # Parse tags
        tags_text = self.tags_entry.get_text().strip()
        tags = [t.strip() for t in tags_text.split(',') if t.strip()]

        # Pegar tipos das portas
        input_types = []
        for combo in self.input_type_combos:
            idx = combo.get_selected()
            input_types.append(self.available_types[idx])

        output_types = []
        for combo in self.output_type_combos:
            idx = combo.get_selected()
            output_types.append(self.available_types[idx])

        # Pegar visibilidade
        visibility_index = self.visibility_combo.get_selected()
        visibility = "private" if visibility_index == 0 else "public"

        return {
            "title": self.name_entry.get_text().strip(),
            "num_inputs": int(self.inputs_spin.get_value()),
            "num_outputs": int(self.outputs_spin.get_value()),
            "code": code,
            "description": self.desc_entry.get_text().strip(),
            "author": self.author_entry.get_text().strip(),
            "version": self.version_entry.get_text().strip(),
            "tags": tags,
            "category": self.category_entry.get_text().strip(),
            "custom_color": custom_color,
            "input_types": input_types,
            "output_types": output_types,
            "visibility": visibility
        }

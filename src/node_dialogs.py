#!/usr/bin/env python3
"""
node_dialogs.py - Dialogs para edição de nós
"""

from gi.repository import Gtk, Adw, GtkSource


class CodeEditorDialog(Gtk.Dialog):
    """Dialog para editar código Python do nó"""
    
    def __init__(self, parent, node):
        super().__init__(title=f"Edit Code: {node.title}")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(700, 500)
        
        self.node = node
        
        # Adicionar botões
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Apply", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        
        # Content area
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        # Label de instruções
        instructions = Gtk.Label()
        instructions.set_markup(
            "<b>Python Code</b>\n"
            "<small>Return values as tuple: return (output1, output2, ...)\n"
            "Inputs available as: in0, in1, in2, ...</small>"
        )
        instructions.set_xalign(0)
        content.append(instructions)
        
        # Tentar usar GtkSourceView para syntax highlighting
        try:
            # ScrolledWindow para o editor
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_vexpand(True)
            scrolled.set_hexpand(True)
            
            # SourceView (editor com syntax highlighting)
            self.text_view = GtkSource.View()
            self.text_buffer = self.text_view.get_buffer()
            
            # Configurar Python language
            lang_manager = GtkSource.LanguageManager.get_default()
            python_lang = lang_manager.get_language("python3")
            if python_lang:
                self.text_buffer.set_language(python_lang)
            
            # Configurar scheme (tema)
            style_manager = GtkSource.StyleSchemeManager.get_default()
            scheme = style_manager.get_scheme("classic")  # Tema claro
            if scheme:
                self.text_buffer.set_style_scheme(scheme)
            
            # Configurações do editor
            self.text_view.set_show_line_numbers(True)
            self.text_view.set_auto_indent(True)
            self.text_view.set_indent_width(4)
            self.text_view.set_insert_spaces_instead_of_tabs(True)
            self.text_view.set_monospace(True)
            
        except (ImportError, AttributeError):
            # Fallback para TextView simples se GtkSourceView não disponível
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_vexpand(True)
            scrolled.set_hexpand(True)
            
            self.text_view = Gtk.TextView()
            self.text_buffer = self.text_view.get_buffer()
            self.text_view.set_monospace(True)
            self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        
        # Definir código atual
        self.text_buffer.set_text(node.code)
        
        scrolled.set_child(self.text_view)
        content.append(scrolled)
        
        # Dar foco ao editor
        self.text_view.grab_focus()
    
    def get_code(self):
        """Retorna o código editado"""
        start = self.text_buffer.get_start_iter()
        end = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(start, end, False)


class RenameNodeDialog(Gtk.Dialog):
    """Dialog para renomear nó"""
    
    def __init__(self, parent, node):
        super().__init__(title="Rename Node")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(400, 150)
        
        self.node = node
        
        # Adicionar botões
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Rename", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        
        # Content area
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        # Label
        label = Gtk.Label(label="Node Name:")
        label.set_xalign(0)
        content.append(label)
        
        # Entry
        self.entry = Gtk.Entry()
        self.entry.set_text(node.title)
        self.entry.set_activates_default(True)  # Enter confirma
        content.append(self.entry)
        
        # Dar foco ao entry e selecionar texto
        self.entry.grab_focus()
        self.entry.select_region(0, -1)
    
    def get_name(self):
        """Retorna o novo nome"""
        return self.entry.get_text().strip()


class SaveToLibraryDialog(Gtk.Dialog):
    """Dialog para salvar nó na biblioteca"""

    def __init__(self, parent, node):
        super().__init__(title="Save to Library")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(400, 200)

        self.node = node

        # Adicionar botões
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Save", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        # Content area
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Informação
        info_label = Gtk.Label()
        info_label.set_markup(
            f"<b>Save node as template</b>\n"
            f"<small>Node: {node.title}</small>"
        )
        info_label.set_xalign(0)
        content.append(info_label)

        # Nome do template
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Template Name:")
        name_label.set_size_request(120, -1)
        name_label.set_xalign(0)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(node.title)
        self.name_entry.set_hexpand(True)
        self.name_entry.set_activates_default(True)
        name_box.append(name_label)
        name_box.append(self.name_entry)
        content.append(name_box)

        # Categoria
        category_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        category_label = Gtk.Label(label="Category:")
        category_label.set_size_request(120, -1)
        category_label.set_xalign(0)
        self.category_entry = Gtk.Entry()
        self.category_entry.set_text("My Nodes")
        self.category_entry.set_hexpand(True)
        self.category_entry.set_activates_default(True)
        category_box.append(category_label)
        category_box.append(self.category_entry)
        content.append(category_box)

        # Descrição
        desc_label = Gtk.Label(label="Description (optional):")
        desc_label.set_xalign(0)
        content.append(desc_label)

        self.desc_entry = Gtk.Entry()
        self.desc_entry.set_placeholder_text(f"Custom node: {node.title}")
        self.desc_entry.set_activates_default(True)
        content.append(self.desc_entry)

        # Dar foco ao nome
        self.name_entry.grab_focus()
        self.name_entry.select_region(0, -1)

    def get_info(self):
        """Retorna informações do template"""
        return {
            "name": self.name_entry.get_text().strip() or self.node.title,
            "category": self.category_entry.get_text().strip() or "My Nodes",
            "description": self.desc_entry.get_text().strip() or f"Custom node: {self.node.title}"
        }


class NodePropertiesDialog(Gtk.Dialog):
    """Dialog completo de propriedades do nó"""
    
    def __init__(self, parent, node):
        super().__init__(title=f"Properties: {node.title}")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(500, 400)
        
        self.node = node
        
        # Adicionar botões
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Apply", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        
        # Content area com notebook
        content = self.get_content_area()
        content.set_spacing(0)
        
        notebook = Gtk.Notebook()
        
        # Tab 1: General
        general_page = self._create_general_page()
        notebook.append_page(general_page, Gtk.Label(label="General"))
        
        # Tab 2: Code
        code_page = self._create_code_page()
        notebook.append_page(code_page, Gtk.Label(label="Code"))
        
        # Tab 3: Info
        info_page = self._create_info_page()
        notebook.append_page(info_page, Gtk.Label(label="Info"))
        
        content.append(notebook)
    
    def _create_general_page(self):
        """Cria página de propriedades gerais"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Nome
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_label = Gtk.Label(label="Name:")
        name_label.set_size_request(100, -1)
        name_label.set_xalign(0)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(self.node.title)
        self.name_entry.set_hexpand(True)
        name_box.append(name_label)
        name_box.append(self.name_entry)
        box.append(name_box)
        
        # Número de inputs
        inputs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        inputs_label = Gtk.Label(label="Inputs:")
        inputs_label.set_size_request(100, -1)
        inputs_label.set_xalign(0)
        self.inputs_spin = Gtk.SpinButton()
        self.inputs_spin.set_range(0, 10)
        self.inputs_spin.set_increments(1, 1)
        self.inputs_spin.set_value(self.node.num_inputs)
        inputs_box.append(inputs_label)
        inputs_box.append(self.inputs_spin)
        box.append(inputs_box)
        
        # Número de outputs
        outputs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outputs_label = Gtk.Label(label="Outputs:")
        outputs_label.set_size_request(100, -1)
        outputs_label.set_xalign(0)
        self.outputs_spin = Gtk.SpinButton()
        self.outputs_spin.set_range(0, 10)
        self.outputs_spin.set_increments(1, 1)
        self.outputs_spin.set_value(self.node.num_outputs)
        outputs_box.append(outputs_label)
        outputs_box.append(self.outputs_spin)
        box.append(outputs_box)
        
        return box
    
    def _create_code_page(self):
        """Cria página de edição de código"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Instruções
        instructions = Gtk.Label()
        instructions.set_markup(
            "<small>Return values as tuple: <tt>return (output1, output2, ...)</tt>\n"
            "Inputs available as: <tt>in0, in1, in2, ...</tt></small>"
        )
        instructions.set_xalign(0)
        box.append(instructions)
        
        # Editor
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        
        self.code_view = Gtk.TextView()
        self.code_buffer = self.code_view.get_buffer()
        self.code_view.set_monospace(True)
        self.code_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.code_buffer.set_text(self.node.code)
        
        scrolled.set_child(self.code_view)
        box.append(scrolled)
        
        return box
    
    def _create_info_page(self):
        """Cria página de informações"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # ID
        id_label = Gtk.Label()
        id_label.set_markup(f"<b>Node ID:</b>\n<tt>{self.node.id}</tt>")
        id_label.set_xalign(0)
        id_label.set_selectable(True)
        box.append(id_label)
        
        # Posição
        pos_label = Gtk.Label()
        pos_label.set_markup(f"<b>Position:</b>\n({self.node.x:.0f}, {self.node.y:.0f})")
        pos_label.set_xalign(0)
        box.append(pos_label)
        
        return box
    
    def get_properties(self):
        """Retorna dicionário com as propriedades editadas"""
        # Pegar código
        start = self.code_buffer.get_start_iter()
        end = self.code_buffer.get_end_iter()
        code = self.code_buffer.get_text(start, end, False)
        
        return {
            "title": self.name_entry.get_text().strip(),
            "num_inputs": int(self.inputs_spin.get_value()),
            "num_outputs": int(self.outputs_spin.get_value()),
            "code": code
        }

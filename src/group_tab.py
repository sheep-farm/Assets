#!/usr/bin/env python3
"""
group_tab.py - Aba separada para editar conteúdo interno de um GroupNode
"""

from gi.repository import Gtk, Adw, Gio
from pathlib import Path

from .canvas import AssetsCanvas
from .input_node import InputNode
from .output_node import OutputNode


class GroupTab:
    """
    Representa uma aba para editar o sub-grafo interno de um GroupNode.

    Características:
    - Canvas dedicado ao sub-grafo
    - Toolbar com ações específicas (Add Input/Output, voltar ao pai)
    - Sincronização automática com o GroupNode
    """

    def __init__(self, group_node, parent_window):
        self.group_node = group_node
        self.parent_window = parent_window
        self.is_modified = False

        # Container principal
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_container.set_vexpand(True)
        self.main_container.set_hexpand(True)

        # Criar toolbar
        self._create_toolbar()

        # Criar canvas para o sub-grafo
        self.canvas = AssetsCanvas()
        self.canvas.group_tab = self  # Referência inversa

        # Carregar nodes internos do GroupNode no canvas
        self._load_inner_graph()

        # Colocar canvas em ScrolledWindow
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_vexpand(True)
        self.scrolled_window.set_hexpand(True)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.set_child(self.canvas)

        # Adicionar ao container
        self.main_container.append(self.scrolled_window)

    def _create_toolbar(self):
        """Cria toolbar com ações específicas do GroupNode"""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.set_margin_start(6)
        toolbar.set_margin_end(6)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)
        toolbar.add_css_class("toolbar")

        # Botão: Voltar ao projeto pai
        back_btn = Gtk.Button(label="← Back to Parent")
        back_btn.set_tooltip_text("Voltar ao projeto principal")
        back_btn.connect("clicked", self._on_back_to_parent)
        toolbar.append(back_btn)

        # Separator
        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Botão: Add Input Port
        add_input_btn = Gtk.Button(label="+ Input Port")
        add_input_btn.set_tooltip_text("Adiciona porta de entrada ao GroupNode")
        add_input_btn.connect("clicked", self._on_add_input_port)
        toolbar.append(add_input_btn)

        # Botão: Add Output Port
        add_output_btn = Gtk.Button(label="+ Output Port")
        add_output_btn.set_tooltip_text("Adiciona porta de saída ao GroupNode")
        add_output_btn.connect("clicked", self._on_add_output_port)
        toolbar.append(add_output_btn)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        # Label de status
        status_label = Gtk.Label(label=f"Editing: {self.group_node.title}")
        status_label.add_css_class("dim-label")
        toolbar.append(status_label)

        self.main_container.append(toolbar)

    def _load_inner_graph(self):
        """Carrega nodes internos do GroupNode para o canvas"""
        # Limpar canvas
        self.canvas.nodes.clear()
        self.canvas.connections.clear()

        # Carregar nodes internos
        for node in self.group_node.inner_nodes:
            self.canvas.nodes.append(node)

        # Carregar conexões internas
        for conn in self.group_node.inner_connections:
            self.canvas.connections.append(conn)

        print(f"📦 Loaded {len(self.canvas.nodes)} nodes, {len(self.canvas.connections)} connections into GroupTab")

        # Redesenhar
        self.canvas.queue_draw()

    def _save_to_group_node(self):
        """Salva estado atual do canvas de volta para o GroupNode"""
        # Sincronizar nodes
        self.group_node.inner_nodes = self.canvas.nodes.copy()

        # Sincronizar conexões
        self.group_node.inner_connections = self.canvas.connections.copy()

        print(f"💾 Saved GroupTab changes to {self.group_node.title}")

        # Marcar como modificado
        self.is_modified = True

    def _on_back_to_parent(self, button):
        """Handler: Voltar ao projeto pai"""
        # Salvar mudanças antes de voltar
        self._save_to_group_node()

        # Pedir à janela para fechar esta aba
        if hasattr(self.parent_window, 'close_group_tab'):
            self.parent_window.close_group_tab(self)

    def _on_add_input_port(self, button):
        """Handler: Adiciona porta de entrada ao InputNode"""
        if not self.group_node.input_node:
            # Criar InputNode se não existir
            input_node = InputNode(50, 100, num_outputs=1)
            self.group_node.set_input_node(input_node)
            self.canvas.nodes.append(input_node)
            print("✓ Created InputNode")
        else:
            # Adicionar porta ao InputNode existente
            input_node = self.group_node.input_node
            input_node.num_outputs += 1
            input_node.output_types.append('any')
            input_node.output_docs.append(f"Input {input_node.num_outputs - 1}")

            # Atualizar GroupNode
            self.group_node.set_input_node(input_node)

            print(f"✓ Added input port (total: {input_node.num_outputs})")

        # Salvar e redesenhar
        self._save_to_group_node()
        self.canvas.queue_draw()

    def _on_add_output_port(self, button):
        """Handler: Adiciona porta de saída ao OutputNode"""
        if not self.group_node.output_node:
            # Criar OutputNode se não existir
            output_node = OutputNode(500, 100, num_inputs=1)
            self.group_node.set_output_node(output_node)
            self.canvas.nodes.append(output_node)
            print("✓ Created OutputNode")
        else:
            # Adicionar porta ao OutputNode existente
            output_node = self.group_node.output_node
            output_node.num_inputs += 1
            output_node.input_types.append('any')
            output_node.input_docs.append(f"Output {output_node.num_inputs - 1}")

            # Atualizar GroupNode
            self.group_node.set_output_node(output_node)

            print(f"✓ Added output port (total: {output_node.num_inputs})")

        # Salvar e redesenhar
        self._save_to_group_node()
        self.canvas.queue_draw()

    def get_widget(self):
        """Retorna widget principal da aba"""
        return self.main_container

    def get_title(self):
        """Retorna título da aba"""
        return f"Group: {self.group_node.title}"

    def get_tooltip(self):
        """Retorna tooltip da aba"""
        return f"Editing GroupNode: {self.group_node.title} ({len(self.group_node.inner_nodes)} nodes)"

    def on_closing(self):
        """Chamado quando aba está prestes a fechar"""
        # Salvar mudanças finais
        self._save_to_group_node()
        print(f"🔒 Closed GroupTab for {self.group_node.title}")

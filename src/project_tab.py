"""
project_tab.py - Encapsula um projeto (aba) completo
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

        # Container principal - box vertical com toolbar + paned
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_container.set_vexpand(True)
        self.main_container.set_hexpand(True)

        # Criar canvas
        self.canvas = AssetsCanvas()

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

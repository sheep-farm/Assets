#!/usr/bin/env python3
"""
output_panel.py - Sistema de visualização de outputs
"""

from gi.repository import Gtk, Gdk, Pango
import json


class OutputPanel(Gtk.Box):
    """Painel principal de outputs com tabs"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        # Header com controles
        self.header = self._create_header()
        self.append(self.header)

        # Separator
        self.append(Gtk.Separator())

        # Notebook com tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # Criar tabs
        self.console_tab = ConsoleTab()
        self.plots_tab = PlotsTab()
        self.tables_tab = TablesTab()
        self.data_tab = DataTab()

        # Adicionar ao notebook
        self.notebook.append_page(self.console_tab, self._create_tab_label("🖥️ Console", 0))
        self.notebook.append_page(self.plots_tab, self._create_tab_label("📊 Plots", 0))
        self.notebook.append_page(self.tables_tab, self._create_tab_label("📋 Tables", 0))
        self.notebook.append_page(self.data_tab, self._create_tab_label("📦 Data", 0))

        self.append(self.notebook)

        # Contadores
        self.counts = {"console": 0, "plots": 0, "tables": 0, "data": 0}

    def _create_header(self):
        """Cria header com botões"""
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_top(6)
        header.set_margin_bottom(6)
        header.set_margin_start(12)
        header.set_margin_end(12)

        # Label
        label = Gtk.Label()
        label.set_markup("<b>📊 Output Panel</b>")
        label.set_xalign(0)
        header.append(label)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        # Botão Clear
        clear_btn = Gtk.Button(label="Clear All")
        clear_btn.connect("clicked", lambda b: self.clear_all())
        header.append(clear_btn)

        return header

    def _create_tab_label(self, text, count):
        """Cria label do tab com contador"""
        if count > 0:
            return Gtk.Label(label=f"{text} ({count})")
        return Gtk.Label(label=text)

    def _update_tab_label(self, tab_index, icon, name, count):
        """Atualiza label do tab com contador"""
        label = self._create_tab_label(f"{icon} {name}", count)
        self.notebook.set_tab_label(
            self.notebook.get_nth_page(tab_index),
            label
        )

    def clear_all(self):
        """Limpa todos os tabs"""
        self.console_tab.clear()
        self.plots_tab.clear()
        self.tables_tab.clear()
        self.data_tab.clear()

        # Reset contadores
        self.counts = {"console": 0, "plots": 0, "tables": 0, "data": 0}
        self._update_tab_label(0, "🖥️", "Console", 0)
        self._update_tab_label(1, "📊", "Plots", 0)
        self._update_tab_label(2, "📋", "Tables", 0)
        self._update_tab_label(3, "📦", "Data", 0)

        print("✓ Output panel cleared")

    def add_console(self, text):
        """Adiciona texto ao console"""
        self.console_tab.add_text(text)
        self.counts["console"] += 1
        self._update_tab_label(0, "🖥️", "Console", self.counts["console"])

    def add_plot(self, figure, title="Plot"):
        """Adiciona plot matplotlib"""
        self.plots_tab.add_plot(figure, title)
        self.counts["plots"] += 1
        self._update_tab_label(1, "📊", "Plots", self.counts["plots"])
        # Mudar para tab de plots
        self.notebook.set_current_page(1)

    def add_table(self, dataframe, title="Table"):
        """Adiciona tabela (DataFrame)"""
        self.tables_tab.add_table(dataframe, title)
        self.counts["tables"] += 1
        self._update_tab_label(2, "📋", "Tables", self.counts["tables"])
        # Mudar para tab de tables
        self.notebook.set_current_page(2)

    def add_data(self, data, title="Data"):
        """Adiciona dados estruturados (dict/list)"""
        self.data_tab.add_data(data, title)
        self.counts["data"] += 1
        self._update_tab_label(3, "📦", "Data", self.counts["data"])
        # Mudar para tab de data
        self.notebook.set_current_page(3)


class ConsoleTab(Gtk.ScrolledWindow):
    """Tab de console/logs"""

    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)

        # TextView
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_margin_top(12)
        self.text_view.set_margin_bottom(12)
        self.text_view.set_margin_start(12)
        self.text_view.set_margin_end(12)

        self.buffer = self.text_view.get_buffer()

        self.set_child(self.text_view)

    def clear(self):
        """Limpa console"""
        self.buffer.set_text("")

    def add_text(self, text):
        """Adiciona texto ao console"""
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, text)

        # Scroll para o final
        self.text_view.scroll_to_iter(self.buffer.get_end_iter(), 0.0, False, 0.0, 0.0)


class PlotsTab(Gtk.ScrolledWindow):
    """Tab de plots matplotlib"""

    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)

        # Box vertical para múltiplos plots
        self.plots_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.plots_box.set_margin_top(12)
        self.plots_box.set_margin_bottom(12)
        self.plots_box.set_margin_start(12)
        self.plots_box.set_margin_end(12)

        self.set_child(self.plots_box)

        # Lista de figures (para cleanup)
        self.figures = []

    def clear(self):
        """Limpa todos os plots"""
        # Remover todos os widgets
        while child := self.plots_box.get_first_child():
            self.plots_box.remove(child)

        # Limpar figures
        import matplotlib.pyplot as plt
        for fig in self.figures:
            plt.close(fig)
        self.figures.clear()

    def add_plot(self, figure, title="Plot"):
        """Adiciona matplotlib figure"""
        try:
            from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg

            # Frame para o plot
            frame = Gtk.Frame()
            frame.set_label(title)

            # Canvas matplotlib
            canvas = FigureCanvasGTK4Agg(figure)
            canvas.set_size_request(800, 400)

            frame.set_child(canvas)
            self.plots_box.append(frame)

            # Guardar figure
            self.figures.append(figure)

            print(f"✓ Plot adicionado: {title}")

        except ImportError:
            print("❌ Matplotlib GTK4 backend não disponível")
            print("   Instale: pip install matplotlib")


class TablesTab(Gtk.ScrolledWindow):
    """Tab de tabelas (DataFrames)"""

    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)

        # Box vertical para múltiplas tabelas
        self.tables_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.tables_box.set_margin_top(12)
        self.tables_box.set_margin_bottom(12)
        self.tables_box.set_margin_start(12)
        self.tables_box.set_margin_end(12)

        self.set_child(self.tables_box)

    def clear(self):
        """Limpa todas as tabelas"""
        while child := self.tables_box.get_first_child():
            self.tables_box.remove(child)

    def add_table(self, dataframe, title="Table"):
        """Adiciona pandas DataFrame"""
        try:
            import pandas as pd

            # Frame para a tabela
            frame = Gtk.Frame()
            frame.set_label(title)

            # ScrolledWindow interno
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_size_request(-1, 300)

            # TextView com tabela
            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_monospace(True)
            text_view.set_wrap_mode(Gtk.WrapMode.NONE)

            buffer = text_view.get_buffer()

            # Formatar DataFrame como texto
            table_str = dataframe.to_string()
            buffer.set_text(table_str)

            scrolled.set_child(text_view)
            frame.set_child(scrolled)

            self.tables_box.append(frame)

            print(f"✓ Tabela adicionada: {title} (shape: {dataframe.shape})")

        except Exception as e:
            print(f"❌ Erro ao adicionar tabela: {e}")


class DataTab(Gtk.ScrolledWindow):
    """Tab de dados estruturados (dict/JSON)"""

    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)

        # TextView para JSON
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_margin_top(12)
        self.text_view.set_margin_bottom(12)
        self.text_view.set_margin_start(12)
        self.text_view.set_margin_end(12)

        self.buffer = self.text_view.get_buffer()

        self.set_child(self.text_view)

    def clear(self):
        """Limpa dados"""
        self.buffer.set_text("")

    def add_data(self, data, title="Data"):
        """Adiciona dados estruturados"""
        try:
            # Pegar texto atual
            start = self.buffer.get_start_iter()
            end = self.buffer.get_end_iter()
            current_text = self.buffer.get_text(start, end, False)

            # Adicionar separador se já tem conteúdo
            if current_text:
                current_text += "\n\n" + "="*60 + "\n\n"

            # Adicionar título
            current_text += f"=== {title} ===\n"

            # Formatar dados como JSON
            json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            current_text += json_str + "\n"

            # Atualizar buffer
            self.buffer.set_text(current_text)

            # Scroll para o final
            self.text_view.scroll_to_iter(self.buffer.get_end_iter(), 0.0, False, 0.0, 0.0)

            print(f"✓ Dados adicionados: {title}")

        except Exception as e:
            print(f"❌ Erro ao adicionar dados: {e}")

#!/usr/bin/env python3
"""
output_panel.py - Sistema de visualização de outputs
Agora com sub-abas por item dentro de Plots/Tables/Data.
O rótulo da sub-aba é o 'title' passado (inclua o nome do nó no title).
"""

from gi.repository import Gtk, Gdk, Pango
import json
import sys


class OutputPanel(Gtk.Box):
    """Painel principal de outputs com tabs"""

    def __init__(self, canvas=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        # Armazenar referência ao canvas para dar foco quando esconder
        self.canvas = canvas

        # Header com controles
        self.header = self._create_header()
        self.append(self.header)

        # Separator
        self.separator = Gtk.Separator()
        self.append(self.separator)

        # Notebook com tabs (globais)
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # Estado de visibilidade
        self.is_visible = True
        self.saved_height = None  # Altura salva antes de ocultar

        # Criar tabs
        self.console_tab = ConsoleTab()
        self.plots_tab = PlotsTab()    # agora usa sub-notebook
        self.tables_tab = TablesTab()  # agora usa sub-notebook
        self.data_tab = DataTab()      # agora usa sub-notebook

        # Adicionar ao notebook
        self.notebook.append_page(self.console_tab, self._create_tab_label("🖥️ Console", 0))
        self.notebook.append_page(self.plots_tab,   self._create_tab_label("📊 Plots",   0))
        self.notebook.append_page(self.tables_tab,  self._create_tab_label("📋 Tables",  0))
        self.notebook.append_page(self.data_tab,    self._create_tab_label("📦 Data",    0))

        self.append(self.notebook)

        # Contadores
        self.counts = {"console": 0, "plots": 0, "tables": 0, "data": 0}

    def _create_header(self):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_top(6)
        header.set_margin_bottom(6)
        header.set_margin_start(12)
        header.set_margin_end(12)

        # Botão de Show/Hide com o título
        self.toggle_btn = Gtk.Button()
        self.toggle_btn.set_has_frame(False)
        self.toggle_btn.set_can_focus(False)  # Não recebe foco
        title_label = Gtk.Label()
        title_label.set_markup("<b>📊 Output Panel</b>")
        title_label.set_xalign(0)
        self.toggle_btn.set_child(title_label)
        self.toggle_btn.connect("clicked", self._on_toggle_visibility)
        header.append(self.toggle_btn)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        return header

    def _create_tab_label(self, text, count):
        if count > 0:
            return Gtk.Label(label=f"{text} ({count})")
        return Gtk.Label(label=text)

    def _update_tab_label(self, tab_index, icon, name, count):
        label = self._create_tab_label(f"{icon} {name}", count)
        self.notebook.set_tab_label(self.notebook.get_nth_page(tab_index), label)

    def _on_toggle_visibility(self, button):
        """Toggle show/hide do notebook de outputs"""
        # Encontrar o Paned pai
        parent = self.get_parent()
        while parent and not isinstance(parent, Gtk.Paned):
            parent = parent.get_parent()

        if not parent:
            return

        self.is_visible = not self.is_visible

        if self.is_visible:
            # Mostrar: restaurar altura salva
            self.notebook.set_visible(True)
            self.separator.set_visible(True)
            if self.saved_height is not None:
                parent.set_position(self.saved_height)
        else:
            # Ocultar: salvar altura atual e minimizar
            self.saved_height = parent.get_position()
            self.notebook.set_visible(False)
            self.separator.set_visible(False)
            # Mover divisor para o final (minimizar output panel)
            parent.set_position(parent.get_allocated_height() - 40)
            # Dar foco ao canvas
            if self.canvas:
                self.canvas.grab_focus()

    def clear_all(self):
        """Limpa todos os outputs (chamado ao clicar em Run)"""
        self.console_tab.clear()
        self.plots_tab.clear()
        self.tables_tab.clear()
        self.data_tab.clear()
        self.counts = {"console": 0, "plots": 0, "tables": 0, "data": 0}
        self._update_tab_label(0, "🖥️", "Console", 0)
        self._update_tab_label(1, "📊", "Plots", 0)
        self._update_tab_label(2, "📋", "Tables", 0)
        self._update_tab_label(3, "📦", "Data", 0)

    # ===== API pública (sem mudar assinaturas) =====

    def add_console(self, text):
        self.console_tab.add_text(text)
        self.counts["console"] += 1
        self._update_tab_label(0, "🖥️", "Console", self.counts["console"])

    def add_plot(self, figure, title="Plot"):
        self.plots_tab.add_plot(figure, title)
        self.counts["plots"] = self.plots_tab.count()  # baseado nas sub-abas
        self._update_tab_label(1, "📊", "Plots", self.counts["plots"])
        self.notebook.set_current_page(1)

    def add_table(self, dataframe, title="Table"):
        self.tables_tab.add_table(dataframe, title)
        self.counts["tables"] = self.tables_tab.count()
        self._update_tab_label(2, "📋", "Tables", self.counts["tables"])
        self.notebook.set_current_page(2)

    def add_data(self, data, title="Data"):
        self.data_tab.add_data(data, title)
        self.counts["data"] = self.data_tab.count()
        self._update_tab_label(3, "📦", "Data", self.counts["data"])
        self.notebook.set_current_page(3)


# ===================== Console =====================

class ConsoleTab(Gtk.ScrolledWindow):
    """Tab de console/logs"""

    def __init__(self):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)

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
        self.buffer.set_text("")

    def add_text(self, text):
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, text)
        self.text_view.scroll_to_iter(self.buffer.get_end_iter(), 0.0, False, 0.0, 0.0)


# ===================== Plots =====================

class PlotsTab(Gtk.Box):
    """
    Antes: scroller com frames empilhados
    Agora: sub-notebook, cada plot vira uma sub-aba rotulada por 'title'
    (inclua o nome do nó no title).
    """

    MAX_PLOTS = 50  # Limite de plots para evitar consumo excessivo de memória

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self.sub = Gtk.Notebook()
        self.sub.set_scrollable(True)
        self.append(self.sub)

        self._figures = []  # para cleanup

    def count(self) -> int:
        return self.sub.get_n_pages()

    def clear(self):
        while self.sub.get_n_pages() > 0:
            page = self.sub.get_nth_page(0)
            self.sub.remove_page(0)
        # fechar figures
        try:
            import matplotlib.pyplot as plt
            for fig in self._figures:
                plt.close(fig)
        except Exception:
            pass
        self._figures.clear()

    def add_plot(self, figure, title="Plot"):
        try:
            from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg
        except ImportError:
            print("❌ Matplotlib GTK4 backend não disponível. Instale: pip install matplotlib", file=sys.__stdout__)
            return

        # Verificar limite de plots
        if self.sub.get_n_pages() >= self.MAX_PLOTS:
            print(f"⚠️  Limite de {self.MAX_PLOTS} plots atingido. Removendo o mais antigo.", file=sys.__stdout__)
            # Remover primeiro plot (mais antigo)
            self.sub.remove_page(0)
            # Fechar e remover figura
            if self._figures:
                try:
                    import matplotlib.pyplot as plt
                    plt.close(self._figures[0])
                except:
                    pass
                self._figures.pop(0)

        # Canvas do matplotlib direto na sub-aba
        canvas = FigureCanvasGTK4Agg(figure)
        canvas.set_size_request(800, 400)
        self._figures.append(figure)

        # Colocar dentro de um ScrolledWindow para segurança
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(canvas)

        tab_label = Gtk.Label(label=title or "Plot")
        self.sub.append_page(scrolled, tab_label)
        self.sub.set_current_page(self.sub.get_n_pages() - 1)
        print(f"✓ Plot em aba: {title}", file=sys.__stdout__)


# ===================== Tables =====================

class TablesTab(Gtk.Box):
    """
    Antes: scroller com frames empilhados
    Agora: sub-notebook, cada DataFrame vira uma sub-aba rotulada por 'title'
    (inclua o nome do nó no title).
    """

    MAX_TABLES = 50  # Limite de tabelas para evitar consumo excessivo de memória

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self.sub = Gtk.Notebook()
        self.sub.set_scrollable(True)
        self.append(self.sub)

    def count(self) -> int:
        return self.sub.get_n_pages()

    def clear(self):
        while self.sub.get_n_pages() > 0:
            self.sub.remove_page(0)

    def add_table(self, dataframe, title="Table"):
        # Verificar limite de tabelas
        if self.sub.get_n_pages() >= self.MAX_TABLES:
            print(f"⚠️  Limite de {self.MAX_TABLES} tabelas atingido. Removendo a mais antiga.", file=sys.__stdout__)
            # Remover primeira tabela (mais antiga)
            self.sub.remove_page(0)

        # Render simples como texto monoespaçado
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        text_view.set_margin_top(6)
        text_view.set_margin_bottom(6)
        text_view.set_margin_start(6)
        text_view.set_margin_end(6)

        buf = text_view.get_buffer()
        try:
            table_str = dataframe.to_string()
        except Exception as e:
            table_str = f"[erro ao renderizar DataFrame: {e}]"
        buf.set_text(table_str)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)   # ocupa horizontalmente
        scrolled.set_vexpand(True)   # ocupa verticalmente
        #scrolled.set_size_request(-1, 320)
        scrolled.set_child(text_view)

        tab_label = Gtk.Label(label=title or "Table")
        self.sub.append_page(scrolled, tab_label)
        self.sub.set_current_page(self.sub.get_n_pages() - 1)
        print(f"✓ Tabela em aba: {title}", file=sys.__stdout__)


# ===================== Data (JSON) =====================

class DataTab(Gtk.Box):
    """
    Antes: um único TextView concatenando dados
    Agora: sub-notebook, cada bloco de dados vira uma sub-aba rotulada por 'title'
    (inclua o nome do nó no title).
    """

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self.sub = Gtk.Notebook()
        self.sub.set_scrollable(True)
        self.append(self.sub)

    def count(self) -> int:
        return self.sub.get_n_pages()

    def clear(self):
        while self.sub.get_n_pages() > 0:
            self.sub.remove_page(0)

    def add_data(self, data, title="Data"):
        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_margin_top(6)
        text_view.set_margin_bottom(6)
        text_view.set_margin_start(6)
        text_view.set_margin_end(6)

        buf = text_view.get_buffer()
        try:
            json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            json_str = f"[erro ao serializar dados: {e}]"
        buf.set_text(json_str)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(-1, 260)
        scrolled.set_child(text_view)

        tab_label = Gtk.Label(label=title or "Data")
        self.sub.append_page(scrolled, tab_label)
        self.sub.set_current_page(self.sub.get_n_pages() - 1)
        print(f"✓ Dados em aba: {title}", file=sys.__stdout__)

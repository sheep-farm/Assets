#!/usr/bin/env python3
"""
preferences_dialog.py - Diálogo de preferências da aplicação
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio


class PreferencesDialog(Adw.PreferencesWindow):
    """Diálogo de preferências com abas para configurações da aplicação"""

    def __init__(self, parent):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Preferences")

        # Inicializar GSettings
        try:
            from pathlib import Path
            import os
            # Para desenvolvimento: usar schema local se não instalado
            schema_dir = Path(__file__).parent.parent / "data"
            if schema_dir.exists():
                os.environ['GSETTINGS_SCHEMA_DIR'] = str(schema_dir)

            self.settings = Gio.Settings.new("com.github.sheep.farm.assets")
        except Exception as e:
            print(f"Error: Could not load GSettings: {e}")
            # Mostrar erro ao usuário
            from gi.repository import Gtk
            dialog = Gtk.MessageDialog(
                transient_for=parent,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Settings Error",
            )
            dialog.format_secondary_text(
                f"Could not load application settings:\n{e}\n\n"
                "Please rebuild the application with:\n"
                "glib-compile-schemas data/"
            )
            dialog.present()
            return

        # Criar páginas
        self._create_style_page()

    def _create_style_page(self):
        """Cria a página de configurações de estilo visual"""
        page = Adw.PreferencesPage()
        page.set_title("Style")
        page.set_icon_name("applications-graphics-symbolic")

        # Grupo: Canvas Background
        canvas_group = Adw.PreferencesGroup()
        canvas_group.set_title("Canvas Background")
        canvas_group.set_description("Configure background and grid colors")

        # Cor de fundo do canvas
        bg_color_row = self._create_color_row(
            "Background Color",
            "Main canvas background color",
            "canvas-bg-color"
        )
        canvas_group.add(bg_color_row)

        # Cor da grid fina
        fine_grid_row = self._create_color_row(
            "Fine Grid Color",
            "Small grid lines color",
            "fine-grid-color"
        )
        canvas_group.add(fine_grid_row)

        # Cor da grid grossa
        coarse_grid_row = self._create_color_row(
            "Coarse Grid Color",
            "Large grid lines color",
            "coarse-grid-color"
        )
        canvas_group.add(coarse_grid_row)

        page.add(canvas_group)

        # Grupo: Nodes
        nodes_group = Adw.PreferencesGroup()
        nodes_group.set_title("Nodes")
        nodes_group.set_description("Configure node appearance")

        # Cor do corpo do nó
        node_body_row = self._create_color_row(
            "Node Body Color",
            "Background color of node body",
            "node-body-color"
        )
        nodes_group.add(node_body_row)

        # Cor da borda do nó
        node_border_row = self._create_color_row(
            "Node Border Color",
            "Color of node borders",
            "node-border-color"
        )
        nodes_group.add(node_border_row)

        # Cor do contorno quando selecionado
        node_selection_row = self._create_color_row(
            "Node Selection Color",
            "Outline color when node is selected",
            "node-selection-color"
        )
        nodes_group.add(node_selection_row)

        # Cor durante execução
        node_running_row = self._create_color_row(
            "Node Running Color",
            "Border color when node is executing",
            "node-running-color"
        )
        nodes_group.add(node_running_row)

        page.add(nodes_group)

        # Grupo: Connections
        connections_group = Adw.PreferencesGroup()
        connections_group.set_title("Connections")
        connections_group.set_description("Configure connection line appearance")

        # Cor da conexão em criação
        conn_creating_row = self._create_color_row(
            "Creating Connection Color",
            "Color when dragging to create connection",
            "connection-creating-color"
        )
        connections_group.add(conn_creating_row)

        # Cor da conexão estabelecida
        conn_normal_row = self._create_color_row(
            "Connected Line Color",
            "Color of established connections",
            "connection-normal-color"
        )
        connections_group.add(conn_normal_row)

        # Cor da conexão selecionada
        conn_selected_row = self._create_color_row(
            "Selected Connection Color",
            "Color when connection is selected",
            "connection-selected-color"
        )
        connections_group.add(conn_selected_row)

        page.add(connections_group)

        # Grupo: Selection
        selection_group = Adw.PreferencesGroup()
        selection_group.set_title("Selection Rectangle")
        selection_group.set_description("Configure multi-selection appearance")

        # Cor do retângulo de seleção
        selection_fill_row = self._create_color_row(
            "Selection Fill Color",
            "Fill color of selection rectangle",
            "selection-fill-color"
        )
        selection_group.add(selection_fill_row)

        # Opacidade do retângulo
        selection_opacity_row = Adw.SpinRow()
        selection_opacity_row.set_title("Selection Fill Opacity")
        selection_opacity_row.set_subtitle("Transparency of selection rectangle fill")
        adjustment = Gtk.Adjustment(
            value=self.settings.get_double("selection-fill-opacity"),
            lower=0.0,
            upper=1.0,
            step_increment=0.05,
            page_increment=0.1,
            page_size=0
        )
        selection_opacity_row.set_adjustment(adjustment)
        selection_opacity_row.set_digits(2)
        adjustment.connect('value-changed', self._on_opacity_changed, "selection-fill-opacity")
        selection_group.add(selection_opacity_row)

        # Cor da borda de seleção
        selection_border_row = self._create_color_row(
            "Selection Border Color",
            "Border color of selection rectangle",
            "selection-border-color"
        )
        selection_group.add(selection_border_row)

        # Opacidade da borda
        selection_border_opacity_row = Adw.SpinRow()
        selection_border_opacity_row.set_title("Selection Border Opacity")
        selection_border_opacity_row.set_subtitle("Transparency of selection rectangle border")
        adjustment2 = Gtk.Adjustment(
            value=self.settings.get_double("selection-border-opacity"),
            lower=0.0,
            upper=1.0,
            step_increment=0.05,
            page_increment=0.1,
            page_size=0
        )
        selection_border_opacity_row.set_adjustment(adjustment2)
        selection_border_opacity_row.set_digits(2)
        adjustment2.connect('value-changed', self._on_opacity_changed, "selection-border-opacity")
        selection_group.add(selection_border_opacity_row)

        page.add(selection_group)

        # Grupo: Focus Mode
        focus_group = Adw.PreferencesGroup()
        focus_group.set_title("Focus Mode")
        focus_group.set_description("Configure node focus and highlighting behavior")

        # Número de níveis de conexão
        focus_depth_row = Adw.SpinRow()
        focus_depth_row.set_title("Focus Depth")
        focus_depth_row.set_subtitle("Connection levels to highlight (0=only node, 1=direct, 2+=indirect)")
        depth_adjustment = Gtk.Adjustment(
            value=self.settings.get_int("focus-depth"),
            lower=0,
            upper=10,
            step_increment=1,
            page_increment=1,
            page_size=0
        )
        focus_depth_row.set_adjustment(depth_adjustment)
        focus_depth_row.set_digits(0)
        depth_adjustment.connect('value-changed', self._on_depth_changed, "focus-depth")
        focus_group.add(focus_depth_row)

        # Opacidade dos elementos desfocados
        dimming_opacity_row = Adw.SpinRow()
        dimming_opacity_row.set_title("Dimming Opacity")
        dimming_opacity_row.set_subtitle("Opacity of dimmed nodes/connections when not in focus")
        dimming_adjustment = Gtk.Adjustment(
            value=self.settings.get_double("focus-dimming-opacity"),
            lower=0.0,
            upper=1.0,
            step_increment=0.05,
            page_increment=0.1,
            page_size=0
        )
        dimming_opacity_row.set_adjustment(dimming_adjustment)
        dimming_opacity_row.set_digits(2)
        dimming_adjustment.connect('value-changed', self._on_opacity_changed, "focus-dimming-opacity")
        focus_group.add(dimming_opacity_row)

        page.add(focus_group)

        # Adicionar página à janela
        self.add(page)

    def _create_color_row(self, title, subtitle, setting_key):
        """
        Cria uma linha de preferência com seletor de cor

        Args:
            title: Título da configuração
            subtitle: Descrição
            setting_key: Chave GSettings (com hífen)

        Returns:
            Adw.ActionRow configurada
        """
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)

        # Criar botão de cor
        color_button = Gtk.ColorButton()

        # Carregar cor do GSettings
        rgb_tuple = self.settings.get_value(setting_key).unpack()

        # Converter RGB (0-1) para RGBA Gdk
        rgba = Gdk.RGBA()
        rgba.red = rgb_tuple[0]
        rgba.green = rgb_tuple[1]
        rgba.blue = rgb_tuple[2]
        rgba.alpha = 1.0

        color_button.set_rgba(rgba)
        color_button.set_valign(Gtk.Align.CENTER)

        # Conectar sinal de mudança
        color_button.connect('color-set', self._on_color_changed, setting_key)

        # Adicionar botão à row
        row.add_suffix(color_button)
        row.set_activatable_widget(color_button)

        return row

    def _on_color_changed(self, color_button, setting_key):
        """
        Callback quando uma cor é alterada

        Args:
            color_button: Gtk.ColorButton que disparou o evento
            setting_key: Chave da configuração
        """
        rgba = color_button.get_rgba()
        rgb_tuple = (rgba.red, rgba.green, rgba.blue)

        # Salvar em GSettings
        from gi.repository import GLib
        variant = GLib.Variant('(ddd)', rgb_tuple)
        self.settings.set_value(setting_key, variant)

    def _on_opacity_changed(self, adjustment, setting_key):
        """
        Callback quando uma opacidade é alterada

        Args:
            adjustment: Gtk.Adjustment que disparou o evento
            setting_key: Chave da configuração
        """
        value = adjustment.get_value()
        self.settings.set_double(setting_key, value)

    def _on_depth_changed(self, adjustment, setting_key):
        """
        Callback quando o depth é alterado

        Args:
            adjustment: Gtk.Adjustment que disparou o evento
            setting_key: Chave da configuração
        """
        value = int(adjustment.get_value())
        self.settings.set_int(setting_key, value)

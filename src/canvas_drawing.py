"""
CanvasDrawing - Métodos de renderização do canvas

Responsável por toda a renderização visual do canvas, nós e conexões.
Extraído de canvas.py para melhor separação de responsabilidades.
"""

import cairo


class CanvasDrawing:
    """
    Classe responsável pela renderização do canvas.

    Attributes:
        canvas: Referência ao canvas que será desenhado
    """

    def __init__(self, canvas):
        """
        Inicializa o renderizador do canvas.

        Args:
            canvas: Instância do AssetsCanvas
        """
        self.canvas = canvas

    def draw(self, area, context, width, height):
        """Desenha o canvas e todos os nós"""
        # Fundo com cor configurável
        bg_color = self.canvas._get_color_setting("canvas-bg-color")
        context.set_source_rgb(*bg_color)
        context.paint()

        # Salvar estado do contexto
        context.save()

        # Aplicar transformações de pan e zoom
        context.translate(self.canvas.pan_offset_x, self.canvas.pan_offset_y)
        context.scale(self.canvas.zoom_level, self.canvas.zoom_level)

        # Grid de fundo com dois níveis (blueprint style)
        small_grid_size = 20  # Grid fino (menor)
        large_grid_size = 100  # Grid grosso (maior) - a cada 5 linhas finas

        # Calcular limites visíveis do grid
        start_x = int(-self.canvas.pan_offset_x / self.canvas.zoom_level / small_grid_size) * small_grid_size
        start_y = int(-self.canvas.pan_offset_y / self.canvas.zoom_level / small_grid_size) * small_grid_size
        end_x = int((width - self.canvas.pan_offset_x) / self.canvas.zoom_level) + small_grid_size
        end_y = int((height - self.canvas.pan_offset_y) / self.canvas.zoom_level) + small_grid_size

        # Desenhar grid FINO primeiro (mais claro)
        fine_grid_color = self.canvas._get_color_setting("fine-grid-color")
        context.set_source_rgb(*fine_grid_color)
        # Linha fina com largura constante na tela (não escala com zoom)
        context.set_line_width(0.5 / self.canvas.zoom_level)

        for x in range(start_x, end_x, small_grid_size):
            # Pular as linhas que serão grossas
            if x % large_grid_size != 0:
                context.move_to(x, start_y)
                context.line_to(x, end_y)
        for y in range(start_y, end_y, small_grid_size):
            # Pular as linhas que serão grossas
            if y % large_grid_size != 0:
                context.move_to(start_x, y)
                context.line_to(end_x, y)
        context.stroke()

        # Desenhar grid GROSSO por cima (mais escuro)
        coarse_grid_color = self.canvas._get_color_setting("coarse-grid-color")
        context.set_source_rgb(*coarse_grid_color)
        # Linha grossa com largura constante na tela (não escala com zoom)
        context.set_line_width(1.0 / self.canvas.zoom_level)

        for x in range(start_x, end_x, large_grid_size):
            context.move_to(x, start_y)
            context.line_to(x, end_y)
        for y in range(start_y, end_y, large_grid_size):
            context.move_to(start_x, y)
            context.line_to(end_x, y)
        context.stroke()

        # Desenhar conexões não selecionadas primeiro (atrás dos nós)
        self.draw_connections(context, selected_only=False)

        # Preparar cores do tema para os nós
        theme_colors = {
            'node_body': self.canvas._get_color_setting("node-body-color"),
            'node_border': self.canvas._get_color_setting("node-border-color"),
            'node_selection': self.canvas._get_color_setting("node-selection-color"),
            'node_running': self.canvas._get_color_setting("node-running-color"),
        }

        # Obter opacidade de dimming se em modo focus
        dimming_opacity = 1.0
        if self.canvas.focus_node:
            dimming_opacity = self.canvas._get_opacity_setting("focus-dimming-opacity")

        # Desenhar todos os nós
        for node in self.canvas.nodes:
            # Verificar se o nó deve ser dimmed
            should_dim = self.canvas.focus_node is not None and node not in self.canvas.focus_nodes_set

            if should_dim:
                # Salvar estado e aplicar transparência
                context.save()
                context.push_group()

            node.draw(context, theme_colors)

            if should_dim:
                # Aplicar dimming
                context.pop_group_to_source()
                context.paint_with_alpha(dimming_opacity)
                context.restore()

        # Desenhar conexões selecionadas por cima
        self.draw_connections(context, selected_only=True)

        # Desenhar retângulo de seleção (se estiver selecionando)
        if self.canvas.selecting_region:
            x1 = min(self.canvas.selection_start_x, self.canvas.selection_current_x)
            y1 = min(self.canvas.selection_start_y, self.canvas.selection_current_y)
            x2 = max(self.canvas.selection_start_x, self.canvas.selection_current_x)
            y2 = max(self.canvas.selection_start_y, self.canvas.selection_current_y)

            # Retângulo preenchido semi-transparente
            selection_fill_color = self.canvas._get_color_setting("selection-fill-color")
            selection_fill_opacity = self.canvas._get_opacity_setting("selection-fill-opacity")
            context.set_source_rgba(*selection_fill_color, selection_fill_opacity)
            context.rectangle(x1, y1, x2 - x1, y2 - y1)
            context.fill()

            # Borda do retângulo
            selection_border_color = self.canvas._get_color_setting("selection-border-color")
            selection_border_opacity = self.canvas._get_opacity_setting("selection-border-opacity")
            context.set_source_rgba(*selection_border_color, selection_border_opacity)
            context.set_line_width(1.5 / self.canvas.zoom_level)
            context.rectangle(x1, y1, x2 - x1, y2 - y1)
            context.stroke()

        # Restaurar estado do contexto
        context.restore()

        # Desenhar info de zoom/pan (fora da transformação)
        context.set_source_rgb(0.3, 0.3, 0.3)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(11)
        info_text = f"Zoom: {self.canvas.zoom_level * 100:.0f}% | Pan: ({self.canvas.pan_offset_x:.0f}, {self.canvas.pan_offset_y:.0f}) | Scroll: zoom | Space+Drag: pan | Right-click: menu"
        context.move_to(10, height - 10)
        context.show_text(info_text)

    def draw_connections(self, context, selected_only=False):
        """
        Desenha conexões armazenadas

        Args:
            context: Cairo context
            selected_only: Se True, desenha apenas conexões selecionadas
                          Se False, desenha apenas conexões não selecionadas
        """
        # Desenhar cada conexão da lista
        for connection in self.canvas.connections:
            source_node, out_port, target_node, in_port = connection
            is_selected = (connection == self.canvas.selected_connection)

            # Filtrar baseado no modo
            if selected_only and not is_selected:
                continue
            if not selected_only and is_selected:
                continue

            # Pegar posições das portas
            start = source_node.get_output_port_position(out_port)
            end = target_node.get_input_port_position(in_port)

            # Desenhar se ambas as portas existem
            if start and end:
                # Verificar se deve aplicar dimming
                should_dim = self.canvas.focus_node is not None and connection not in self.canvas.focus_connections_set

                # Cor e largura diferentes se está selecionada
                if is_selected:
                    context.set_line_width(4 / self.canvas.zoom_level)
                    selected_color = self.canvas._get_color_setting("connection-selected-color")
                    alpha = 0.95
                else:
                    context.set_line_width(3 / self.canvas.zoom_level)
                    normal_color = self.canvas._get_color_setting("connection-normal-color")
                    selected_color = normal_color  # Usar mesma variável
                    alpha = 0.75

                # Aplicar dimming se necessário
                if should_dim:
                    dimming_opacity = self.canvas._get_opacity_setting("focus-dimming-opacity")
                    alpha *= dimming_opacity

                context.set_source_rgba(*selected_color, alpha)
                self.draw_connection(context, start, end)

        # Se está criando uma conexão, desenhar linha temporária (sempre por cima)
        if selected_only and self.canvas.creating_connection and self.canvas.connection_start_node:
            start = self.canvas.connection_start_node.get_output_port_position(self.canvas.connection_start_port)
            if start:
                # Linha temporária em cor diferente
                context.set_line_width(3)
                creating_color = self.canvas._get_color_setting("connection-creating-color")
                context.set_source_rgba(*creating_color, 0.8)
                self.draw_connection(context, start, self.canvas.connection_mouse_pos)

    def draw_connection(self, context, start, end):
        """
        Desenha uma conexão curva (Bezier) entre duas portas

        Args:
            context: Cairo context
            start: (x, y) da porta de saída
            end: (x, y) da porta de entrada
        """
        x1, y1 = start
        x2, y2 = end

        # Calcular pontos de controle para curva Bezier suave
        distance = abs(x2 - x1)
        offset = min(distance * 0.5, 100)

        # Pontos de controle
        ctrl1_x = x1 + offset
        ctrl1_y = y1
        ctrl2_x = x2 - offset
        ctrl2_y = y2

        # Desenhar curva
        context.move_to(x1, y1)
        context.curve_to(ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, x2, y2)
        context.stroke()

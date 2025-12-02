#!/usr/bin/env python3
"""
Node - Classe para desenhar e gerenciar um nó visual
"""

import cairo
import uuid
from enum import Enum


class NodeExecutionState(Enum):
    """Estados de execução de um nó"""
    IDLE = "idle"           # Aguardando execução
    RUNNING = "running"     # Em execução
    COMPLETED = "completed" # Concluído com sucesso
    ERROR = "error"         # Erro na execução


class Node:
    """
    Representa um nó visual no canvas.
    Desenha uma caixinha com título, portas de entrada (esquerda) e saída (direita).
    """

    # Constantes de design
    WIDTH = 200
    HEIGHT_HEADER = 40
    HEIGHT_PORT = 30
    PORT_RADIUS = 8
    PORT_SPACING = 10
    PADDING = 10
    BORDER_RADIUS = 8  # Raio das bordas arredondadas

    # Cores
    COLOR_HEADER = (0.2, 0.4, 0.8)  # Azul
    COLOR_BODY = (0.95, 0.95, 0.95)  # Cinza claro
    COLOR_BORDER = (0.3, 0.3, 0.3)  # Cinza escuro
    COLOR_PORT = (0.3, 0.7, 0.3)     # Verde
    COLOR_TEXT = (1, 1, 1)           # Branco (header)
    COLOR_TEXT_BODY = (0.2, 0.2, 0.2)  # Preto (corpo)

    # Cores por tipo de porta
    PORT_COLORS = {
        'any': (0.5, 0.5, 0.5),      # Cinza
        'int': (0.3, 0.6, 1.0),      # Azul claro
        'float': (0.4, 0.7, 1.0),    # Azul ainda mais claro
        'str': (1.0, 0.7, 0.3),      # Laranja
        'list': (0.7, 0.3, 1.0),     # Roxo
        'dict': (1.0, 0.4, 0.7),     # Rosa
        'dataframe': (0.2, 0.8, 0.4),  # Verde
        'array': (0.3, 0.9, 0.6),    # Verde claro
        'figure': (1.0, 0.5, 0.2),   # Laranja escuro
    }

    def __init__(self, x, y, title="Code Node", num_inputs=2, num_outputs=1, node_id=None):
        """
        Inicializa um nó.

        Args:
            x: Posição X no canvas
            y: Posição Y no canvas
            title: Título do nó
            num_inputs: Número de portas de entrada
            num_outputs: Número de portas de saída
            node_id: UUID único (gera automaticamente se None)
        """
        self.id = node_id if node_id else str(uuid.uuid4())
        self.x = x
        self.y = y
        self.title = title
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs

        # Calcular altura total baseado no número de portas
        max_ports = max(num_inputs, num_outputs)
        self.body_height = max_ports * self.HEIGHT_PORT + self.PADDING * 2
        self.total_height = self.HEIGHT_HEADER + self.body_height

        # Armazenar posições das portas (calculadas no draw)
        self.input_ports = []   # Lista de (x, y) das portas de entrada
        self.output_ports = []  # Lista de (x, y) das portas de saída

        # Estado de interatividade
        self.selected = False   # Se o nó está selecionado
        self.hovered = False    # Se o mouse está sobre o nó
        self.dragging = False   # Se está sendo arrastado
        self.drag_offset_x = 0  # Offset do mouse ao arrastar
        self.drag_offset_y = 0

        # Estado de execução
        self.has_error = False  # Se o nó teve erro na última execução
        self.error_message = ""  # Mensagem de erro
        self.execution_state = NodeExecutionState.IDLE  # Estado de execução

        # Código Python do nó
        self._code = ""  # Armazenamento interno

        # Metadata profissional
        self.description = ""         # Descrição do que o nó faz
        self.author = ""              # Autor do nó
        self.version = "1.0"          # Versão do nó
        self.tags = []                # Tags para busca
        self.category = ""            # Categoria

        # Documentação de portas
        self.input_docs = []          # Descrição de cada porta de entrada
        self.output_docs = []         # Descrição de cada porta de saída

        # Tipos de portas (None = any type)
        # Tipos suportados: 'int', 'float', 'str', 'list', 'dict', 'dataframe', 'any'
        self.input_types = ['any'] * num_inputs   # Tipo esperado em cada entrada
        self.output_types = ['any'] * num_outputs  # Tipo de cada saída

        # Customização visual
        self.custom_color = None      # Cor customizada (tuple RGB ou None)

        # Configurações de biblioteca
        self.visibility = "private"   # "private" ou "public"

        # Profiling
        self.last_execution_time = 0.0  # Tempo da última execução em segundos
        self.total_executions = 0       # Contador de execuções

    @property
    def code(self):
        """Retorna o código Python do nó"""
        return self._code

    @code.setter
    def code(self, value):
        """Define o código Python do nó."""
        self._code = value

    def draw(self, context):
        """
        Desenha o nó no canvas usando Cairo.

        Args:
            context: Cairo context
        """
        # 1. Desenhar corpo (fundo)
        self._draw_body(context)

        # 2. Desenhar header
        self._draw_header(context)

        # 3. Desenhar portas de entrada (esquerda)
        self._draw_input_ports(context)

        # 4. Desenhar portas de saída (direita)
        self._draw_output_ports(context)

        # 5. Desenhar borda (muda se selecionado/hover/estado)
        self._draw_border(context)

        # 6. Desenhar badge de estado de execução
        self._draw_execution_state_badge(context)

    def _draw_rounded_rectangle(self, context, x, y, width, height, radius, top_left=True, top_right=True, bottom_right=True, bottom_left=True):
        """
        Desenha um retângulo com bordas arredondadas.

        Args:
            context: Cairo context
            x, y: Posição do retângulo
            width, height: Dimensões
            radius: Raio das bordas
            top_left, top_right, bottom_right, bottom_left: Quais cantos arredondar
        """
        # Começar do canto superior esquerdo
        context.new_path()

        # Canto superior esquerdo
        if top_left:
            context.arc(x + radius, y + radius, radius, 3.14159, 1.5 * 3.14159)
        else:
            context.move_to(x, y)

        # Canto superior direito
        if top_right:
            context.arc(x + width - radius, y + radius, radius, 1.5 * 3.14159, 0)
        else:
            context.line_to(x + width, y)

        # Canto inferior direito
        if bottom_right:
            context.arc(x + width - radius, y + height - radius, radius, 0, 0.5 * 3.14159)
        else:
            context.line_to(x + width, y + height)

        # Canto inferior esquerdo
        if bottom_left:
            context.arc(x + radius, y + height - radius, radius, 0.5 * 3.14159, 3.14159)
        else:
            context.line_to(x, y + height)

        context.close_path()

    def _draw_body(self, context):
        """Desenha o corpo do nó (parte cinza) com cantos inferiores arredondados"""
        context.set_source_rgb(*self.COLOR_BODY)
        self._draw_rounded_rectangle(
            context,
            self.x,
            self.y + self.HEIGHT_HEADER,
            self.WIDTH,
            self.body_height,
            self.BORDER_RADIUS,
            top_left=False,    # Canto superior esquerdo reto (conecta com header)
            top_right=False,   # Canto superior direito reto (conecta com header)
            bottom_right=True, # Canto inferior direito arredondado
            bottom_left=True   # Canto inferior esquerdo arredondado
        )
        context.fill()

    def _draw_header(self, context):
        """Desenha o header (parte azul com título) com cantos superiores arredondados"""
        # Retângulo do header - usar cor de erro, customizada ou padrão
        if self.has_error:
            context.set_source_rgb(0.8, 0.2, 0.2)  # Vermelho para erro
        elif self.custom_color:
            context.set_source_rgb(*self.custom_color)
        else:
            context.set_source_rgb(*self.COLOR_HEADER)

        self._draw_rounded_rectangle(
            context,
            self.x,
            self.y,
            self.WIDTH,
            self.HEIGHT_HEADER,
            self.BORDER_RADIUS,
            top_left=True,     # Canto superior esquerdo arredondado
            top_right=True,    # Canto superior direito arredondado
            bottom_right=False, # Canto inferior direito reto (conecta com corpo)
            bottom_left=False   # Canto inferior esquerdo reto (conecta com corpo)
        )
        context.fill()

        # Texto do título
        context.set_source_rgb(*self.COLOR_TEXT)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(14)

        # Centralizar texto
        extents = context.text_extents(self.title)
        text_x = self.x + (self.WIDTH - extents.width) / 2
        text_y = self.y + (self.HEIGHT_HEADER + extents.height) / 2

        context.move_to(text_x, text_y)
        context.show_text(self.title)

        # Desenhar ícone de erro se houver
        if self.has_error:
            self._draw_error_icon(context)

        # Desenhar indicador de profiling se houver dados
        if self.last_execution_time > 0 and not self.has_error:
            self._draw_profiling_badge(context)

    def _draw_input_ports(self, context):
        """Desenha portas de entrada (bolinhas à esquerda)"""
        self.input_ports.clear()

        for i in range(self.num_inputs):
            # Calcular posição Y da porta
            port_y = (self.y + self.HEIGHT_HEADER + self.PADDING +
                     i * self.HEIGHT_PORT + self.HEIGHT_PORT / 2)
            port_x = self.x  # Exatamente na borda esquerda

            # Cor baseada no tipo da porta
            port_type = self.input_types[i] if i < len(self.input_types) else 'any'
            port_color = self.PORT_COLORS.get(port_type, self.COLOR_PORT)

            # Desenhar bolinha
            context.set_source_rgb(*port_color)
            context.arc(port_x, port_y, self.PORT_RADIUS, 0, 2 * 3.14159)
            context.fill()

            # Borda da bolinha
            context.set_source_rgb(*self.COLOR_BORDER)
            context.set_line_width(2)
            context.arc(port_x, port_y, self.PORT_RADIUS, 0, 2 * 3.14159)
            context.stroke()

            # Label da porta
            context.set_source_rgb(*self.COLOR_TEXT_BODY)
            context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            context.set_font_size(11)
            label = f"in[{i}]"
            context.move_to(port_x + self.PORT_RADIUS + 8, port_y + 4)
            context.show_text(label)

            # Guardar posição
            self.input_ports.append((port_x, port_y))

    def _draw_output_ports(self, context):
        """Desenha portas de saída (bolinhas à direita)"""
        self.output_ports.clear()

        for i in range(self.num_outputs):
            # Calcular posição Y da porta
            port_y = (self.y + self.HEIGHT_HEADER + self.PADDING +
                     i * self.HEIGHT_PORT + self.HEIGHT_PORT / 2)
            port_x = self.x + self.WIDTH  # Exatamente na borda direita

            # Cor baseada no tipo da porta
            port_type = self.output_types[i] if i < len(self.output_types) else 'any'
            port_color = self.PORT_COLORS.get(port_type, self.COLOR_PORT)

            # Desenhar bolinha
            context.set_source_rgb(*port_color)
            context.arc(port_x, port_y, self.PORT_RADIUS, 0, 2 * 3.14159)
            context.fill()

            # Borda da bolinha
            context.set_source_rgb(*self.COLOR_BORDER)
            context.set_line_width(2)
            context.arc(port_x, port_y, self.PORT_RADIUS, 0, 2 * 3.14159)
            context.stroke()

            # Label da porta (à esquerda da bolinha)
            context.set_source_rgb(*self.COLOR_TEXT_BODY)
            context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            context.set_font_size(11)
            label = f"out[{i}]"
            extents = context.text_extents(label)
            context.move_to(port_x - extents.width - self.PORT_RADIUS - 8, port_y + 4)
            context.show_text(label)

            # Guardar posição
            self.output_ports.append((port_x, port_y))

    def _calculate_port_positions(self):
        """Calcula posições das portas sem desenhar (útil para pré-cálculo ao carregar arquivos)"""
        # Calcular posições das portas de entrada
        self.input_ports.clear()
        for i in range(self.num_inputs):
            port_y = (self.y + self.HEIGHT_HEADER + self.PADDING +
                     i * self.HEIGHT_PORT + self.HEIGHT_PORT / 2)
            port_x = self.x
            self.input_ports.append((port_x, port_y))

        # Calcular posições das portas de saída
        self.output_ports.clear()
        for i in range(self.num_outputs):
            port_y = (self.y + self.HEIGHT_HEADER + self.PADDING +
                     i * self.HEIGHT_PORT + self.HEIGHT_PORT / 2)
            port_x = self.x + self.WIDTH
            self.output_ports.append((port_x, port_y))

    def _draw_border(self, context):
        """Desenha borda arredondada ao redor do nó inteiro (muda com hover/seleção/estado)"""
        # Prioridade: erro > execução > seleção > hover > padrão

        if self.execution_state == NodeExecutionState.RUNNING:
            # Executando: borda azul pulsante COM DUPLO GLOW
            # Glow externo (mais transparente)
            context.set_source_rgba(0.2, 0.6, 1.0, 0.15)
            context.set_line_width(10)
            self._draw_rounded_rectangle(
                context, self.x - 5, self.y - 5,
                self.WIDTH + 10, self.total_height + 10,
                self.BORDER_RADIUS + 3
            )
            context.stroke()

            # Glow interno (mais forte)
            context.set_source_rgba(0.2, 0.6, 1.0, 0.4)
            context.set_line_width(6)
            self._draw_rounded_rectangle(
                context, self.x - 2, self.y - 2,
                self.WIDTH + 4, self.total_height + 4,
                self.BORDER_RADIUS + 1
            )
            context.stroke()

            # Borda principal (sólida e grossa)
            context.set_source_rgb(0.2, 0.6, 1.0)  # Azul vivo
            context.set_line_width(3.5)

        elif self.execution_state == NodeExecutionState.COMPLETED:
            # Concluído: borda verde suave
            context.set_source_rgb(0.3, 0.7, 0.3)  # Verde
            context.set_line_width(2.5)
        elif self.execution_state == NodeExecutionState.IDLE:
            # Aguardando: borda laranja suave
            context.set_source_rgb(0.9, 0.6, 0.2)  # Laranja
            context.set_line_width(2)
        elif self.selected:
            # Selecionado: borda azul COM GLOW
            # Glow externo
            context.set_source_rgba(0.2, 0.5, 1.0, 0.25)
            context.set_line_width(8)
            self._draw_rounded_rectangle(
                context, self.x - 3, self.y - 3,
                self.WIDTH + 6, self.total_height + 6,
                self.BORDER_RADIUS + 2
            )
            context.stroke()

            # Borda principal
            context.set_source_rgb(0.2, 0.5, 1.0)  # Azul brilhante
            context.set_line_width(3)
        elif self.hovered:
            context.set_source_rgb(0.5, 0.5, 0.5)  # Cinza mais claro
            context.set_line_width(2.5)
        else:
            context.set_source_rgb(*self.COLOR_BORDER)
            context.set_line_width(2)

        self._draw_rounded_rectangle(
            context,
            self.x,
            self.y,
            self.WIDTH,
            self.total_height,
            self.BORDER_RADIUS
        )
        context.stroke()

    def _draw_selection_indicator(self, context):
        """Desenha indicador visual arredondado de que o nó está selecionado"""
        # Brilho/glow ao redor quando selecionado
        context.set_source_rgba(0.2, 0.5, 1.0, 0.2)  # Azul semi-transparente
        context.set_line_width(8)
        self._draw_rounded_rectangle(
            context,
            self.x - 2,
            self.y - 2,
            self.WIDTH + 4,
            self.total_height + 4,
            self.BORDER_RADIUS + 1
        )
        context.stroke()

    def contains_point(self, px, py):
        """
        Verifica se um ponto está dentro do nó.
        Útil para detecção de clique.

        Args:
            px: Coordenada X do ponto
            py: Coordenada Y do ponto

        Returns:
            bool: True se o ponto está dentro do nó
        """
        return (self.x <= px <= self.x + self.WIDTH and
                self.y <= py <= self.y + self.total_height)

    def start_drag(self, mouse_x, mouse_y):
        """
        Inicia o arrasto do nó.

        Args:
            mouse_x: Posição X do mouse
            mouse_y: Posição Y do mouse
        """
        self.dragging = True
        self.drag_offset_x = mouse_x - self.x
        self.drag_offset_y = mouse_y - self.y

    def update_drag(self, mouse_x, mouse_y):
        """
        Atualiza a posição do nó durante o arrasto.

        Args:
            mouse_x: Posição X atual do mouse
            mouse_y: Posição Y atual do mouse
        """
        if self.dragging:
            self.x = mouse_x - self.drag_offset_x
            self.y = mouse_y - self.drag_offset_y

    def stop_drag(self):
        """Para o arrasto do nó."""
        self.dragging = False

    def set_selected(self, selected):
        """
        Define se o nó está selecionado.

        Args:
            selected: bool
        """
        self.selected = selected

    def set_hovered(self, hovered):
        """
        Define se o mouse está sobre o nó.

        Args:
            hovered: bool
        """
        self.hovered = hovered

    def move_to(self, x, y):
        """
        Move o nó para uma posição específica.

        Args:
            x: Nova posição X
            y: Nova posição Y
        """
        self.x = x
        self.y = y

    def get_input_port_position(self, index):
        """Retorna posição (x, y) de uma porta de entrada"""
        if 0 <= index < len(self.input_ports):
            return self.input_ports[index]
        return None

    def get_output_port_position(self, index):
        """Retorna posição (x, y) de uma porta de saída"""
        if 0 <= index < len(self.output_ports):
            return self.output_ports[index]
        return None

    def validate_input_types(self, inputs):
        """
        Valida se os tipos dos inputs batem com os tipos esperados.

        Args:
            inputs: Tupla com valores de entrada

        Returns:
            tuple: (is_valid, error_message)
        """
        if len(inputs) != len(self.input_types):
            return False, f"Esperava {len(self.input_types)} inputs, recebeu {len(inputs)}"

        for i, (value, expected_type) in enumerate(zip(inputs, self.input_types)):
            # 'any' aceita qualquer coisa
            if expected_type == 'any' or value is None:
                continue

            # Validação por tipo
            actual_type = type(value).__name__

            if expected_type == 'int':
                if not isinstance(value, int) or isinstance(value, bool):
                    return False, f"Porta in[{i}] esperava 'int', recebeu '{actual_type}'"

            elif expected_type == 'float':
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    return False, f"Porta in[{i}] esperava 'float', recebeu '{actual_type}'"

            elif expected_type == 'str':
                if not isinstance(value, str):
                    return False, f"Porta in[{i}] esperava 'str', recebeu '{actual_type}'"

            elif expected_type == 'list':
                if not isinstance(value, list):
                    return False, f"Porta in[{i}] esperava 'list', recebeu '{actual_type}'"

            elif expected_type == 'dict':
                if not isinstance(value, dict):
                    return False, f"Porta in[{i}] esperava 'dict', recebeu '{actual_type}'"

            elif expected_type == 'dataframe':
                try:
                    import pandas as pd
                    if not isinstance(value, pd.DataFrame):
                        return False, f"Porta in[{i}] esperava 'DataFrame', recebeu '{actual_type}'"
                except ImportError:
                    # Se pandas não está instalado, ignora validação
                    pass

            elif expected_type == 'array':
                try:
                    import numpy as np
                    if not isinstance(value, np.ndarray):
                        return False, f"Porta in[{i}] esperava 'ndarray', recebeu '{actual_type}'"
                except ImportError:
                    # Se numpy não está instalado, ignora validação
                    pass

            elif expected_type == 'figure':
                try:
                    import matplotlib.figure
                    if not isinstance(value, matplotlib.figure.Figure):
                        return False, f"Porta in[{i}] esperava 'Figure', recebeu '{actual_type}'"
                except ImportError:
                    # Se matplotlib não está instalado, ignora validação
                    pass

        return True, ""

    def _draw_error_icon(self, context):
        """Desenha ícone de erro (!) no canto superior direito"""
        icon_x = self.x + self.WIDTH - 20
        icon_y = self.y + self.HEIGHT_HEADER / 2

        # Círculo de fundo vermelho (mais visível)
        context.set_source_rgb(1.0, 0.2, 0.2)
        context.arc(icon_x, icon_y, 12, 0, 2 * 3.14159)
        context.fill()

        # Borda branca para contraste
        context.set_source_rgb(1.0, 1.0, 1.0)
        context.set_line_width(2)
        context.arc(icon_x, icon_y, 12, 0, 2 * 3.14159)
        context.stroke()

        # Símbolo "!" em branco
        context.set_source_rgb(1.0, 1.0, 1.0)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(16)
        extents = context.text_extents("!")
        context.move_to(icon_x - extents.width / 2, icon_y + extents.height / 2)
        context.show_text("!")

    def _draw_profiling_badge(self, context):
        """Desenha badge com tempo de execução no canto superior direito"""
        time_ms = self.last_execution_time * 1000
        badge_text = f"{time_ms:.1f}ms"

        context.set_source_rgba(0, 0, 0, 0.7)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(9)

        extents = context.text_extents(badge_text)
        badge_x = self.x + self.WIDTH - extents.width - 8
        badge_y = self.y + 6

        context.move_to(badge_x, badge_y + extents.height)
        context.show_text(badge_text)

    def _draw_execution_state_badge(self, context):
        """Desenha badge de estado de execução no canto inferior esquerdo"""
        # Não desenhar se estiver completado (aparência normal)
        if self.execution_state == NodeExecutionState.COMPLETED:
            return

        # Posição do badge
        badge_x = self.x + 8
        badge_y = self.y + self.total_height - 8

        # Cor baseada no estado
        if self.execution_state == NodeExecutionState.IDLE:
            color = (0.9, 0.6, 0.2)  # Laranja
        elif self.execution_state == NodeExecutionState.RUNNING:
            color = (0.2, 0.6, 1.0)  # Azul
        elif self.execution_state == NodeExecutionState.ERROR:
            color = (1.0, 0.2, 0.2)  # Vermelho
        else:
            return

        # Desenhar círculo de fundo
        context.set_source_rgba(*color, 0.3)
        context.arc(badge_x, badge_y, 10, 0, 2 * 3.14159)
        context.fill()

        # Desenhar símbolo baseado no estado
        context.set_source_rgb(*color)

        if self.execution_state == NodeExecutionState.IDLE:
            # Desenhar relógio (círculo com ponteiros)
            context.set_line_width(1.5)
            context.arc(badge_x, badge_y, 6, 0, 2 * 3.14159)
            context.stroke()
            # Ponteiro curto (horas)
            context.move_to(badge_x, badge_y)
            context.line_to(badge_x + 3, badge_y - 2)
            context.stroke()
            # Ponteiro longo (minutos)
            context.move_to(badge_x, badge_y)
            context.line_to(badge_x, badge_y - 4)
            context.stroke()

        elif self.execution_state == NodeExecutionState.RUNNING:
            # Desenhar triângulo play
            context.move_to(badge_x - 3, badge_y - 4)
            context.line_to(badge_x - 3, badge_y + 4)
            context.line_to(badge_x + 4, badge_y)
            context.close_path()
            context.fill()

        elif self.execution_state == NodeExecutionState.ERROR:
            # Desenhar X
            context.set_line_width(2)
            context.move_to(badge_x - 4, badge_y - 4)
            context.line_to(badge_x + 4, badge_y + 4)
            context.stroke()
            context.move_to(badge_x + 4, badge_y - 4)
            context.line_to(badge_x - 4, badge_y + 4)
            context.stroke()

    def to_dict(self):
        """
        Serializa o nó para um dicionário (para salvar em arquivo).

        Returns:
            dict: Representação do nó em dicionário
        """
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "title": self.title,
            "num_inputs": self.num_inputs,
            "num_outputs": self.num_outputs,
            "code": self._code,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
            "category": self.category,
            "input_docs": self.input_docs,
            "output_docs": self.output_docs,
            "custom_color": self.custom_color,
            "visibility": self.visibility
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Cria um nó a partir de um dicionário (para carregar de arquivo).

        Args:
            data: Dicionário com dados do nó

        Returns:
            Node: Nova instância do nó
        """
        node = cls(
            x=data["x"],
            y=data["y"],
            title=data["title"],
            num_inputs=data["num_inputs"],
            num_outputs=data["num_outputs"],
            node_id=data.get("id")
        )
        node.code = data.get("code", "")
        node.description = data.get("description", "")
        node.author = data.get("author", "")
        node.version = data.get("version", "1.0")
        node.tags = data.get("tags", [])
        node.category = data.get("category", "")
        node.input_docs = data.get("input_docs", [])
        node.output_docs = data.get("output_docs", [])
        node.custom_color = data.get("custom_color")
        node.visibility = data.get("visibility", "private")
        return node

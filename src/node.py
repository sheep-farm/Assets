#!/usr/bin/env python3
"""
Node - Classe para desenhar e gerenciar um nó visual
"""

import cairo
import uuid


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

    # Cores
    COLOR_HEADER = (0.2, 0.4, 0.8)  # Azul
    COLOR_BODY = (0.95, 0.95, 0.95)  # Cinza claro
    COLOR_BORDER = (0.3, 0.3, 0.3)  # Cinza escuro
    COLOR_PORT = (0.3, 0.7, 0.3)     # Verde
    COLOR_TEXT = (1, 1, 1)           # Branco (header)
    COLOR_TEXT_BODY = (0.2, 0.2, 0.2)  # Preto (corpo)

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

        # Código Python do nó
        self._code = ""  # Armazenamento interno

        # Sistema de cache (última execução)
        self._last_inputs = None      # Hash das últimas entradas
        self._last_outputs = None     # Resultados da última execução
        self._cache_valid = False     # Flag de validade do cache

    @property
    def code(self):
        """Retorna o código Python do nó"""
        return self._code

    @code.setter
    def code(self, value):
        """
        Define o código Python do nó.
        Invalida o cache quando o código é modificado.
        """
        if self._code != value:
            self._code = value
            self.invalidate_cache()

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

        # 5. Desenhar borda (muda se selecionado/hover)
        self._draw_border(context)

        # 6. Desenhar indicador de seleção (se selecionado)
        if self.selected:
            self._draw_selection_indicator(context)

    def _draw_body(self, context):
        """Desenha o corpo do nó (parte cinza)"""
        context.set_source_rgb(*self.COLOR_BODY)
        context.rectangle(
            self.x,
            self.y + self.HEIGHT_HEADER,
            self.WIDTH,
            self.body_height
        )
        context.fill()

    def _draw_header(self, context):
        """Desenha o header (parte azul com título)"""
        # Retângulo do header
        context.set_source_rgb(*self.COLOR_HEADER)
        context.rectangle(
            self.x,
            self.y,
            self.WIDTH,
            self.HEIGHT_HEADER
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

    def _draw_input_ports(self, context):
        """Desenha portas de entrada (bolinhas à esquerda)"""
        self.input_ports.clear()

        for i in range(self.num_inputs):
            # Calcular posição Y da porta
            port_y = (self.y + self.HEIGHT_HEADER + self.PADDING +
                     i * self.HEIGHT_PORT + self.HEIGHT_PORT / 2)
            port_x = self.x  # Exatamente na borda esquerda

            # Desenhar bolinha
            context.set_source_rgb(*self.COLOR_PORT)
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

            # Desenhar bolinha
            context.set_source_rgb(*self.COLOR_PORT)
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

    def _draw_border(self, context):
        """Desenha borda ao redor do nó inteiro (muda com hover/seleção)"""
        # Escolher cor e espessura baseado no estado
        if self.selected:
            context.set_source_rgb(0.2, 0.5, 1.0)  # Azul brilhante
            context.set_line_width(3)
        elif self.hovered:
            context.set_source_rgb(0.5, 0.5, 0.5)  # Cinza mais claro
            context.set_line_width(2.5)
        else:
            context.set_source_rgb(*self.COLOR_BORDER)
            context.set_line_width(2)

        context.rectangle(
            self.x,
            self.y,
            self.WIDTH,
            self.total_height
        )
        context.stroke()

    def _draw_selection_indicator(self, context):
        """Desenha indicador visual de que o nó está selecionado"""
        # Brilho/glow ao redor quando selecionado
        context.set_source_rgba(0.2, 0.5, 1.0, 0.2)  # Azul semi-transparente
        context.set_line_width(8)
        context.rectangle(
            self.x - 2,
            self.y - 2,
            self.WIDTH + 4,
            self.total_height + 4
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

    def _hash_inputs(self, inputs):
        """
        Gera hash das entradas para comparação de cache.

        Args:
            inputs: Tupla com valores de entrada

        Returns:
            int: Hash das entradas
        """
        try:
            # Converte para string e gera hash
            # Usa repr() para capturar tipos diferentes
            input_str = repr(inputs)
            return hash(input_str)
        except Exception:
            # Se não conseguir gerar hash, retorna None (força recálculo)
            return None

    def get_cached_result(self, inputs):
        """
        Tenta recuperar resultado do cache.

        Args:
            inputs: Tupla com valores de entrada

        Returns:
            tuple: (resultado, from_cache)
                - resultado: Resultado em cache ou None se inválido
                - from_cache: bool indicando se veio do cache
        """
        if not self._cache_valid:
            return None, False

        # Verificar se entradas são iguais
        current_hash = self._hash_inputs(inputs)
        if current_hash is None or current_hash != self._last_inputs:
            return None, False

        # Usar stdout original para não ser capturado
        import sys
        print(f"✓ Cache hit: {self.title}", file=sys.__stdout__)
        return self._last_outputs, True

    def set_cache(self, inputs, outputs):
        """
        Armazena resultado no cache.

        Args:
            inputs: Tupla com valores de entrada
            outputs: Resultados da execução
        """
        self._last_inputs = self._hash_inputs(inputs)
        self._last_outputs = outputs
        self._cache_valid = True
        # Usar stdout original para não ser capturado
        import sys
        print(f"⚙️ Executado e cacheado: {self.title}", file=sys.__stdout__)

    def invalidate_cache(self):
        """
        Invalida o cache, forçando recálculo na próxima execução.
        Útil quando o código do nó é modificado.
        """
        self._cache_valid = False
        self._last_inputs = None
        self._last_outputs = None

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
            "code": self._code  # Usa _code diretamente
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
            node_id=data.get("id")  # Usa ID existente ou gera novo
        )
        node.code = data.get("code", "")
        return node

#!/usr/bin/env python3
"""
output_node.py - Node especial que representa saídas de um GroupNode
"""

from .node import Node
import cairo


class OutputNode(Node):
    """
    Node especial que envia outputs para fora do GroupNode.

    Características:
    - Só existe DENTRO de GroupNodes
    - Não tem outputs (num_outputs=0)
    - Inputs são mapeados para outputs do GroupNode pai
    - Não editável
    """

    COLOR_HEADER = (0.8, 0.4, 0.2)  # Laranja
    COLOR_BODY = (1.0, 0.95, 0.9)   # Laranja muito claro

    def __init__(self, x, y, num_inputs=1, node_id=None):
        super().__init__(
            x=x,
            y=y,
            title="Output",
            num_inputs=num_inputs,
            num_outputs=0,     # Sem outputs!
            node_id=node_id
        )

        # Identificação
        self.is_special_node = True
        self.node_type = "output"

        # Não editável
        self._code = "[OUTPUT NODE - Envia dados para fora do GroupNode]"
        self.code_editable = False

        # Descrição
        self.description = "Ponto de saída do GroupNode"
        self.category = "Group Interface"

        # Input types (configurável)
        self.input_types = ['any'] * num_inputs
        self.input_docs = [f"Output {i} do GroupNode" for i in range(num_inputs)]

    @property
    def code(self):
        """OutputNode não tem código editável"""
        return self._code

    @code.setter
    def code(self, value):
        """Ignora tentativas de editar código"""
        pass

    def draw(self, cr, theme_colors=None, dimmed=False):
        """Desenha OutputNode com ícone especial"""
        super().draw(cr, theme_colors)

        # Ícone de saída (seta para esquerda)
        cr.set_source_rgb(1, 1, 1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(20)
        cr.move_to(self.x + self.WIDTH - 35, self.y + 28)
        cr.show_text("◀")

        # Badge "OUTPUT"
        cr.set_font_size(9)
        cr.set_source_rgb(0.8, 0.4, 0.2)
        cr.move_to(self.x + 10, self.y + self.total_height - 8)
        cr.show_text("OUTPUT")

    def execute(self, inputs):
        """
        'Executa' o OutputNode - coleta inputs e prepara para saída.

        Args:
            inputs: Tuple de valores de dentro do GroupNode

        Returns:
            tuple: Os mesmos inputs (passthrough)
        """
        # OutputNode apenas passa adiante
        return inputs

    def to_dict(self):
        """Serializa"""
        data = super().to_dict()
        data['node_type'] = 'output'
        data['is_special_node'] = True
        return data

    @staticmethod
    def from_dict(data):
        """Deserializa"""
        node = OutputNode(
            x=data['x'],
            y=data['y'],
            num_inputs=data['num_inputs'],
            node_id=data.get('id')
        )

        # Restaurar tipos e docs
        node.input_types = data.get('input_types', ['any'] * node.num_inputs)
        node.input_docs = data.get('input_docs', [])
        node.title = data.get('title', 'Output')

        return node

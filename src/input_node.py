#!/usr/bin/env python3
"""
input_node.py - Node especial que representa entradas de um GroupNode
"""

from .node import Node
import cairo


class InputNode(Node):
    """
    Node especial que recebe inputs externos do GroupNode.

    Características:
    - Só existe DENTRO de GroupNodes
    - Não tem inputs (num_inputs=0)
    - Outputs são mapeados para inputs do GroupNode pai
    - Não editável (código fixo)
    """

    COLOR_HEADER = (0.2, 0.6, 0.8)  # Azul claro
    COLOR_BODY = (0.9, 0.95, 1.0)   # Azul muito claro

    def __init__(self, x, y, num_outputs=1, node_id=None):
        super().__init__(
            x=x,
            y=y,
            title="Input",
            num_inputs=0,      # Sem inputs!
            num_outputs=num_outputs,
            node_id=node_id
        )

        # Identificação
        self.is_special_node = True
        self.node_type = "input"

        # Não editável
        self._code = "[INPUT NODE - Recebe dados do GroupNode pai]"
        self.code_editable = False

        # Descrição
        self.description = "Ponto de entrada do GroupNode"
        self.category = "Group Interface"

        # Output types (configurável)
        self.output_types = ['any'] * num_outputs
        self.output_docs = [f"Input {i} do GroupNode" for i in range(num_outputs)]

    @property
    def code(self):
        """InputNode não tem código editável"""
        return self._code

    @code.setter
    def code(self, value):
        """Ignora tentativas de editar código"""
        pass

    def draw(self, cr, theme_colors=None, dimmed=False):
        """Desenha InputNode com ícone especial"""
        super().draw(cr, theme_colors)

        # Ícone de entrada (seta para direita)
        cr.set_source_rgb(1, 1, 1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(20)
        cr.move_to(self.x + self.WIDTH - 35, self.y + 28)
        cr.show_text("▶")

        # Badge "INPUT"
        cr.set_font_size(9)
        cr.set_source_rgb(0.2, 0.6, 0.8)
        cr.move_to(self.x + 10, self.y + self.total_height - 8)
        cr.show_text("INPUT")

    def execute(self, external_inputs):
        """
        'Executa' o InputNode - simplesmente passa os inputs externos.

        Args:
            external_inputs: Tuple vinda do GroupNode pai

        Returns:
            tuple: Os mesmos inputs (passthrough)
        """
        # InputNode apenas passa adiante o que recebeu
        return external_inputs

    def to_dict(self):
        """Serializa"""
        data = super().to_dict()
        data['node_type'] = 'input'
        data['is_special_node'] = True
        return data

    @staticmethod
    def from_dict(data):
        """Deserializa"""
        node = InputNode(
            x=data['x'],
            y=data['y'],
            num_outputs=data['num_outputs'],
            node_id=data.get('id')
        )

        # Restaurar tipos e docs
        node.output_types = data.get('output_types', ['any'] * node.num_outputs)
        node.output_docs = data.get('output_docs', [])
        node.title = data.get('title', 'Input')

        return node

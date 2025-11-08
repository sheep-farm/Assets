# window.py
#
# Copyright 2025 Flavio de Vasconcellos Corrêa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw
from gi.repository import Gtk

import cairo

from .node import Node


class AssetsCanvas(Gtk.DrawingArea):
    """Canvas que desenha os nós"""

    def __init__(self):
        super().__init__()
        self.set_draw_func(self.on_draw)

        # Criar alguns nós de exemplo
        self.nodes = [
            Node(50, 50, "Input: Stock Data", num_inputs=0, num_outputs=2),
            Node(320, 80, "Calculate Returns", num_inputs=1, num_outputs=1),
            Node(320, 250, "Moving Average", num_inputs=2, num_outputs=1),
            Node(590, 120, "Plot Chart", num_inputs=2, num_outputs=0),
            Node(590, 300, "Export CSV", num_inputs=1, num_outputs=0),
        ]

        # Armazenar conexões como: (nó_origem, porta_saída, nó_destino, porta_entrada)
        # Guarda REFERÊNCIAS aos nós, não índices!
        self.connections = [
            (self.nodes[0], 0, self.nodes[1], 0),  # Stock Data out[0] -> Calculate Returns in[0]
            (self.nodes[0], 1, self.nodes[2], 0),  # Stock Data out[1] -> Moving Average in[0]
            (self.nodes[1], 0, self.nodes[3], 0),  # Calculate Returns out[0] -> Plot Chart in[0]
            (self.nodes[2], 0, self.nodes[3], 1),  # Moving Average out[0] -> Plot Chart in[1]
            (self.nodes[2], 0, self.nodes[4], 0),  # Moving Average out[0] -> Export CSV in[0]
        ]

        # Estado de interação
        self.dragging_node = None
        self.hovered_node = None
        self.focused_node_index = -1  # Índice do nó com foco (-1 = nenhum)
        self.clipboard_node = None  # Nó copiado para clipboard

        # Estado para criar conexões
        self.creating_connection = False  # Está criando uma conexão?
        self.connection_start_node = None  # Nó de origem
        self.connection_start_port = None  # Porta de saída
        self.connection_mouse_pos = (0, 0)  # Posição atual do mouse

        # Configurar eventos de mouse
        self._setup_mouse_events()

        # Configurar eventos de teclado
        self._setup_keyboard_events()

        print(f"✓ Canvas criado com {len(self.nodes)} nós")
        print(f"✓ {len(self.connections)} conexões criadas")
        print("  - Clique para selecionar")
        print("  - Arraste para mover")
        print("  - TAB/Shift+TAB para navegar")
        print("  - Setas para mover nó focado")
        print("  - Delete para remover nó focado")
        print("  - Ctrl+C para copiar")
        print("  - Ctrl+V para colar")
        print("  - Ctrl+D para duplicar")

    def _setup_mouse_events(self):
        """Configura controladores de eventos de mouse"""

        # Click
        click_gesture = Gtk.GestureClick.new()
        click_gesture.connect("pressed", self.on_mouse_pressed)
        click_gesture.connect("released", self.on_mouse_released)
        self.add_controller(click_gesture)

        # Drag
        drag_gesture = Gtk.GestureDrag.new()
        drag_gesture.connect("drag-begin", self.on_drag_begin)
        drag_gesture.connect("drag-update", self.on_drag_update)
        drag_gesture.connect("drag-end", self.on_drag_end)
        self.add_controller(drag_gesture)

        # Motion (hover)
        motion_controller = Gtk.EventControllerMotion.new()
        motion_controller.connect("motion", self.on_mouse_motion)
        self.add_controller(motion_controller)

    def _setup_keyboard_events(self):
        """Configura controlador de eventos de teclado"""
        # O canvas precisa poder receber foco
        self.set_can_focus(True)
        self.set_focusable(True)

        # Controlador de teclado
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        # Dar foco inicial ao canvas
        self.grab_focus()

    def on_mouse_pressed(self, gesture, n_press, x, y):
        """Quando o mouse é pressionado"""
        print(f"Click em ({x:.0f}, {y:.0f})")

        # Primeiro, verificar se clicou em uma porta de SAÍDA (para criar conexão)
        for node in reversed(self.nodes):
            port_index = self._get_output_port_at(node, x, y)
            if port_index is not None:
                # Clicou em uma porta de saída - iniciar criação de conexão
                self.creating_connection = True
                self.connection_start_node = node
                self.connection_start_port = port_index
                self.connection_mouse_pos = (x, y)
                print(f"🔗 Iniciando conexão de {node.title}.out[{port_index}]")
                self.queue_draw()
                return

        # Verificar se clicou em algum nó (corpo do nó, não porta)
        clicked_node = None
        for node in reversed(self.nodes):
            if node.contains_point(x, y):
                clicked_node = node
                break

        # Desselecionar todos
        for node in self.nodes:
            node.set_selected(False)

        # Selecionar o clicado e trazer para frente (z-order)
        if clicked_node:
            clicked_node.set_selected(True)
            print(f"  → Selecionou: {clicked_node.title}")

            # Z-order: mover nó para o final da lista (desenha por último = fica em cima)
            self.bring_to_front(clicked_node)

            # Atualizar índice de foco para o nó clicado
            self.focused_node_index = self.nodes.index(clicked_node)
        else:
            # Clicou no vazio - remove foco
            self.focused_node_index = -1

        self.queue_draw()

    def _get_output_port_at(self, node, x, y):
        """
        Verifica se (x, y) está sobre uma porta de saída do nó.

        Args:
            node: Nó a verificar
            x, y: Coordenadas do clique

        Returns:
            int: Índice da porta (0, 1, 2...) ou None se não clicou em porta
        """
        port_click_radius = 12  # Raio de detecção ao redor da porta

        for i, (port_x, port_y) in enumerate(node.output_ports):
            distance = ((x - port_x) ** 2 + (y - port_y) ** 2) ** 0.5
            if distance <= port_click_radius:
                return i

        return None

    def _get_input_port_at(self, node, x, y):
        """
        Verifica se (x, y) está sobre uma porta de entrada do nó.

        Args:
            node: Nó a verificar
            x, y: Coordenadas do clique

        Returns:
            int: Índice da porta (0, 1, 2...) ou None se não clicou em porta
        """
        port_click_radius = 12  # Raio de detecção ao redor da porta

        for i, (port_x, port_y) in enumerate(node.input_ports):
            distance = ((x - port_x) ** 2 + (y - port_y) ** 2) ** 0.5
            if distance <= port_click_radius:
                return i

        return None

    def bring_to_front(self, node):
        """
        Move um nó para o final da lista (z-order: fica em cima).

        Args:
            node: Nó a ser movido para frente
        """
        if node in self.nodes:
            self.nodes.remove(node)
            self.nodes.append(node)
            # Atualizar índice de foco se necessário
            if self.focused_node_index >= 0:
                # O nó focado agora está no final da lista
                self.focused_node_index = len(self.nodes) - 1
            print(f"  → Trouxe para frente: {node.title}")

    def on_key_pressed(self, controller, keyval, keycode, state):
        """
        Processa teclas pressionadas.

        Args:
            controller: EventControllerKey
            keyval: Valor da tecla (Gdk.KEY_*)
            keycode: Código da tecla
            state: Modificadores (Ctrl, Shift, etc)

        Returns:
            bool: True se processou a tecla (impede propagação)
        """
        from gi.repository import Gdk

        # Verificar se Ctrl está pressionado
        ctrl_pressed = state & Gdk.ModifierType.CONTROL_MASK

        # Ctrl+C - Copiar nó focado
        if ctrl_pressed and keyval == Gdk.KEY_c:
            self._copy_focused_node()
            return True

        # Ctrl+V - Colar nó do clipboard
        if ctrl_pressed and keyval == Gdk.KEY_v:
            self._paste_node()
            return True

        # Ctrl+D - Duplicar nó focado
        if ctrl_pressed and keyval == Gdk.KEY_d:
            self._duplicate_focused_node()
            return True

        # TAB - Próximo nó
        if keyval == Gdk.KEY_Tab and not (state & Gdk.ModifierType.SHIFT_MASK):
            self._focus_next_node()
            return True

        # Shift+TAB - Nó anterior
        if keyval == Gdk.KEY_Tab and (state & Gdk.ModifierType.SHIFT_MASK):
            self._focus_previous_node()
            return True

        # Escape - Deselecionar tudo
        if keyval == Gdk.KEY_Escape:
            self._clear_selection()
            return True

        # Delete - Remover nó focado
        if keyval == Gdk.KEY_Delete:
            self._delete_focused_node()
            return True

        # Setas - Mover nó focado
        if self.focused_node_index >= 0 and self.focused_node_index < len(self.nodes):
            focused = self.nodes[self.focused_node_index]
            move_speed = 10  # pixels por tecla

            if keyval == Gdk.KEY_Left:
                focused.move_to(focused.x - move_speed, focused.y)
                self.queue_draw()
                return True
            elif keyval == Gdk.KEY_Right:
                focused.move_to(focused.x + move_speed, focused.y)
                self.queue_draw()
                return True
            elif keyval == Gdk.KEY_Up:
                focused.move_to(focused.x, focused.y - move_speed)
                self.queue_draw()
                return True
            elif keyval == Gdk.KEY_Down:
                focused.move_to(focused.x, focused.y + move_speed)
                self.queue_draw()
                return True

        return False  # Não processou - deixa propagar

    def _focus_next_node(self):
        """Move foco para o próximo nó (TAB)"""
        if not self.nodes:
            return

        # Desselecionar atual
        if 0 <= self.focused_node_index < len(self.nodes):
            self.nodes[self.focused_node_index].set_selected(False)

        # Próximo índice (circular)
        self.focused_node_index = (self.focused_node_index + 1) % len(self.nodes)

        # Selecionar novo
        self.nodes[self.focused_node_index].set_selected(True)
        print(f"Foco → {self.nodes[self.focused_node_index].title}")
        self.queue_draw()

    def _focus_previous_node(self):
        """Move foco para o nó anterior (Shift+TAB)"""
        if not self.nodes:
            return

        # Desselecionar atual
        if 0 <= self.focused_node_index < len(self.nodes):
            self.nodes[self.focused_node_index].set_selected(False)

        # Índice anterior (circular)
        self.focused_node_index = (self.focused_node_index - 1) % len(self.nodes)

        # Selecionar novo
        self.nodes[self.focused_node_index].set_selected(True)
        print(f"Foco ← {self.nodes[self.focused_node_index].title}")
        self.queue_draw()

    def _clear_selection(self):
        """Deseleciona todos os nós (Escape)"""
        for node in self.nodes:
            node.set_selected(False)
        self.focused_node_index = -1
        print("Seleção limpa")
        self.queue_draw()

    def _delete_focused_node(self):
        """Remove o nó que está com foco (Delete)"""
        if 0 <= self.focused_node_index < len(self.nodes):
            node_to_delete = self.nodes[self.focused_node_index]

            # Remover conexões associadas ao nó
            self.connections = [
                conn for conn in self.connections
                if conn[0] != node_to_delete and conn[2] != node_to_delete
            ]

            # Remover o nó
            self.nodes.remove(node_to_delete)
            print(f"✗ Removido: {node_to_delete.title}")

            # Ajustar índice de foco
            if self.focused_node_index >= len(self.nodes):
                self.focused_node_index = len(self.nodes) - 1

            self.queue_draw()

    def _copy_focused_node(self):
        """Copia o nó focado para o clipboard (Ctrl+C)"""
        if 0 <= self.focused_node_index < len(self.nodes):
            self.clipboard_node = self.nodes[self.focused_node_index]
            print(f"📋 Copiado: {self.clipboard_node.title}")
        else:
            print("⚠️  Nenhum nó selecionado para copiar")

    def _paste_node(self):
        """Cola o nó do clipboard (Ctrl+V)"""
        if self.clipboard_node is None:
            print("⚠️  Clipboard vazio")
            return

        # Criar novo nó com offset de posição
        offset = 30  # Deslocamento para não colar em cima
        new_node = Node(
            self.clipboard_node.x + offset,
            self.clipboard_node.y + offset,
            f"{self.clipboard_node.title} (cópia)",
            num_inputs=self.clipboard_node.num_inputs,
            num_outputs=self.clipboard_node.num_outputs
        )

        # Adicionar à lista
        self.nodes.append(new_node)

        # NOTA: Não copiamos as conexões porque elas referenciam outros nós
        # Para copiar conexões seria necessário copiar também os nós conectados

        # Desselecionar todos
        for node in self.nodes:
            node.set_selected(False)

        # Selecionar o novo
        new_node.set_selected(True)

        # Atualizar foco para o índice correto do novo nó
        self.focused_node_index = self.nodes.index(new_node)

        print(f"📌 Colado: {new_node.title} em ({new_node.x:.0f}, {new_node.y:.0f})")
        print(f"   Foco atualizado para índice {self.focused_node_index}")
        self.queue_draw()

    def _duplicate_focused_node(self):
        """Duplica o nó focado (Ctrl+D) - atalho para copiar+colar"""
        if 0 <= self.focused_node_index < len(self.nodes):
            # Copiar
            self._copy_focused_node()
            # Colar imediatamente
            self._paste_node()
        else:
            print("⚠️  Nenhum nó selecionado para duplicar")

    def on_mouse_released(self, gesture, n_press, x, y):
        """Quando o mouse é solto"""
        # Se estava criando conexão, tentar finalizar
        if self.creating_connection:
            self._finish_connection(x, y)
            self.creating_connection = False
            self.connection_start_node = None
            self.connection_start_port = None
            self.queue_draw()
            return

        # Se estava arrastando nó
        if self.dragging_node:
            self.dragging_node.stop_drag()
            self.dragging_node = None
            print("  → Parou de arrastar")

    def _finish_connection(self, x, y):
        """
        Finaliza criação de conexão ao soltar mouse em uma porta de entrada.

        Args:
            x, y: Posição onde soltou o mouse
        """
        # Verificar se soltou em uma porta de ENTRADA
        for node in reversed(self.nodes):
            port_index = self._get_input_port_at(node, x, y)
            if port_index is not None:
                # Soltou em uma porta de entrada válida!
                # Criar a conexão
                new_connection = (
                    self.connection_start_node,
                    self.connection_start_port,
                    node,
                    port_index
                )

                # Verificar se já existe essa conexão
                if new_connection not in self.connections:
                    self.connections.append(new_connection)
                    print(f"✅ Conexão criada: {self.connection_start_node.title}.out[{self.connection_start_port}] → {node.title}.in[{port_index}]")
                else:
                    print(f"⚠️  Conexão já existe")

                return

        # Se chegou aqui, não soltou em uma porta válida
        print(f"❌ Conexão cancelada (não soltou em porta de entrada)")

    def on_drag_begin(self, gesture, start_x, start_y):
        """Quando começa a arrastar"""
        # Verificar se começou a arrastar sobre um nó
        for node in reversed(self.nodes):
            if node.contains_point(start_x, start_y):
                self.dragging_node = node
                self.dragging_node.start_drag(start_x, start_y)
                print(f"Começou a arrastar: {node.title}")
                break

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Enquanto arrasta"""
        if self.dragging_node:
            # Pegar posição inicial do drag
            success, start_x, start_y = gesture.get_start_point()
            if success:
                # Calcular posição atual
                current_x = start_x + offset_x
                current_y = start_y + offset_y
                # Atualizar posição do nó
                self.dragging_node.update_drag(current_x, current_y)
                self.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Quando termina de arrastar"""
        if self.dragging_node:
            self.dragging_node.stop_drag()
            print(f"  → Nova posição: ({self.dragging_node.x:.0f}, {self.dragging_node.y:.0f})")
            self.dragging_node = None

    def on_mouse_motion(self, controller, x, y):
        """Quando o mouse se move (para hover)"""
        # Se está criando conexão, atualizar posição do mouse
        if self.creating_connection:
            self.connection_mouse_pos = (x, y)
            self.queue_draw()
            return

        # Verificar se está sobre algum nó
        found_hover = False
        for node in reversed(self.nodes):
            if node.contains_point(x, y):
                if node != self.hovered_node:
                    # Entrou em um novo nó
                    if self.hovered_node:
                        self.hovered_node.set_hovered(False)
                    node.set_hovered(True)
                    self.hovered_node = node
                    self.queue_draw()
                found_hover = True
                break

        # Se não está sobre nenhum nó, limpar hover
        if not found_hover and self.hovered_node:
            self.hovered_node.set_hovered(False)
            self.hovered_node = None
            self.queue_draw()

    def on_draw(self, area, context, width, height):
        """Desenha o canvas e todos os nós"""
        # Fundo branco
        context.set_source_rgb(1, 1, 1)
        context.paint()

        # Grid de fundo sutil
        context.set_source_rgb(0.96, 0.96, 0.96)
        context.set_line_width(1)

        for x in range(0, width, 20):
            context.move_to(x, 0)
            context.line_to(x, height)
        for y in range(0, height, 20):
            context.move_to(0, y)
            context.line_to(width, y)
        context.stroke()

        # Desenhar todos os nós
        for node in self.nodes:
            node.draw(context)

        # Desenhar algumas conexões de exemplo (linhas entre portas)
        self._draw_example_connections(context)

    def _draw_example_connections(self, context):
        """Desenha todas as conexões armazenadas"""
        context.set_line_width(3)
        context.set_source_rgba(0.3, 0.6, 0.9, 0.8)  # Azul semi-transparente

        # Desenhar cada conexão da lista
        for source_node, out_port, target_node, in_port in self.connections:
            # Pegar posições das portas
            start = source_node.get_output_port_position(out_port)
            end = target_node.get_input_port_position(in_port)

            # Desenhar se ambas as portas existem
            if start and end:
                self._draw_connection(context, start, end)

        # Se está criando uma conexão, desenhar linha temporária
        if self.creating_connection and self.connection_start_node:
            start = self.connection_start_node.get_output_port_position(self.connection_start_port)
            if start:
                # Linha temporária em cor diferente (verde/amarelo)
                context.set_line_width(3)
                context.set_source_rgba(0.3, 0.8, 0.3, 0.7)  # Verde semi-transparente
                self._draw_connection(context, start, self.connection_mouse_pos)

    def _draw_connection(self, context, start, end):
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


class AssetsWindow(Gtk.ApplicationWindow):
    """Janela principal"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(900, 600)

        # Header
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Canvas
        self.canvas = AssetsCanvas()
        self.set_child(self.canvas)

        print("✓ Janela criada")

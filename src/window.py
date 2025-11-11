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
from gi.repository import Gdk

import cairo

from .node import Node


class AssetsCanvas(Gtk.DrawingArea):
    """Canvas que desenha os nós"""

    def __init__(self):
        super().__init__()
        self.set_draw_func(self.on_draw)

        # Criar alguns nós de exemplo
        self.nodes = []

        # Armazenar conexões como: (nó_origem, porta_saída, nó_destino, porta_entrada)
        # Guarda REFERÊNCIAS aos nós, não índices!
        self.connections = []

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
        self.selected_connection = None  # Conexão selecionada (tupla ou None)

        # Estado de zoom e pan
        self.zoom_level = 1.0  # 1.0 = 100%, 0.5 = 50%, 2.0 = 200%
        self.pan_offset_x = 0  # Offset horizontal do canvas
        self.pan_offset_y = 0  # Offset vertical do canvas
        self.panning = False  # Está arrastando o canvas?
        self.pan_start_x = 0
        self.pan_start_y = 0

        # Configurar eventos de mouse
        self._setup_mouse_events()

        # Configurar eventos de teclado
        self._setup_keyboard_events()

        # print(f"✓ Canvas criado com {len(self.nodes)} nós")
        # print(f"✓ {len(self.connections)} conexões criadas")
        # print("  - Clique para selecionar")
        # print("  - Arraste para mover")
        # print("  - TAB/Shift+TAB para navegar")
        # print("  - Setas para mover nó focado")
        # print("  - Delete para remover nó focado")
        # print("  - Ctrl+C para copiar")
        # print("  - Ctrl+V para colar")
        # print("  - Ctrl+D para duplicar")

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

        # Scroll (zoom)
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
        )
        scroll_controller.connect("scroll", self.on_scroll)
        self.add_controller(scroll_controller)

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

    def _screen_to_canvas(self, screen_x, screen_y):
        """
        Converte coordenadas da tela para coordenadas do canvas (com zoom e pan).

        Args:
            screen_x, screen_y: Coordenadas na tela

        Returns:
            tuple: (canvas_x, canvas_y)
        """
        canvas_x = (screen_x - self.pan_offset_x) / self.zoom_level
        canvas_y = (screen_y - self.pan_offset_y) / self.zoom_level
        return (canvas_x, canvas_y)

    def _canvas_to_screen(self, canvas_x, canvas_y):
        """
        Converte coordenadas do canvas para coordenadas da tela.

        Args:
            canvas_x, canvas_y: Coordenadas no canvas

        Returns:
            tuple: (screen_x, screen_y)
        """
        screen_x = canvas_x * self.zoom_level + self.pan_offset_x
        screen_y = canvas_y * self.zoom_level + self.pan_offset_y
        return (screen_x, screen_y)

    def on_mouse_pressed(self, gesture, n_press, x, y):
        """Quando o mouse é pressionado"""
        # IMPORTANTE: Dar foco ao canvas quando clica nele
        self.grab_focus()

        # Converter para coordenadas do canvas
        canvas_x, canvas_y = self._screen_to_canvas(x, y)
#        print(f"Click em tela ({x:.0f}, {y:.0f}) → canvas ({canvas_x:.0f}, {canvas_y:.0f})")

        # Primeiro, verificar se clicou em uma porta de ENTRADA (para remover conexões - Opção C)
        for node in reversed(self.nodes):
            port_index = self._get_input_port_at(node, canvas_x, canvas_y)
            if port_index is not None:
                # Clicou em porta de entrada - remover todas conexões dessa porta
 #               print(f"👆 Clicou em porta de ENTRADA: {node.title}.in[{port_index}]")
                self._remove_connections_to_input_port(node, port_index)
                self.queue_draw()
                return

        # Segundo, verificar se clicou em uma porta de SAÍDA (para criar conexão)
        for node in reversed(self.nodes):
            port_index = self._get_output_port_at(node, canvas_x, canvas_y)
            if port_index is not None:
                # Clicou em uma porta de saída - iniciar criação de conexão
                self.creating_connection = True
                self.connection_start_node = node
                self.connection_start_port = port_index
                self.connection_mouse_pos = (canvas_x, canvas_y)
  #              print(f"🔗 Iniciando conexão de {node.title}.out[{port_index}]")
                self.queue_draw()
                return

        # Terceiro, verificar se clicou em uma CONEXÃO (linha - Opção A)
        clicked_connection = self._get_connection_at_point(canvas_x, canvas_y)
        if clicked_connection:
            self.selected_connection = clicked_connection
   #         print(f"🔗 Conexão selecionada: {clicked_connection[0].title}.out[{clicked_connection[1]}] → {clicked_connection[2].title}.in[{clicked_connection[3]}]")
            self.queue_draw()
            return
        else:
            # Não clicou em conexão - limpar seleção de conexão
            self.selected_connection = None

        # Quarto, verificar se clicou em algum nó (corpo do nó, não porta)
        clicked_node = None
        for node in reversed(self.nodes):
            if node.contains_point(canvas_x, canvas_y):
                clicked_node = node
                break

        # Desselecionar todos
        for node in self.nodes:
            node.set_selected(False)

        # Selecionar o clicado e trazer para frente (z-order)
        if clicked_node:
            clicked_node.set_selected(True)
    #        print(f"  → Selecionou: {clicked_node.title}")

            # Z-order: mover nó para o final da lista (desenha por último = fica em cima)
            self.bring_to_front(clicked_node)

            # Atualizar índice de foco para o nó clicado
            self.focused_node_index = self.nodes.index(clicked_node)
        else:
            # Clicou no vazio - iniciar pan (arrastar canvas)
            self.panning = True
            self.pan_start_x = x
            self.pan_start_y = y
            self.focused_node_index = -1

        self.queue_draw()

    def on_scroll(self, controller, dx, dy):
        """
        Callback para scroll do mouse (usado para zoom).

        Args:
            controller: EventControllerScroll
            dx: Delta horizontal (não usado)
            dy: Delta vertical (negativo = scroll up = zoom in)

        Returns:
            bool: True se processou o evento
        """
        # Zoom com scroll
        zoom_speed = 0.1
        old_zoom = self.zoom_level

        if dy < 0:  # Scroll up = zoom in
            self.zoom_level = min(self.zoom_level * (1 + zoom_speed), 3.0)  # Max 300%
        else:  # Scroll down = zoom out
            self.zoom_level = max(self.zoom_level * (1 - zoom_speed), 0.3)  # Min 30%

        if old_zoom != self.zoom_level:
#            print(f"🔍 Zoom: {self.zoom_level * 100:.0f}%")
            self.queue_draw()

        return True

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

    def _get_connection_at_point(self, x, y):
        """
        Verifica se (x, y) está próximo a alguma conexão (linha).

        Args:
            x, y: Coordenadas do clique

        Returns:
            tuple: Conexão (source_node, out_port, target_node, in_port) ou None
        """
        click_tolerance = 8  # Pixels de tolerância para clicar na linha

        for connection in self.connections:
            source_node, out_port, target_node, in_port = connection

            # Pegar posições das portas
            start = source_node.get_output_port_position(out_port)
            end = target_node.get_input_port_position(in_port)

            if not start or not end:
                continue

            # Verificar se o ponto está próximo da linha (usando curva Bezier simplificada)
            if self._point_near_bezier(x, y, start, end, click_tolerance):
                return connection

        return None

    def _point_near_bezier(self, px, py, start, end, tolerance):
        """
        Verifica se um ponto está próximo a uma curva Bezier.
        Usa aproximação por segmentos de linha.

        Args:
            px, py: Ponto a testar
            start: (x1, y1) ponto inicial
            end: (x2, y2) ponto final
            tolerance: Distância máxima em pixels

        Returns:
            bool: True se o ponto está próximo da curva
        """
        x1, y1 = start
        x2, y2 = end

        # Calcular pontos de controle (mesma lógica do _draw_connection)
        distance = abs(x2 - x1)
        offset = min(distance * 0.5, 100)
        ctrl1_x = x1 + offset
        ctrl1_y = y1
        ctrl2_x = x2 - offset
        ctrl2_y = y2

        # Aproximar curva Bezier com segmentos de linha
        num_samples = 20
        for i in range(num_samples):
            t = i / num_samples
            t_next = (i + 1) / num_samples

            # Ponto atual na curva
            bx = (1-t)**3 * x1 + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * x2
            by = (1-t)**3 * y1 + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * y2

            # Próximo ponto
            bx_next = (1-t_next)**3 * x1 + 3*(1-t_next)**2*t_next * ctrl1_x + 3*(1-t_next)*t_next**2 * ctrl2_x + t_next**3 * x2
            by_next = (1-t_next)**3 * y1 + 3*(1-t_next)**2*t_next * ctrl1_y + 3*(1-t_next)*t_next**2 * ctrl2_y + t_next**3 * y2

            # Distância do ponto ao segmento de linha
            dist = self._point_to_segment_distance(px, py, bx, by, bx_next, by_next)
            if dist <= tolerance:
                return True

        return False

    def _point_to_segment_distance(self, px, py, x1, y1, x2, y2):
        """Calcula distância de um ponto a um segmento de linha"""
        # Vetor do segmento
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            # Segmento é um ponto
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

        # Projeção do ponto no segmento (parametrizada entre 0 e 1)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        # Ponto mais próximo no segmento
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy

        # Distância
        return ((px - closest_x) ** 2 + (py - closest_y) ** 2) ** 0.5

    def _remove_connections_to_input_port(self, node, port_index):
        """
        Remove todas as conexões que chegam em uma porta de entrada específica (Opção C).

        Args:
            node: Nó com a porta de entrada
            port_index: Índice da porta de entrada
        """
        # Filtrar conexões que NÃO vão para essa porta
        before_count = len(self.connections)
        self.connections = [
            conn for conn in self.connections
            if not (conn[2] == node and conn[3] == port_index)
        ]
        removed_count = before_count - len(self.connections)

        # if removed_count > 0:
        #     print(f"✂️  Removidas {removed_count} conexão(ões) de {node.title}.in[{port_index}]")
        # else:
        #     print(f"⚠️  Nenhuma conexão em {node.title}.in[{port_index}]")

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
            # print(f"  → Trouxe para frente: {node.title}")

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

        # Delete - Remover nó focado OU conexão selecionada
        if keyval == Gdk.KEY_Delete:
            # Prioridade: se tem conexão selecionada, remove ela
            if self.selected_connection:
                self._delete_selected_connection()
            else:
                # Senão, remove nó focado
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
        # print(f"Foco → {self.nodes[self.focused_node_index].title}")
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
        # print(f"Foco ← {self.nodes[self.focused_node_index].title}")
        self.queue_draw()

    def _clear_selection(self):
        """Deseleciona todos os nós (Escape)"""
        for node in self.nodes:
            node.set_selected(False)
        self.focused_node_index = -1
        # print("Seleção limpa")
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
          #  print(f"✗ Removido: {node_to_delete.title}")

            # Ajustar índice de foco
            if self.focused_node_index >= len(self.nodes):
                self.focused_node_index = len(self.nodes) - 1

            self.queue_draw()

    def _delete_selected_connection(self):
        """Remove a conexão selecionada (Delete - Opção A)"""
        if self.selected_connection and self.selected_connection in self.connections:
            source_node, out_port, target_node, in_port = self.selected_connection
            self.connections.remove(self.selected_connection)
           # print(f"✂️  Conexão removida: {source_node.title}.out[{out_port}] → {target_node.title}.in[{in_port}]")
            self.selected_connection = None
            self.queue_draw()

    def _copy_focused_node(self):
        """Copia o nó focado para o clipboard (Ctrl+C)"""
        if 0 <= self.focused_node_index < len(self.nodes):
            self.clipboard_node = self.nodes[self.focused_node_index]
            #print(f"📋 Copiado: {self.clipboard_node.title}")
        #else:
            #print("⚠️  Nenhum nó selecionado para copiar")

    def _paste_node(self):
        """Cola o nó do clipboard (Ctrl+V)"""
        if self.clipboard_node is None:
            #print("⚠️  Clipboard vazio")
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

        #print(f"📌 Colado: {new_node.title} em ({new_node.x:.0f}, {new_node.y:.0f})")
        #print(f"   Foco atualizado para índice {self.focused_node_index}")
        self.queue_draw()

    def _duplicate_focused_node(self):
        """Duplica o nó focado (Ctrl+D) - atalho para copiar+colar"""
        if 0 <= self.focused_node_index < len(self.nodes):
            # Copiar
            self._copy_focused_node()
            # Colar imediatamente
            self._paste_node()
        #else:
         #   print("⚠️  Nenhum nó selecionado para duplicar")

    def execute_graph(self):
        """
        Executa o grafo completo em ordem topológica.

        Returns:
            bool: True se execução foi bem sucedida, False caso contrário
        """
        if not self.nodes:
            print("⚠️  Nenhum nó para executar")
            return False

        # 1. Resolver ordem topológica
        execution_order = self._topological_sort()

        if execution_order is None:
            print("❌ Erro: Grafo contém ciclos! Não é possível executar.")
            return False

        print(f"📋 Ordem de execução: {[node.title for node in execution_order]}")
        print()

        # 2. Dicionário para armazenar resultados de cada nó
        node_results = {}

        # 3. Executar cada nó em ordem
        for i, node in enumerate(execution_order, 1):
          #  print(f"[{i}/{len(execution_order)}] Executando: {node.title}")

            try:
                # Coletar inputs deste nó
                inputs = self._collect_node_inputs(node, node_results)

                # Executar código do nó
                outputs = self._execute_node_code(node, inputs)

                # Armazenar resultados
                node_results[node] = outputs

           #     print(f"  ✓ Saídas: {outputs}")

            except Exception as e:
                print(f"  ❌ Erro ao executar nó: {e}")
                import traceback
                traceback.print_exc()
                return False

        return True

    def _topological_sort(self):
        """
        Ordena os nós em ordem topológica (dependências primeiro).

        Returns:
            list: Lista de nós em ordem de execução, ou None se houver ciclos
        """
        # Construir grafo de dependências
        in_degree = {node: 0 for node in self.nodes}
        adjacency = {node: [] for node in self.nodes}

        for source_node, out_port, target_node, in_port in self.connections:
            adjacency[source_node].append(target_node)
            in_degree[target_node] += 1

        # Algoritmo de Kahn para ordenação topológica
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Se não processou todos os nós, há ciclos
        if len(result) != len(self.nodes):
            return None

        return result

    def _collect_node_inputs(self, node, node_results):
        """
        Coleta os inputs de um nó a partir dos resultados dos nós anteriores.

        Args:
            node: Nó cujos inputs serão coletados
            node_results: Dicionário com resultados dos nós já executados

        Returns:
            tuple: Tupla com os inputs do nó
        """
        # Inicializar lista de inputs (um por porta de entrada)
        inputs = [None] * node.num_inputs

        # Preencher inputs baseado nas conexões
        for source_node, out_port, target_node, in_port in self.connections:
            if target_node == node:
                # Esta conexão fornece input para este nó
                if source_node in node_results:
                    source_outputs = node_results[source_node]
                    if out_port < len(source_outputs):
                        inputs[in_port] = source_outputs[out_port]

        return tuple(inputs)

    def _execute_node_code(self, node, inputs):
        """
        Executa o código Python de um nó.

        Args:
            node: Nó a ser executado
            inputs: Tupla com inputs do nó

        Returns:
            tuple: Tupla com outputs do nó
        """
        if not node.code or node.code.strip() == "":
            print(f"  ⚠️  Nó sem código, retornando inputs como outputs")
            return inputs

        # Transformar o código em uma função
        # O código já está escrito como corpo de função (com return)
        code_as_function = "def __node_function(inputs):\n"
        for line in node.code.split('\n'):
            code_as_function += f"    {line}\n"

        namespace = {'__builtins__': __builtins__}
        exec(code_as_function, namespace)

        # Chamar a função com os inputs
        result = namespace['__node_function'](inputs)

        # Garantir que retorno é tupla
        if not isinstance(result, tuple):
            result = (result,)

        return result

    def on_mouse_released(self, gesture, n_press, x, y):
        """Quando o mouse é solto"""
        canvas_x, canvas_y = self._screen_to_canvas(x, y)

        # Se estava criando conexão, tentar finalizar
        if self.creating_connection:
            self._finish_connection(canvas_x, canvas_y)
            self.creating_connection = False
            self.connection_start_node = None
            self.connection_start_port = None
            self.queue_draw()
            return

        # Se estava fazendo pan
        if self.panning:
            self.panning = False
            return

        # Se estava arrastando nó
        if self.dragging_node:
            self.dragging_node.stop_drag()
            self.dragging_node = None
            # print("  → Parou de arrastar")

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
                    # print(f"✅ Conexão criada: {self.connection_start_node.title}.out[{self.connection_start_port}] → {node.title}.in[{port_index}]")
                # else:
                    # print(f"⚠️  Conexão já existe")

                # return

        # Se chegou aqui, não soltou em uma porta válida
        # print(f"❌ Conexão cancelada (não soltou em porta de entrada)")

    def on_drag_begin(self, gesture, start_x, start_y):
        """Quando começa a arrastar"""
        canvas_x, canvas_y = self._screen_to_canvas(start_x, start_y)

        # Se está fazendo pan, não arrastar nós
        if self.panning:
            return

        # Verificar se começou a arrastar sobre um nó
        for node in reversed(self.nodes):
            if node.contains_point(canvas_x, canvas_y):
                self.dragging_node = node
                self.dragging_node.start_drag(canvas_x, canvas_y)
            #    print(f"Começou a arrastar: {node.title}")
                break

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Enquanto arrasta"""
        # Pegar posição inicial do drag
        (_, start_x, start_y) = gesture.get_start_point()

        # Se está fazendo pan do canvas
        if self.panning:
            self.pan_offset_x = (start_x + offset_x) - self.pan_start_x + self.pan_offset_x
            self.pan_offset_y = (start_y + offset_y) - self.pan_start_y + self.pan_offset_y
            self.pan_start_x = start_x + offset_x
            self.pan_start_y = start_y + offset_y
            self.queue_draw()
            return

        # Se está arrastando um nó
        if self.dragging_node:
            # Calcular posição atual
            current_x = start_x + offset_x
            current_y = start_y + offset_y
            canvas_x, canvas_y = self._screen_to_canvas(current_x, current_y)
            # Atualizar posição do nó
            self.dragging_node.update_drag(canvas_x, canvas_y)
            self.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Quando termina de arrastar"""
        if self.dragging_node:
            self.dragging_node.stop_drag()
            #print(f"  → Nova posição: ({self.dragging_node.x:.0f}, {self.dragging_node.y:.0f})")
            self.dragging_node = None

    def on_mouse_motion(self, controller, x, y):
        """Quando o mouse se move (para hover)"""
        canvas_x, canvas_y = self._screen_to_canvas(x, y)

        # Se está criando conexão, atualizar posição do mouse
        if self.creating_connection:
            self.connection_mouse_pos = (canvas_x, canvas_y)
            self.queue_draw()
            return

        # Verificar se está sobre algum nó
        found_hover = False
        for node in reversed(self.nodes):
            if node.contains_point(canvas_x, canvas_y):
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

        # Salvar estado do contexto
        context.save()

        # Aplicar transformações de pan e zoom
        context.translate(self.pan_offset_x, self.pan_offset_y)
        context.scale(self.zoom_level, self.zoom_level)

        # Grid de fundo sutil (ajustado para zoom)
        context.set_source_rgb(0.96, 0.96, 0.96)
        context.set_line_width(1 / self.zoom_level)  # Linha sempre fina

        grid_size = 20
        # Calcular limites visíveis do grid
        start_x = int(-self.pan_offset_x / self.zoom_level / grid_size) * grid_size
        start_y = int(-self.pan_offset_y / self.zoom_level / grid_size) * grid_size
        end_x = int((width - self.pan_offset_x) / self.zoom_level) + grid_size
        end_y = int((height - self.pan_offset_y) / self.zoom_level) + grid_size

        for x in range(start_x, end_x, grid_size):
            context.move_to(x, start_y)
            context.line_to(x, end_y)
        for y in range(start_y, end_y, grid_size):
            context.move_to(start_x, y)
            context.line_to(end_x, y)
        context.stroke()

        # Desenhar todos os nós
        for node in self.nodes:
            node.draw(context)

        # Desenhar conexões
        self._draw_example_connections(context)

        # Restaurar estado do contexto
        context.restore()

        # Desenhar info de zoom/pan (fora da transformação)
        context.set_source_rgb(0.3, 0.3, 0.3)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(11)
        info_text = f"Zoom: {self.zoom_level * 100:.0f}% | Pan: ({self.pan_offset_x:.0f}, {self.pan_offset_y:.0f}) | Scroll para zoom, Arraste vazio para pan"
        context.move_to(10, height - 10)
        context.show_text(info_text)

    def _draw_example_connections(self, context):
        """Desenha todas as conexões armazenadas"""

        # Desenhar cada conexão da lista
        for connection in self.connections:
            source_node, out_port, target_node, in_port = connection

            # Pegar posições das portas
            start = source_node.get_output_port_position(out_port)
            end = target_node.get_input_port_position(in_port)

            # Desenhar se ambas as portas existem
            if start and end:
                # Cor diferente se está selecionada
                if connection == self.selected_connection:
                    context.set_line_width(4)
                    context.set_source_rgba(1.0, 0.3, 0.3, 0.9)  # Vermelho para selecionada
                else:
                    context.set_line_width(3)
                    context.set_source_rgba(0.3, 0.6, 0.9, 0.8)  # Azul normal

                self._draw_connection(context, start, end)

        # Se está criando uma conexão, desenhar linha temporária
        if self.creating_connection and self.connection_start_node:
            start = self.connection_start_node.get_output_port_position(self.connection_start_port)
            if start:
                # Linha temporária em cor diferente (verde)
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
        self.set_default_size(1200, 700)

        # Header
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Botão toggle para mostrar/esconder biblioteca
        self.library_button = Gtk.ToggleButton(label="📚 Library")
        self.library_button.set_active(True)
        self.library_button.connect("toggled", self.on_library_toggle)
        header.pack_start(self.library_button)

        # Botão Run para executar o grafo
        self.run_button = Gtk.Button(label="▶️ Run")
        self.run_button.connect("clicked", self.on_run_clicked)
        header.pack_end(self.run_button)

        # Layout principal com Paned (divisor)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.paned)

        # Painel esquerdo - Biblioteca de nós
        self.library_panel = self._create_library_panel()
        self.paned.set_start_child(self.library_panel)
        self.paned.set_resize_start_child(False)
        self.paned.set_shrink_start_child(False)

        # Canvas
        self.canvas = AssetsCanvas()
        self.paned.set_end_child(self.canvas)
        self.paned.set_resize_end_child(True)
        self.paned.set_shrink_end_child(False)

        # Posição inicial do divisor
        self.paned.set_position(250)

        # IMPORTANTE: Garantir que canvas tenha foco para receber atalhos de teclado
        # Usar GLib.idle_add para garantir que aconteça depois da janela estar pronta
        from gi.repository import GLib
        GLib.idle_add(self.canvas.grab_focus)

#        print("✓ Janela criada")

    def _create_library_panel(self):
        """Cria o painel da biblioteca de nós"""
        from .node_library import get_all_categories, get_nodes_in_category, get_category_icon

        # Box principal do painel
        panel_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        panel_box.set_size_request(250, -1)

        # Header do painel
        panel_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        panel_header.set_margin_top(12)
        panel_header.set_margin_bottom(12)
        panel_header.set_margin_start(12)
        panel_header.set_margin_end(12)

        header_label = Gtk.Label(label="Node Library")
        header_label.set_markup("<b>Node Library</b>")
        header_label.set_xalign(0)
        panel_header.append(header_label)

        panel_box.append(panel_header)
        panel_box.append(Gtk.Separator())

        # ScrolledWindow para a lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Box para as categorias
        categories_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        categories_box.set_margin_top(12)
        categories_box.set_margin_bottom(12)
        categories_box.set_margin_start(12)
        categories_box.set_margin_end(12)

        # Criar seções para cada categoria
        for category in get_all_categories():
            icon = get_category_icon(category)

            # Header da categoria
            category_header = Gtk.Label()
            category_header.set_markup(f"<b>{icon} {category}</b>")
            category_header.set_xalign(0)
            category_header.set_margin_top(6)
            categories_box.append(category_header)

            # Nós da categoria
            nodes = get_nodes_in_category(category)
            for node_template in nodes:
                node_button = Gtk.Button(label=node_template["name"])
                node_button.set_has_frame(False)
                node_button.set_halign(Gtk.Align.START)  # GTK4 usa set_halign
                node_button.set_tooltip_text(node_template["description"])
                node_button.connect("clicked", self.on_node_template_clicked, node_template)
                categories_box.append(node_button)

        scrolled.set_child(categories_box)
        panel_box.append(scrolled)

        # Instruções no rodapé
        instructions = Gtk.Label()
        instructions.set_markup("<small>Click to add node to center</small>")
        instructions.set_margin_top(6)
        instructions.set_margin_bottom(6)
        panel_box.append(Gtk.Separator())
        panel_box.append(instructions)

        return panel_box

    def on_library_toggle(self, button):
        """Toggle visibilidade da biblioteca"""
        if button.get_active():
            self.library_panel.set_visible(True)
            self.paned.set_position(250)
        else:
            self.library_panel.set_visible(False)
            self.paned.set_position(0)

    def on_node_template_clicked(self, button, template):
        """Quando clica em um template na biblioteca"""
        from .node_library import create_node_from_template

        # Criar nó no centro do canvas visível
        # Calcular posição central considerando zoom e pan
        center_x = (400 - self.canvas.pan_offset_x) / self.canvas.zoom_level
        center_y = (300 - self.canvas.pan_offset_y) / self.canvas.zoom_level

        new_node = create_node_from_template(template, center_x, center_y)
        self.canvas.nodes.append(new_node)

        # Selecionar o novo nó
        for node in self.canvas.nodes:
            node.set_selected(False)
        new_node.set_selected(True)
        self.canvas.focused_node_index = len(self.canvas.nodes) - 1

 #       print(f"✓ Adicionado: {template['name']}")
        self.canvas.queue_draw()

        # Retornar foco para o canvas para atalhos funcionarem
        self.canvas.grab_focus()

    def on_run_clicked(self, button):
        """Quando clica no botão Run - executa o grafo"""
#        print("\n" + "=" * 60)
#        print("▶️  EXECUTANDO GRAFO")
#        print("=" * 60)

        # Executar o grafo
        success = self.canvas.execute_graph()

        if success:
            print("=" * 60)
            print("✅ EXECUÇÃO CONCLUÍDA COM SUCESSO")
            print("=" * 60 + "\n")
        else:
            print("=" * 60)
            print("❌ EXECUÇÃO FALHOU")
            print("=" * 60 + "\n")

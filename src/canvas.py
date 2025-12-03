from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio

import cairo
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .node import Node
from .node_dialogs import CodeEditorDialog, RenameNodeDialog, NodePropertiesDialog, SaveToLibraryDialog
from .graph_io import GraphSerializer, get_default_save_directory
from .node_library import _get_library
from .output_panel import OutputPanel
from .undo_redo import UndoRedoManager
from .data_helpers import create_data_helpers, process_folder_output

class AssetsCanvas(Gtk.DrawingArea):
    """Canvas que desenha os nós"""

    def __init__(self):
        super().__init__()
        self.set_draw_func(self.on_draw)

        # Inicializar GSettings para cores
        try:
            from pathlib import Path
            import os
            # Para desenvolvimento: usar schema local se não instalado
            schema_dir = Path(__file__).parent.parent / "data"
            if schema_dir.exists():
                os.environ['GSETTINGS_SCHEMA_DIR'] = str(schema_dir)

            self.settings = Gio.Settings.new("com.github.sheep.farm.assets")
            self.settings.connect("changed", self._on_settings_changed)
        except Exception as e:
            print(f"Warning: Could not load GSettings: {e}")
            self.settings = None

        # Criar alguns nós de exemplo
        self.nodes = []

        # Armazenar conexões como: (nó_origem, porta_saída, nó_destino, porta_entrada)
        # Guarda REFERÊNCIAS aos nós, não índices!
        self.connections = []

        # Estado de interação
        self.dragging_node = None
        self.hovered_node = None
        self.focused_node_index = -1  # Índice do nó com foco (-1 = nenhum)

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
        self.space_pressed = False  # Se a tecla Espaço está pressionada

        # Estado de seleção de região
        self.selecting_region = False  # Está selecionando região?
        self.selection_start_x = 0
        self.selection_start_y = 0
        self.selection_current_x = 0
        self.selection_current_y = 0

        # Estado de focus (destacar nó e conexões)
        self.focus_node = None  # Nó em focus (None = sem focus)
        self.focus_nodes_set = set()  # Set de nós destacados (nó focado + N níveis)
        self.focus_connections_set = set()  # Set de conexões destacadas

        # Configurar eventos de mouse
        self._setup_mouse_events()

        # Configurar eventos de teclado
        self._setup_keyboard_events()

        # Configurar action group para menu de contexto
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("canvas", self.action_group)

        # Inicializar sistema de Undo/Redo
        self.undo_manager = UndoRedoManager(self)
        self._recording_undo = True  # Flag para controlar gravação

        # Posição do menu de contexto (para paste na posição do mouse)
        self.context_menu_position = None

        # Cache de cursores (evitar criar múltiplos cursores e esgotar file descriptors)
        self._cursor_cache = {
            'grab': Gdk.Cursor.new_from_name("grab"),
            'grabbing': Gdk.Cursor.new_from_name("grabbing"),
        }

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

    def _on_settings_changed(self, settings, key):
        """Callback quando uma configuração muda"""
        # Redesenhar canvas quando cores mudarem
        self.queue_draw()

        # Se mudou o focus-depth, recalcular focus
        if key == "focus-depth" and self.focus_node:
            self._calculate_focus_nodes()

    def _calculate_focus_nodes(self):
        """
        Calcula quais nós e conexões devem ser destacados baseado no nó em focus
        e no nível de profundidade configurado.

        Apenas inclui as conexões que fazem parte do CAMINHO entre o nó focado
        e os nós conectados, não todas as conexões dos nós intermediários.
        """
        if not self.focus_node:
            self.focus_nodes_set = set()
            self.focus_connections_set = set()
            return

        # Obter profundidade das configurações
        depth = 1
        if self.settings:
            try:
                depth = self.settings.get_int("focus-depth")
            except:
                depth = 1

        # Inicializar sets
        self.focus_nodes_set = {self.focus_node}
        self.focus_connections_set = set()

        if depth == 0:
            # Apenas o nó focado
            return

        # BFS: apenas adicionar conexões que fazem parte do caminho explorado
        from collections import deque
        queue = deque([(self.focus_node, 0)])
        visited = {self.focus_node}

        while queue:
            current_node, current_level = queue.popleft()

            if current_level >= depth:
                continue

            # Explorar conexões (upstream e downstream)
            for conn in self.connections:
                source_node, source_port, target_node, target_port = conn

                # Downstream: current_node fornece dados para target_node
                if source_node == current_node and target_node not in visited:
                    # Adicionar esta conexão ao caminho
                    self.focus_connections_set.add(conn)
                    visited.add(target_node)
                    self.focus_nodes_set.add(target_node)
                    queue.append((target_node, current_level + 1))

                # Upstream: source_node fornece dados para current_node
                elif target_node == current_node and source_node not in visited:
                    # Adicionar esta conexão ao caminho
                    self.focus_connections_set.add(conn)
                    visited.add(source_node)
                    self.focus_nodes_set.add(source_node)
                    queue.append((source_node, current_level + 1))

    def toggle_focus_node(self, node):
        """
        Ativa/desativa o modo focus em um nó

        Args:
            node: Nó para focar (ou None para limpar)
        """
        if self.focus_node == node:
            # Toggle off
            self.focus_node = None
            self.focus_nodes_set = set()
            self.focus_connections_set = set()
        else:
            # Focus on
            self.focus_node = node
            self._calculate_focus_nodes()

        self.queue_draw()

    def set_focus_node(self, node):
        """
        Define o nó em focus (sem toggle, apenas set)

        Args:
            node: Nó para focar (ou None para limpar)
        """
        if node is None:
            self.focus_node = None
            self.focus_nodes_set = set()
            self.focus_connections_set = set()
        else:
            self.focus_node = node
            self._calculate_focus_nodes()

        self.queue_draw()

    def clear_focus_node(self):
        """Limpa o foco atual"""
        self.set_focus_node(None)

    def _get_color_setting(self, key):
        """
        Obtém uma cor do GSettings

        Args:
            key: Chave da configuração (ex: "canvas-bg-color")

        Returns:
            Tupla (r, g, b) com valores 0.0-1.0
        """
        # Valores padrão caso GSettings não esteja disponível
        defaults = {
            "canvas-bg-color": (0.98, 0.98, 0.98),
            "fine-grid-color": (0.96, 0.96, 0.96),
            "coarse-grid-color": (0.90, 0.90, 0.90),
            "node-body-color": (0.95, 0.95, 0.95),
            "node-border-color": (0.3, 0.3, 0.3),
            "node-selection-color": (0.2, 0.6, 1.0),
            "node-running-color": (0.2, 0.7, 0.5),
            "connection-creating-color": (0.2, 0.7, 0.5),
            "connection-normal-color": (0.35, 0.45, 0.55),
            "connection-selected-color": (1.0, 0.4, 0.2),
            "selection-fill-color": (0.2, 0.5, 0.9),
            "selection-border-color": (0.2, 0.5, 0.9),
        }

        if self.settings:
            try:
                variant = self.settings.get_value(key)
                return variant.unpack()
            except Exception as e:
                print(f"Warning: Could not get setting {key}: {e}")
                return defaults.get(key, (0.5, 0.5, 0.5))
        else:
            return defaults.get(key, (0.5, 0.5, 0.5))

    def _get_opacity_setting(self, key):
        """
        Obtém uma opacidade do GSettings

        Args:
            key: Chave da configuração (ex: "selection-fill-opacity")

        Returns:
            Float 0.0-1.0
        """
        defaults = {
            "selection-fill-opacity": 0.15,
            "selection-border-opacity": 0.6,
        }

        if self.settings:
            try:
                return self.settings.get_double(key)
            except Exception as e:
                print(f"Warning: Could not get setting {key}: {e}")
                return defaults.get(key, 0.5)
        else:
            return defaults.get(key, 0.5)

    def _update_canvas_size(self):
        """Atualiza o tamanho do canvas baseado nos nós e zoom"""
        if not self.nodes:
            # Tamanho padrão se não há nós
            self.set_size_request(int(2000 * self.zoom_level), int(2000 * self.zoom_level))
            return

        # Encontrar limites dos nós (considerando coordenadas absolutas)
        min_x = min(node.x for node in self.nodes)
        min_y = min(node.y for node in self.nodes)
        max_x = max(node.x + node.WIDTH for node in self.nodes)
        max_y = max(node.y + node.HEIGHT_HEADER + node.PADDING +
                   max(node.num_inputs, node.num_outputs) * node.HEIGHT_PORT + node.PADDING
                   for node in self.nodes)

        # Adicionar margem proporcional
        margin = 300

        # Calcular tamanho total baseado no espaço real ocupado
        # Considerando desde min até max (não assumir 0,0)
        width = int((max_x - min(0, min_x) + margin) * self.zoom_level)
        height = int((max_y - min(0, min_y) + margin) * self.zoom_level)

        # Garantir tamanho mínimo razoável
        min_size = 1000
        width = max(width, int(min_size * self.zoom_level))
        height = max(height, int(min_size * self.zoom_level))

        self.set_size_request(width, height)

    def center_view_on_graph(self):
        """Centraliza a visualização no grafo, independente do zoom/pan salvos"""
        if not self.nodes:
            return

        # Calcular bounding box do grafo
        min_x = min(node.x for node in self.nodes)
        min_y = min(node.y for node in self.nodes)
        max_x = max(node.x + node.WIDTH for node in self.nodes)
        max_y = max(node.y + node.HEIGHT_HEADER + node.PADDING +
                   max(node.num_inputs, node.num_outputs) * node.HEIGHT_PORT + node.PADDING
                   for node in self.nodes)

        # Centro do grafo
        graph_center_x = (min_x + max_x) / 2
        graph_center_y = (min_y + max_y) / 2

        # Tamanho da viewport (widget)
        widget_width = self.get_width()
        widget_height = self.get_height()

        # Calcular pan offset para centralizar
        # O centro do grafo (em coordenadas de canvas) deve aparecer no centro da viewport
        self.pan_offset_x = widget_width / 2 - graph_center_x * self.zoom_level
        self.pan_offset_y = widget_height / 2 - graph_center_y * self.zoom_level

        self.queue_draw()

    def _setup_mouse_events(self):
        """Configura controladores de eventos de mouse"""

        # Click - configurar para aceitar TODOS os botões
        click_gesture = Gtk.GestureClick.new()
        click_gesture.set_button(0)  # 0 = todos os botões (esquerdo, direito, meio)
        click_gesture.connect("pressed", self.on_mouse_pressed)
        click_gesture.connect("released", self.on_mouse_released)
        self.add_controller(click_gesture)

        # Drag - botão esquerdo
        drag_gesture = Gtk.GestureDrag.new()
        drag_gesture.set_button(1)  # Botão esquerdo
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
        key_controller.connect("key-released", self.on_key_released)
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

        # Verificar se é clique com botão direito
        button = gesture.get_current_button()

        # Converter para coordenadas do canvas
        canvas_x, canvas_y = self._screen_to_canvas(x, y)

        # Pegar estado dos modificadores (Ctrl, Shift, Alt)
        modifiers = gesture.get_current_event_state()
        ctrl_pressed = modifiers & Gdk.ModifierType.CONTROL_MASK
        shift_pressed = modifiers & Gdk.ModifierType.SHIFT_MASK
        alt_pressed = modifiers & Gdk.ModifierType.ALT_MASK

        # Botão direito: menu de contexto
        if button == 3:  # Botão direito
            # Verificar se está sobre um nó
            for node in reversed(self.nodes):
                if node.contains_point(canvas_x, canvas_y):
                    self._show_node_context_menu(node, x, y)
                    return
            # Se não está sobre nó, mostrar menu de contexto do canvas
            self._show_canvas_context_menu(x, y)
            return

        # Botão esquerdo: nova lógica

        # Primeiro, verificar se clicou em uma porta de ENTRADA (para remover conexões)
        for node in reversed(self.nodes):
            port_index = self._get_input_port_at(node, canvas_x, canvas_y)
            if port_index is not None:
                self._remove_connections_to_input_port(node, port_index)
                self.queue_draw()
                return

        # Segundo, verificar se clicou em uma porta de SAÍDA (para criar conexão)
        for node in reversed(self.nodes):
            port_index = self._get_output_port_at(node, canvas_x, canvas_y)
            if port_index is not None:
                self.creating_connection = True
                self.connection_start_node = node
                self.connection_start_port = port_index
                self.connection_mouse_pos = (canvas_x, canvas_y)
                self.queue_draw()
                return

        # Terceiro, verificar se clicou em algum nó (corpo do nó, não porta)
        # NÓS TÊM PRIORIDADE SOBRE CONEXÕES!
        clicked_node = None
        for node in reversed(self.nodes):
            if node.contains_point(canvas_x, canvas_y):
                clicked_node = node
                break

        if clicked_node:
            # Clicou em um nó
            # Desselecionar conexão se havia uma selecionada
            self.selected_connection = None

            # DUPLO CLIQUE: Abrir editor de código
            if n_press == 2:
                window = self.get_root()
                dialog = CodeEditorDialog(window, clicked_node)
                dialog.on_apply_callback = lambda code: self._on_code_editor_apply(clicked_node, code)
                dialog.present()
                return

            if ctrl_pressed and alt_pressed:
                # Ctrl+Alt+Click: toggle focus mode
                self.toggle_focus_node(clicked_node)
                return

            elif ctrl_pressed:
                # Ctrl+Click: toggle seleção (seleção múltipla)
                clicked_node.set_selected(not clicked_node.selected)
                if clicked_node.selected:
                    self.bring_to_front(clicked_node)
                    self.focused_node_index = self.nodes.index(clicked_node)
            else:
                # Click normal: selecionar este nó (permite arrastar imediatamente)

                # Se está em focus mode, sair dele ao clicar em qualquer nó
                if self.focus_node is not None:
                    self.clear_focus_node()

                # Se não está selecionado, desselecionar outros
                if not clicked_node.selected:
                    for node in self.nodes:
                        node.set_selected(False)
                    clicked_node.set_selected(True)
                # Se já está selecionado, manter a seleção (útil para Shift+drag múltiplo)
                self.bring_to_front(clicked_node)
                self.focused_node_index = self.nodes.index(clicked_node)
        else:
            # Não clicou em um nó - verificar se clicou em uma CONEXÃO (linha)
            clicked_connection = self._get_connection_at_point(canvas_x, canvas_y)
            if clicked_connection:
                self.selected_connection = clicked_connection
                self.queue_draw()
                return
            else:
                self.selected_connection = None

            # Clicou no vazio
            if not ctrl_pressed:
                # Se não está com Ctrl, iniciar seleção de região
                self.selecting_region = True
                self.selection_start_x = canvas_x
                self.selection_start_y = canvas_y
                self.selection_current_x = canvas_x
                self.selection_current_y = canvas_y

                # Desselecionar todos se não está com Ctrl
                for node in self.nodes:
                    node.set_selected(False)

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
            self._update_canvas_size()
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

    def _select_nodes_in_region(self):
        """Seleciona todos os nós dentro do retângulo de seleção"""
        # Calcular limites do retângulo
        x1 = min(self.selection_start_x, self.selection_current_x)
        y1 = min(self.selection_start_y, self.selection_current_y)
        x2 = max(self.selection_start_x, self.selection_current_x)
        y2 = max(self.selection_start_y, self.selection_current_y)

        # Selecionar nós cujo centro está dentro do retângulo
        for node in self.nodes:
            node_center_x = node.x + node.WIDTH / 2
            node_center_y = node.y + node.HEIGHT_HEADER / 2

            if x1 <= node_center_x <= x2 and y1 <= node_center_y <= y2:
                node.set_selected(True)

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

        # Espaço - Ativar modo de pan
        if keyval == Gdk.KEY_space:
            if not self.space_pressed:
                self.space_pressed = True
                self.set_cursor(self._cursor_cache['grab'])
            return True

        # Verificar se Ctrl está pressionado
        ctrl_pressed = state & Gdk.ModifierType.CONTROL_MASK

        # Ctrl+A - Selecionar todos os nós
        if ctrl_pressed and keyval == Gdk.KEY_a:
            self._select_all_nodes()
            return True

        # Ctrl+C - Copiar nós selecionados
        if ctrl_pressed and keyval == Gdk.KEY_c:
            self._copy_focused_node()
            return True

        # Ctrl+V - Colar nós do clipboard
        if ctrl_pressed and keyval == Gdk.KEY_v:
            self._paste_node()
            return True

        # Ctrl+D - Duplicar nós selecionados
        if ctrl_pressed and keyval == Gdk.KEY_d:
            self._duplicate_focused_node()
            return True

        # Ctrl+Z - Undo
        if ctrl_pressed and keyval == Gdk.KEY_z:
            self.undo_manager.undo()
            return True

        # Ctrl+Y ou Ctrl+Shift+Z - Redo
        if ctrl_pressed and (keyval == Gdk.KEY_y or
                            (keyval == Gdk.KEY_z and state & Gdk.ModifierType.SHIFT_MASK)):
            self.undo_manager.redo()
            return True

        # E - Editar código do nó focado
        if keyval == Gdk.KEY_e and not ctrl_pressed:
            if 0 <= self.focused_node_index < len(self.nodes):
                self.context_menu_node = self.nodes[self.focused_node_index]
                self.edit_node_code()
                return True

        # R - Renomear nó focado
        if keyval == Gdk.KEY_r and not ctrl_pressed:
            if 0 <= self.focused_node_index < len(self.nodes):
                self.context_menu_node = self.nodes[self.focused_node_index]
                self.rename_node()
                return True

        # P - Propriedades do nó focado
        if keyval == Gdk.KEY_p and not ctrl_pressed:
            if 0 <= self.focused_node_index < len(self.nodes):
                self.context_menu_node = self.nodes[self.focused_node_index]
                self.show_node_properties()
                return True

        # F - Toggle focus mode no nó focado
        if keyval == Gdk.KEY_f and not ctrl_pressed:
            if 0 <= self.focused_node_index < len(self.nodes):
                node = self.nodes[self.focused_node_index]
                self.toggle_focus_node(node)
                return True

        # Escape - Limpar focus mode
        if keyval == Gdk.KEY_Escape:
            if self.focus_node:
                self.toggle_focus_node(None)
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

    def on_key_released(self, controller, keyval, keycode, state):
        """
        Processa teclas soltas.

        Args:
            controller: EventControllerKey
            keyval: Valor da tecla (Gdk.KEY_*)
            keycode: Código da tecla
            state: Modificadores

        Returns:
            bool: True se processou a tecla
        """
        # Espaço - Desativar modo de pan
        if keyval == Gdk.KEY_space:
            self.space_pressed = False
            # Finalizar panning se estiver ativo
            if self.panning:
                self.panning = False
            self.set_cursor(None)  # Restaurar cursor padrão
            return True

        return False

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

        # Atualizar focus se em focus mode
        if self.focus_node is not None:
            self.set_focus_node(self.nodes[self.focused_node_index])

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

        # Atualizar focus se em focus mode
        if self.focus_node is not None:
            self.set_focus_node(self.nodes[self.focused_node_index])

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
        """Remove o(s) nó(s) selecionado(s) ou o nó com foco (Delete)"""
        # Verificar se há múltiplos nós selecionados
        selected_nodes = [node for node in self.nodes if node.selected]

        if len(selected_nodes) > 1:
            # Deletar todos os nós selecionados
            if self._recording_undo:
                old_state = self.undo_manager.capture_state()

            # Remover conexões associadas a qualquer nó selecionado
            self.connections = [
                conn for conn in self.connections
                if conn[0] not in selected_nodes and conn[2] not in selected_nodes
            ]

            # Remover todos os nós selecionados
            for node in selected_nodes:
                self.nodes.remove(node)

            # Ajustar índice de foco
            if self.focused_node_index >= len(self.nodes):
                self.focused_node_index = len(self.nodes) - 1

            # Registrar ação no undo
            if self._recording_undo:
                self.undo_manager.record_action(old_state)

            self._update_canvas_size()
            self.queue_draw()

        elif 0 <= self.focused_node_index < len(self.nodes):
            # Deletar apenas o nó com foco
            if self._recording_undo:
                old_state = self.undo_manager.capture_state()

            node_to_delete = self.nodes[self.focused_node_index]

            # Remover conexões associadas ao nó
            self.connections = [
                conn for conn in self.connections
                if conn[0] != node_to_delete and conn[2] != node_to_delete
            ]

            # Remover o nó
            self.nodes.remove(node_to_delete)

            # Ajustar índice de foco
            if self.focused_node_index >= len(self.nodes):
                self.focused_node_index = len(self.nodes) - 1

            # Registrar ação no undo
            if self._recording_undo:
                self.undo_manager.record_action(old_state)

            self._update_canvas_size()
            self.queue_draw()

    def _delete_selected_connection(self):
        """Remove a conexão selecionada (Delete - Opção A)"""
        if self.selected_connection and self.selected_connection in self.connections:
            source_node, out_port, target_node, in_port = self.selected_connection
            self.connections.remove(self.selected_connection)
           # print(f"✂️  Conexão removida: {source_node.title}.out[{out_port}] → {target_node.title}.in[{in_port}]")
            self.selected_connection = None
            self.queue_draw()

    def _select_all_nodes(self):
        """Seleciona todos os nós (Ctrl+A)"""
        if not self.nodes:
            return

        # Selecionar todos os nós
        for node in self.nodes:
            node.set_selected(True)

        # Atualizar foco para o último nó
        self.focused_node_index = len(self.nodes) - 1

        self.queue_draw()
        #print(f"✓ Selecionados {len(self.nodes)} nó(s)")

    def _copy_focused_node(self):
        """Copia os nós selecionados para o clipboard global (Ctrl+C)"""
        window = self.get_root()
        if not window:
            print("⚠️  Sem window!")
            return

        # Pegar todos os nós selecionados
        selected_nodes = [node for node in self.nodes if node.selected]

        if not selected_nodes:
            print("⚠️  Nenhum nó selecionado para copiar")
            return

        # Copiar nós
        window.clipboard_nodes = selected_nodes

        print(f"🔍 Debug - Total de conexões no canvas: {len(self.connections)}")
        print(f"🔍 Debug - Nós selecionados: {[node.title for node in selected_nodes]}")

        # Copiar conexões relacionadas aos nós selecionados
        # Incluir: conexões entre nós selecionados E conexões que chegam nos nós selecionados
        window.clipboard_connections = []
        for conn in self.connections:
            source_node, source_port, target_node, target_port = conn
            print(f"🔍 Verificando conexão: {source_node.title}[{source_port}] -> {target_node.title}[{target_port}]")
            print(f"   source in selected: {source_node in selected_nodes}, target in selected: {target_node in selected_nodes}")

            # Copiar se:
            # 1. Ambos os nós estão selecionados (conexão interna)
            # 2. Apenas o target está selecionado (conexão de entrada)
            if target_node in selected_nodes:
                window.clipboard_connections.append(conn)
                if source_node in selected_nodes:
                    print(f"   ✅ Conexão interna copiada!")
                else:
                    print(f"   ✅ Conexão de entrada copiada (origem não selecionada)!")

        print(f"📋 Copiado: {len(selected_nodes)} nó(s) e {len(window.clipboard_connections)} conexão(ões)")

    def _are_types_compatible(self, source_type, target_type):
        """
        Verifica se dois tipos de portas são compatíveis para conexão.

        Args:
            source_type: Tipo da porta de saída
            target_type: Tipo da porta de entrada

        Returns:
            bool: True se compatíveis
        """
        # 'any' aceita qualquer tipo
        if source_type == 'any' or target_type == 'any':
            return True

        # Mesmos tipos são compatíveis
        if source_type == target_type:
            return True

        # Regras especiais de compatibilidade
        # int pode ser usado como float
        if source_type == 'int' and target_type == 'float':
            return True

        # array e dataframe podem ser usados onde espera list
        if source_type in ['array', 'dataframe'] and target_type == 'list':
            return True

        # Caso contrário, incompatível
        return False

    def _paste_node(self, paste_x=None, paste_y=None):
        """
        Cola os nós do clipboard global (Ctrl+V ou menu).

        Args:
            paste_x: Posição X onde colar (em coordenadas de canvas). Se None, usa offset
            paste_y: Posição Y onde colar (em coordenadas de canvas). Se None, usa offset
        """
        window = self.get_root()
        if not window or not window.clipboard_nodes:
            #print("⚠️  Clipboard vazio")
            return

        # Verificar se estamos colando no mesmo projeto (adicionar "(cópia)" no título)
        is_same_project = any(node in self.nodes for node in window.clipboard_nodes)

        # Se não foi fornecida posição, usar offset padrão
        if paste_x is None or paste_y is None:
            # Usar offset para Ctrl+V (teclado)
            offset = 30
            use_offset = True
        else:
            # Usar posição do mouse para colar via menu de contexto
            use_offset = False

        # Mapa de nós antigos -> novos para recriar conexões
        node_map = {}
        new_nodes = []

        # Calcular centro do grupo de nós copiados (para posicionar relativo ao mouse)
        if not use_offset:
            min_x = min(node.x for node in window.clipboard_nodes)
            min_y = min(node.y for node in window.clipboard_nodes)
            max_x = max(node.x for node in window.clipboard_nodes)
            max_y = max(node.y for node in window.clipboard_nodes)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

        # Criar cópias de todos os nós
        for clipboard_node in window.clipboard_nodes:
            # Determinar título: adicionar "(cópia)" apenas se for no mesmo projeto
            if is_same_project:
                title = f"{clipboard_node.title} (cópia)"
            else:
                title = clipboard_node.title

            # Calcular posição do novo nó
            if use_offset:
                # Ctrl+V: offset simples
                new_x = clipboard_node.x + 30
                new_y = clipboard_node.y + 30
            else:
                # Menu contexto: posicionar relativo ao mouse
                # Manter distância relativa do centro do grupo
                offset_from_center_x = clipboard_node.x - center_x
                offset_from_center_y = clipboard_node.y - center_y
                new_x = paste_x + offset_from_center_x
                new_y = paste_y + offset_from_center_y

            new_node = Node(
                new_x,
                new_y,
                title,
                num_inputs=clipboard_node.num_inputs,
                num_outputs=clipboard_node.num_outputs
            )

            # Copiar todas as propriedades do nó original
            new_node.code = clipboard_node.code
            new_node.description = clipboard_node.description
            new_node.author = clipboard_node.author
            new_node.version = clipboard_node.version
            new_node.tags = clipboard_node.tags.copy() if clipboard_node.tags else []
            new_node.category = clipboard_node.category
            new_node.custom_color = clipboard_node.custom_color

            # Adicionar à lista
            self.nodes.append(new_node)
            new_nodes.append(new_node)

            # Mapear nó antigo -> novo
            node_map[clipboard_node] = new_node

        # Recriar conexões entre os nós colados
        connections_recreated = 0
        connections_to_existing = 0
        for conn in window.clipboard_connections:
            source_node, source_port, target_node, target_port = conn

            # Caso 1: Ambos os nós foram colados (conexão interna)
            if source_node in node_map and target_node in node_map:
                new_source = node_map[source_node]
                new_target = node_map[target_node]

                # Criar nova conexão
                new_conn = (new_source, source_port, new_target, target_port)
                self.connections.append(new_conn)
                connections_recreated += 1
                print(f"   ✅ Conexão interna recriada: {new_source.title} -> {new_target.title}")

            # Caso 2: Apenas o target foi colado, source existe no canvas original (conexão de entrada)
            elif source_node not in node_map and target_node in node_map:
                # Procurar o nó de origem no canvas atual pelo ID
                existing_source = None
                for node in self.nodes:
                    if node.id == source_node.id:
                        existing_source = node
                        break

                if existing_source:
                    new_target = node_map[target_node]
                    # Criar conexão do nó existente para o nó colado
                    new_conn = (existing_source, source_port, new_target, target_port)
                    self.connections.append(new_conn)
                    connections_to_existing += 1
                    print(f"   ✅ Conexão para nó existente recriada: {existing_source.title} -> {new_target.title}")
                else:
                    print(f"   ⚠️  Nó de origem '{source_node.title}' não encontrado no canvas")

            else:
                print(f"⚠️  Conexão não recriada: source={source_node in node_map}, target={target_node in node_map}")

        total_connections = connections_recreated + connections_to_existing
        print(f"📌 Colado: {len(new_nodes)} nó(s), {connections_recreated} conexão(ões) internas, {connections_to_existing} para nós existentes ({total_connections} total)")

        # Desselecionar todos
        for node in self.nodes:
            node.set_selected(False)

        # Selecionar os novos nós
        for new_node in new_nodes:
            new_node.set_selected(True)

        # Atualizar foco para o último nó colado
        if new_nodes:
            self.focused_node_index = self.nodes.index(new_nodes[-1])

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

    def _cut_context_node(self):
        """Recorta o nó do menu de contexto (copia e remove)"""
        if not hasattr(self, 'context_menu_node') or self.context_menu_node is None:
            return

        # Selecionar o nó do contexto (se não estiver)
        if not self.context_menu_node.selected:
            for node in self.nodes:
                node.set_selected(False)
            self.context_menu_node.set_selected(True)

        # Copiar
        self._copy_focused_node()

        # Remover o nó
        node_to_delete = self.context_menu_node

        # Remover conexões associadas ao nó
        self.connections = [
            conn for conn in self.connections
            if conn[0] != node_to_delete and conn[2] != node_to_delete
        ]

        # Remover o nó
        if node_to_delete in self.nodes:
            self.nodes.remove(node_to_delete)

        self.context_menu_node = None
        self._update_canvas_size()
        self.queue_draw()

    def execute_graph(self):
        """
        Executa o grafo completo em ordem topológica com paralelização por níveis.

        Returns:
            bool: True se execução foi bem sucedida, False caso contrário
        """
        if not self.nodes:
            print("⚠️  Nenhum nó para executar")
            return False

        # Limpar output_values e estado de erro de TODOS os nós antes de executar
        # Isso garante execução limpa sem resultados antigos
        from .node import NodeExecutionState
        for node in self.nodes:
            node.output_values = {}
            node.has_error = False
            node.error_message = ""
            node.execution_state = NodeExecutionState.IDLE

        # 1. Verificar se grafo tem ciclos
        execution_order = self._topological_sort()
        if execution_order is None:
            print("❌ Erro: Grafo contém ciclos! Não é possível executar.")
            return False

        # 2. Agrupar nós por nível de execução
        levels = self._group_by_execution_level()

        print(f"📋 Níveis de execução: {len(levels)}")
        for i, level in enumerate(levels):
            print(f"  Nível {i}: {[node.title for node in level]}")
        print()

        # 3. Dicionário para armazenar resultados de cada nó (thread-safe)
        import threading
        node_results = {}
        results_lock = threading.Lock()

        # Obter referência à janela para acessar output_panel
        window = self.get_root()

        # Obter output_panel do projeto atual (mais confiável)
        output_panel = None
        if hasattr(self, 'project_tab') and self.project_tab:
            output_panel = self.project_tab.output_panel
            print(f"✓ Usando output_panel do project_tab")
        elif hasattr(window, 'output_panel'):
            output_panel = window.output_panel
            print(f"✓ Usando output_panel da window")
        else:
            print(f"⚠️  Nenhum output_panel encontrado!")

        # Limpar outputs anteriores antes de executar
        from gi.repository import GLib
        if output_panel:
            print(f"🧹 Limpando output panel...")
            GLib.idle_add(output_panel.clear_all)

        try:
            # 4. Executar cada nível em paralelo
            for level_idx, level in enumerate(levels):
                print(f"⚡ Executando nível {level_idx} ({len(level)} nós em paralelo)...")

                # Função para executar um nó
                def execute_node_wrapper(node):
                    try:
                        # Marcar nó como RUNNING
                        node.execution_state = NodeExecutionState.RUNNING
                        from gi.repository import GLib
                        GLib.idle_add(self.queue_draw)

                        # Coletar inputs deste nó
                        with results_lock:
                            inputs = self._collect_node_inputs(node, node_results)

                        # Executar código do nó
                        outputs = self._execute_node_code(node, inputs)

                        # Marcar nó como COMPLETED
                        node.execution_state = NodeExecutionState.COMPLETED
                        GLib.idle_add(self.queue_draw)

                        # Armazenar resultados (thread-safe)
                        with results_lock:
                            node_results[node] = outputs

                        # RETORNAR outputs para processar na main thread
                        return (node, outputs, None)  # (node, outputs, error)

                    except Exception as e:
                        import traceback
                        # Marcar nó como ERROR
                        node.execution_state = NodeExecutionState.ERROR
                        GLib.idle_add(self.queue_draw)
                        error_msg = f"❌ Erro ao executar {node.title}: {e}\n{traceback.format_exc()}"
                        return (node, None, error_msg)

                # Executar nós do nível em paralelo
                level_results = []
                with ThreadPoolExecutor(max_workers=len(level)) as executor:
                    futures = [executor.submit(execute_node_wrapper, node) for node in level]

                    # Aguardar conclusão de todos os nós do nível
                    for future in as_completed(futures):
                        node, outputs, error = future.result()

                        if error:
                            print(error)
                            return False

                        # Guardar para processar depois
                        level_results.append((node, outputs))

                # PROCESSAR outputs especiais na MAIN THREAD (fora do executor)
                if output_panel:
                    for node, outputs in level_results:
                        # Pular nós que falharam (outputs = None)
                        if outputs is None:
                            continue
                        for output in outputs:
                            self._process_special_output(output, node, output_panel)

            return True

        except Exception as e:
            print(f"❌ Erro na execução: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _process_special_output(self, output, node, output_panel):
        """
        Processa outputs especiais e envia para o painel apropriado.
        Usa GLib.idle_add para garantir que está na main thread.

        Args:
            output: Output do nó
            node: Nó que gerou o output
            output_panel: Painel de output
        """
        from gi.repository import GLib

        # Se output é dict com chaves especiais, processar
        if isinstance(output, dict):
            # Console output (compartilhado, sem abas)
            if "_console" in output:
                console_text = str(output["_console"]) + "\n"
                print(f"  → Processando console output de '{node.title}': {console_text.strip()}")
                GLib.idle_add(output_panel.add_console, console_text)
                return

            # Plot matplotlib
            if "_plot" in output:
                print(f"  → Processando plot output de '{node.title}'")
                GLib.idle_add(output_panel.add_plot, output["_plot"], f"Plot from: {node.title}")
                return

            # Tabela (DataFrame)
            if "_table" in output:
                print(f"  → Processando table output de '{node.title}'")
                GLib.idle_add(output_panel.add_table, output["_table"], f"Table from: {node.title}")
                return

            # Dados estruturados
            if "_data" in output:
                print(f"  → Processando data output de '{node.title}'")
                GLib.idle_add(output_panel.add_data, output["_data"], f"Data from: {node.title}")
                return

        # Output normal - não fazer nada (só passa para próximo nó)

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

    def _node_has_connections(self, node):
        """
        Verifica se um nó possui pelo menos uma conexão (entrada ou saída).

        Args:
            node: Nó a verificar

        Returns:
            bool: True se o nó tem pelo menos uma conexão, False caso contrário
        """
        for source_node, out_port, target_node, in_port in self.connections:
            if source_node == node or target_node == node:
                return True
        return False

    def _group_by_execution_level(self):
        """
        Agrupa nós por nível de execução (profundidade no DAG).
        Nós no mesmo nível podem ser executados em paralelo.

        NOTA: Nós sem nenhuma conexão (entrada E saída) são excluídos.

        Returns:
            list[list[Node]]: Lista de níveis, cada nível contém lista de nós
        """
        # Filtrar nós sem conexões
        active_nodes = [node for node in self.nodes if self._node_has_connections(node)]
        inactive_nodes = [node for node in self.nodes if not self._node_has_connections(node)]

        # Mostrar nós inativos
        if inactive_nodes:
            print(f"⏸️  Nós inativos (sem conexões): {[node.title for node in inactive_nodes]}")

        # Se não há nós ativos, retornar lista vazia
        if not active_nodes:
            return []

        # Calcular profundidade de cada nó (distância máxima da raiz)
        depth = {node: 0 for node in active_nodes}

        # Construir adjacências inversas (target -> sources)
        predecessors = {node: [] for node in active_nodes}
        for source_node, out_port, target_node, in_port in self.connections:
            if target_node in active_nodes and source_node in active_nodes:
                predecessors[target_node].append(source_node)

        # Calcular profundidade de cada nó
        changed = True
        while changed:
            changed = False
            for node in active_nodes:
                if predecessors[node]:
                    max_pred_depth = max(depth[pred] for pred in predecessors[node])
                    new_depth = max_pred_depth + 1
                    if new_depth > depth[node]:
                        depth[node] = new_depth
                        changed = True

        # Agrupar por profundidade
        max_depth = max(depth.values()) if depth else 0
        levels = [[] for _ in range(max_depth + 1)]

        for node in active_nodes:
            levels[depth[node]].append(node)

        return levels

    def _collect_node_inputs(self, node, node_results):
        """
        Coleta os inputs de um nó a partir dos resultados dos nós anteriores.

        MELHORADO: Múltiplas conexões na mesma porta viram lista automaticamente.

        Args:
            node: Nó cujos inputs serão coletados
            node_results: Dicionário com resultados dos nós já executados

        Returns:
            tuple: Tupla com os inputs do nó
        """
        # Inicializar lista de inputs (um por porta de entrada)
        inputs = [None] * node.num_inputs

        # Rastrear múltiplas conexões por porta
        connections_per_port = [[] for _ in range(node.num_inputs)]

        # Coletar TODAS as conexões para cada porta
        for source_node, out_port, target_node, in_port in self.connections:
            if target_node == node:
                # Esta conexão fornece input para este nó
                if source_node in node_results:
                    source_outputs = node_results[source_node]
                    if out_port < len(source_outputs):
                        # Adicionar à lista de conexões desta porta
                        connections_per_port[in_port].append(source_outputs[out_port])

        # Processar cada porta de entrada
        for port_idx in range(node.num_inputs):
            connections = connections_per_port[port_idx]

            if len(connections) == 0:
                # Nenhuma conexão: manter None
                inputs[port_idx] = None
            elif len(connections) == 1:
                # Uma conexão: valor direto
                inputs[port_idx] = connections[0]
            else:
                # Múltiplas conexões: criar lista
                inputs[port_idx] = connections
                print(f"  📌 Porta in[{port_idx}] recebeu {len(connections)} conexões → lista")

        return tuple(inputs)

    def _get_project_directory(self):
        """
        Retorna o diretório home do usuário.

        Como load_data() e save_data() agora aceitam paths absolutos,
        project_dir serve apenas como fallback para paths relativos.

        Use sempre paths absolutos: load_data("~/caminho/arquivo.csv")
        """
        return Path.home()

    def _execute_via_system_venv(self, node, inputs, venv):
        """
        Executa código usando Python do sistema via subprocess

        Args:
            node: Nó a executar
            inputs: Tupla de inputs
            venv: Instância do SystemVenv

        Returns:
            tuple: Outputs ou None se erro
        """
        import pickle
        import base64
        import time

        # Debug: verificar se venv foi passado corretamente
        if venv is None:
            print(f"❌ ERRO: venv é None para nó '{node.title}'")
            print(f"   project_tab.isolated_env = {getattr(self.project_tab, 'isolated_env', 'N/A') if hasattr(self, 'project_tab') else 'no project_tab'}")
            print(f"   project_tab.python_mode = {getattr(self.project_tab, 'python_mode', 'N/A') if hasattr(self, 'project_tab') else 'no project_tab'}")
            raise RuntimeError("System venv not configured. Please reopen the project or check Project Settings.")

        try:
            start_time = time.perf_counter()

            # Serializar inputs para passar ao subprocess
            inputs_b64 = base64.b64encode(pickle.dumps(inputs)).decode('ascii')

            # Obter project_dir para helpers
            project_dir = None
            if hasattr(self, 'project_tab') and self.project_tab.current_file:
                from pathlib import Path
                project_dir = Path(self.project_tab.current_file).parent

            # Criar script que será executado no venv
            # IMPORTANTE: Envolve código do nó em função para capturar return
            script = f'''
import pickle
import base64
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

# Deserializar inputs
inputs = pickle.loads(base64.b64decode({repr(inputs_b64)}))

# Helpers: load_data e save_data
project_dir = Path({repr(str(project_dir))}) if {repr(str(project_dir))} != "None" else Path.home() / "Documents"

def load_data(filename):
    """Carrega arquivo do projeto (auto-detecta formato)"""
    path = Path(filename).expanduser()
    if not path.is_absolute():
        path = project_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {{path}}")
    suffix = path.suffix.lower()
    if suffix == '.csv':
        return pd.read_csv(path)
    elif suffix in ['.xls', '.xlsx']:
        return pd.read_excel(path)
    elif suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return pd.DataFrame(data)
        return data
    elif suffix == '.parquet':
        return pd.read_parquet(path)
    elif suffix in ['.txt', '.log']:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Formato não suportado: {{suffix}}")

def save_data(data, filename, **kwargs):
    """Salva dados no projeto (auto-detecta formato)"""
    path = Path(filename).expanduser()
    if not path.is_absolute():
        path = project_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    if isinstance(data, pd.DataFrame):
        if suffix == '.csv':
            data.to_csv(path, index=kwargs.get('index', False))
        elif suffix in ['.xls', '.xlsx']:
            data.to_excel(path, index=kwargs.get('index', False))
        elif suffix == '.parquet':
            data.to_parquet(path)
        elif suffix == '.json':
            data.to_json(path, orient=kwargs.get('orient', 'records'), indent=2)
        else:
            raise ValueError(f"Formato não suportado para DataFrame: {{suffix}}")
    elif hasattr(data, 'savefig'):
        data.savefig(path, dpi=kwargs.get('dpi', 150), bbox_inches='tight')
    elif isinstance(data, (dict, list)):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    elif isinstance(data, str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
    elif isinstance(data, np.ndarray):
        if suffix == '.csv':
            pd.DataFrame(data).to_csv(path, index=False, header=False)
        elif suffix == '.npy':
            np.save(path, data)
        else:
            raise ValueError(f"Formato não suportado para array: {{suffix}}")
    else:
        raise TypeError(f"Tipo de dado não suportado: {{type(data)}}")
    return path

# Aliases
load = load_data
save = save_data

# Executar código do nó dentro de função para capturar return
def _node_func():
{chr(10).join("    " + line for line in node.code.splitlines())}

result = _node_func()

# Serializar outputs
output_b64 = base64.b64encode(pickle.dumps(result)).decode('ascii')
print("__OUTPUT__:" + output_b64)
'''

            # Executar via venv
            success, stdout, stderr = venv.run_code(script, timeout=60)

            execution_time = time.perf_counter() - start_time
            node.last_execution_time = execution_time
            node.total_executions += 1

            if not success:
                print(f"❌ ERRO ao executar via system venv:")
                print(stderr)
                raise RuntimeError(stderr)

            # Extrair output serializado
            for line in stdout.split('\n'):
                if line.startswith('__OUTPUT__:'):
                    output_b64 = line.split(':', 1)[1]
                    result = pickle.loads(base64.b64decode(output_b64))

                    # Garantir que é tupla
                    if not isinstance(result, tuple):
                        result = (result,)

                    # Processar outputs com "_folder" para auto-save
                    project_dir = None
                    if hasattr(self, 'project_tab') and self.project_tab.current_file:
                        from pathlib import Path
                        project_dir = Path(self.project_tab.current_file).parent

                    result = process_folder_output(result, node.title, project_dir)

                    return result

            # Se não encontrou output, erro
            raise RuntimeError("Nenhum resultado retornado")

        except Exception as e:
            print(f"❌ ERRO em '{node.title}' (system venv):")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _execute_node_code(self, node, inputs):
        """
        Executa o código Python de um nó com profiling e error handling.

        Args:
            node: Nó a ser executado
            inputs: Tupla com inputs do nó

        Returns:
            tuple: Tupla com outputs do nó, ou None se erro
        """
        import time
        import traceback

        if not node.code or node.code.strip() == "":
            print(f"  ⚠️  Nó sem código, retornando inputs como outputs")
            return inputs

        # Verificar se deve usar system venv
        if hasattr(self, 'project_tab'):
            project = self.project_tab
            if hasattr(project, 'python_mode') and project.python_mode == 'system':
                # Executar via subprocess no venv do sistema
                print(f"🐍 Executando '{node.title}' via system venv")
                return self._execute_via_system_venv(node, inputs, project.isolated_env)

        try:
            # Validar tipos de entrada ANTES de executar
            is_valid, error_msg = node.validate_input_types(inputs)
            if not is_valid:
                raise TypeError(error_msg)

            # Configurar matplotlib para backend non-interactive (evita warning de GUI)
            try:
                import matplotlib
                matplotlib.use('Agg')  # Backend sem GUI
            except:
                pass

            # Executar código com profiling
            start_time = time.perf_counter()

            # Transformar o código em uma função
            code_as_function = "def __node_function(inputs):\n"
            for line in node.code.split('\n'):
                code_as_function += f"    {line}\n"

            # Obter diretório do projeto
            project_dir = self._get_project_directory()

            # Criar helpers de dados configurados para este projeto
            helpers = create_data_helpers(project_dir)

            # Preparar namespace com builtins + helpers + bibliotecas úteis
            namespace = {
                '__builtins__': __builtins__,
                # Data helpers
                'load_data': helpers['load_data'],
                'save_data': helpers['save_data'],
                'load': helpers['load'],
                'save': helpers['save'],
                'project_dir': helpers['project_dir'],
                # Diretórios úteis
                'nodes_dir': Path.home() / ".nodes",
                'home_dir': Path.home(),
                # Bibliotecas comuns
                'pd': __import__('pandas'),
                'np': __import__('numpy'),
                'plt': __import__('matplotlib.pyplot'),
                'Path': Path,
            }

            exec(code_as_function, namespace)

            # Chamar a função com os inputs
            result = namespace['__node_function'](inputs)

            # Calcular tempo de execução
            execution_time = time.perf_counter() - start_time
            node.last_execution_time = execution_time
            node.total_executions += 1

            # Garantir que retorno é tupla
            if not isinstance(result, tuple):
                result = (result,)

            # Processar outputs com "_folder" para auto-save
            result = process_folder_output(result, node.title, project_dir)

            return result

        except Exception as e:
            # Capturar erro e marcar nó
            from .node import NodeExecutionState
            node.has_error = True
            node.error_message = str(e)
            node.execution_state = NodeExecutionState.ERROR

            # Imprimir erro detalhado
            print(f"❌ ERRO em '{node.title}':")
            print(f"   {type(e).__name__}: {e}")
            traceback.print_exc()

            # Redesenhar canvas para mostrar erro visualmente
            from gi.repository import GLib
            GLib.idle_add(self.queue_draw)

            return None

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
                # Validar tipos antes de criar conexão
                source_node = self.connection_start_node
                source_port = self.connection_start_port
                target_node = node
                target_port = port_index

                # Verificar compatibilidade de tipos
                source_type = source_node.output_types[source_port] if source_port < len(source_node.output_types) else 'any'
                target_type = target_node.input_types[target_port] if target_port < len(target_node.input_types) else 'any'

                types_compatible = self._are_types_compatible(source_type, target_type)

                if not types_compatible:
                    print(f"⚠️  Conexão rejeitada: tipo '{source_type}' incompatível com '{target_type}'")
                    # Não cria a conexão
                else:
                    # Criar a conexão
                    new_connection = (source_node, source_port, target_node, target_port)

                    # Verificar se já existe essa conexão
                    if new_connection not in self.connections:
                        self.connections.append(new_connection)
                        # print(f"✅ Conexão criada: {source_node.title}.out[{source_port}] → {target_node.title}.in[{target_port}]")
                    # else:
                        # print(f"⚠️  Conexão já existe")

                # return

        # Se chegou aqui, não soltou em uma porta válida
        # print(f"❌ Conexão cancelada (não soltou em porta de entrada)")

    def on_drag_begin(self, gesture, start_x, start_y):
        """Quando começa a arrastar"""
        canvas_x, canvas_y = self._screen_to_canvas(start_x, start_y)

        # Se Espaço está pressionado, ativar panning
        if self.space_pressed:
            self.panning = True
            self.pan_start_x = start_x - self.pan_offset_x
            self.pan_start_y = start_y - self.pan_offset_y
            self.set_cursor(self._cursor_cache['grabbing'])
            return

        # Capturar estado para undo (só se arrastar nós)
        if self._recording_undo:
            self._drag_old_state = self.undo_manager.capture_state()

        # Verificar modificadores
        modifiers = gesture.get_current_event_state()
        shift_pressed = modifiers & Gdk.ModifierType.SHIFT_MASK

        # Se está selecionando região, não fazer nada aqui
        if self.selecting_region:
            return

        # Verificar se começou sobre um nó
        for node in reversed(self.nodes):
            if node.contains_point(canvas_x, canvas_y):
                # Se o nó clicado está selecionado e há múltiplos selecionados: mover todos juntos
                selected_count = sum(1 for n in self.nodes if n.selected)
                if node.selected and selected_count > 1:
                    # Iniciar drag de todos os nós selecionados
                    for selected_node in self.nodes:
                        if selected_node.selected:
                            selected_node.start_drag(canvas_x, canvas_y)
                    self.dragging_node = node
                    return
                else:
                    # Clique normal em nó: mover apenas este nó
                    node.start_drag(canvas_x, canvas_y)
                    self.dragging_node = node
                    return

    def on_drag_update(self, gesture, offset_x, offset_y):
        """Enquanto arrasta"""
        # Pegar posição inicial do drag
        (_, start_x, start_y) = gesture.get_start_point()

        # Se está fazendo panning, atualizar offset
        if self.panning:
            current_x = start_x + offset_x
            current_y = start_y + offset_y
            self.pan_offset_x = current_x - self.pan_start_x
            self.pan_offset_y = current_y - self.pan_start_y
            self.queue_draw()
            return

        # Se está selecionando região, atualizar o retângulo
        if self.selecting_region:
            current_x = start_x + offset_x
            current_y = start_y + offset_y
            canvas_x, canvas_y = self._screen_to_canvas(current_x, current_y)
            self.selection_current_x = canvas_x
            self.selection_current_y = canvas_y
            self.queue_draw()
            return

        # Se está arrastando nós
        if self.dragging_node:
            # Calcular posição atual
            current_x = start_x + offset_x
            current_y = start_y + offset_y
            canvas_x, canvas_y = self._screen_to_canvas(current_x, current_y)

            # Verificar quantos nós estão selecionados
            selected_count = sum(1 for node in self.nodes if node.selected)

            if selected_count > 1 and self.dragging_node.selected:
                # Múltiplos selecionados: mover todos
                for node in self.nodes:
                    if node.selected:
                        node.update_drag(canvas_x, canvas_y)
            else:
                # Mover apenas o nó arrastado
                self.dragging_node.update_drag(canvas_x, canvas_y)

            # Atualizar tamanho do canvas durante o arrasto
            self._update_canvas_size()
            self.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        """Quando termina de arrastar"""
        # Se estava fazendo panning, finalizar
        if self.panning:
            self.panning = False
            # Manter cursor como "grab" se espaço ainda estiver pressionado
            if self.space_pressed:
                self.set_cursor(self._cursor_cache['grab'])
            else:
                self.set_cursor(None)
            return

        # Se estava selecionando região, selecionar nós dentro do retângulo
        if self.selecting_region:
            self._select_nodes_in_region()
            self.selecting_region = False
            self.queue_draw()
            return

        # Se estava arrastando nós
        if self.dragging_node:
            # Parar drag de todos os nós selecionados
            for node in self.nodes:
                if node.selected:
                    node.stop_drag()
            self.dragging_node = None

            # Registrar movimento no undo
            if self._recording_undo and hasattr(self, '_drag_old_state'):
                self.undo_manager.record_action(self._drag_old_state)
                delattr(self, '_drag_old_state')

            self._update_canvas_size()
            self.queue_draw()

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
        # Fundo com cor configurável
        bg_color = self._get_color_setting("canvas-bg-color")
        context.set_source_rgb(*bg_color)
        context.paint()

        # Salvar estado do contexto
        context.save()

        # Aplicar transformações de pan e zoom
        context.translate(self.pan_offset_x, self.pan_offset_y)
        context.scale(self.zoom_level, self.zoom_level)

        # Grid de fundo com dois níveis (blueprint style)
        small_grid_size = 20  # Grid fino (menor)
        large_grid_size = 100  # Grid grosso (maior) - a cada 5 linhas finas

        # Calcular limites visíveis do grid
        start_x = int(-self.pan_offset_x / self.zoom_level / small_grid_size) * small_grid_size
        start_y = int(-self.pan_offset_y / self.zoom_level / small_grid_size) * small_grid_size
        end_x = int((width - self.pan_offset_x) / self.zoom_level) + small_grid_size
        end_y = int((height - self.pan_offset_y) / self.zoom_level) + small_grid_size

        # Desenhar grid FINO primeiro (mais claro)
        fine_grid_color = self._get_color_setting("fine-grid-color")
        context.set_source_rgb(*fine_grid_color)
        # Linha fina com largura constante na tela (não escala com zoom)
        context.set_line_width(0.5 / self.zoom_level)

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
        coarse_grid_color = self._get_color_setting("coarse-grid-color")
        context.set_source_rgb(*coarse_grid_color)
        # Linha grossa com largura constante na tela (não escala com zoom)
        context.set_line_width(1.0 / self.zoom_level)

        for x in range(start_x, end_x, large_grid_size):
            context.move_to(x, start_y)
            context.line_to(x, end_y)
        for y in range(start_y, end_y, large_grid_size):
            context.move_to(start_x, y)
            context.line_to(end_x, y)
        context.stroke()

        # Desenhar conexões não selecionadas primeiro (atrás dos nós)
        self._draw_connections(context, selected_only=False)

        # Preparar cores do tema para os nós
        theme_colors = {
            'node_body': self._get_color_setting("node-body-color"),
            'node_border': self._get_color_setting("node-border-color"),
            'node_selection': self._get_color_setting("node-selection-color"),
            'node_running': self._get_color_setting("node-running-color"),
        }

        # Obter opacidade de dimming se em modo focus
        dimming_opacity = 1.0
        if self.focus_node:
            dimming_opacity = self._get_opacity_setting("focus-dimming-opacity")

        # Desenhar todos os nós
        for node in self.nodes:
            # Verificar se o nó deve ser dimmed
            should_dim = self.focus_node is not None and node not in self.focus_nodes_set

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
        self._draw_connections(context, selected_only=True)

        # Desenhar retângulo de seleção (se estiver selecionando)
        if self.selecting_region:
            x1 = min(self.selection_start_x, self.selection_current_x)
            y1 = min(self.selection_start_y, self.selection_current_y)
            x2 = max(self.selection_start_x, self.selection_current_x)
            y2 = max(self.selection_start_y, self.selection_current_y)

            # Retângulo preenchido semi-transparente
            selection_fill_color = self._get_color_setting("selection-fill-color")
            selection_fill_opacity = self._get_opacity_setting("selection-fill-opacity")
            context.set_source_rgba(*selection_fill_color, selection_fill_opacity)
            context.rectangle(x1, y1, x2 - x1, y2 - y1)
            context.fill()

            # Borda do retângulo
            selection_border_color = self._get_color_setting("selection-border-color")
            selection_border_opacity = self._get_opacity_setting("selection-border-opacity")
            context.set_source_rgba(*selection_border_color, selection_border_opacity)
            context.set_line_width(1.5 / self.zoom_level)
            context.rectangle(x1, y1, x2 - x1, y2 - y1)
            context.stroke()

        # Restaurar estado do contexto
        context.restore()

        # Desenhar info de zoom/pan (fora da transformação)
        context.set_source_rgb(0.3, 0.3, 0.3)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(11)
        info_text = f"Zoom: {self.zoom_level * 100:.0f}% | Pan: ({self.pan_offset_x:.0f}, {self.pan_offset_y:.0f}) | Scroll: zoom | Space+Drag: pan | Right-click: menu"
        context.move_to(10, height - 10)
        context.show_text(info_text)

    def _draw_connections(self, context, selected_only=False):
        """
        Desenha conexões armazenadas

        Args:
            context: Cairo context
            selected_only: Se True, desenha apenas conexões selecionadas
                          Se False, desenha apenas conexões não selecionadas
        """
        # Desenhar cada conexão da lista
        for connection in self.connections:
            source_node, out_port, target_node, in_port = connection
            is_selected = (connection == self.selected_connection)

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
                should_dim = self.focus_node is not None and connection not in self.focus_connections_set

                # Cor e largura diferentes se está selecionada
                if is_selected:
                    context.set_line_width(4 / self.zoom_level)
                    selected_color = self._get_color_setting("connection-selected-color")
                    alpha = 0.95
                else:
                    context.set_line_width(3 / self.zoom_level)
                    normal_color = self._get_color_setting("connection-normal-color")
                    selected_color = normal_color  # Usar mesma variável
                    alpha = 0.75

                # Aplicar dimming se necessário
                if should_dim:
                    dimming_opacity = self._get_opacity_setting("focus-dimming-opacity")
                    alpha *= dimming_opacity

                context.set_source_rgba(*selected_color, alpha)
                self._draw_connection(context, start, end)

        # Se está criando uma conexão, desenhar linha temporária (sempre por cima)
        if selected_only and self.creating_connection and self.connection_start_node:
            start = self.connection_start_node.get_output_port_position(self.connection_start_port)
            if start:
                # Linha temporária em cor diferente
                context.set_line_width(3)
                creating_color = self._get_color_setting("connection-creating-color")
                context.set_source_rgba(*creating_color, 0.8)
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

    def _show_node_context_menu(self, node, x, y):
        """
        Mostra menu de contexto para um nó

        Args:
            node: Nó clicado
            x, y: Posição do clique (coordenadas da tela/widget)
        """
        # Verificar se há múltiplos nós selecionados
        selected_nodes = [n for n in self.nodes if n.selected]
        if len(selected_nodes) > 1:
            self._show_multi_selection_menu(x, y)
            return

        print(f"📝 Criando menu de contexto para: {node.title}")

        menu = Gio.Menu()

        # Opções do menu
        menu.append("Edit Code", "canvas.edit-code")
        menu.append("Rename", "canvas.rename")
        menu.append("Properties", "canvas.properties")

        # Seção de clipboard
        clipboard_section = Gio.Menu()
        clipboard_section.append("Copy", "canvas.copy")
        clipboard_section.append("Cut", "canvas.cut")
        clipboard_section.append("Paste", "canvas.paste")
        menu.append_section(None, clipboard_section)

        menu.append("Save to Library", "canvas.save-to-library")
        menu.append("Delete", "canvas.delete")

        print(f"✓ Menu criado com itens de clipboard")

        # Criar popover
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(self)

        # Usar Gdk.Rectangle para posicionar no ponto do clique
        # x, y já são coordenadas relativas ao widget (DrawingArea)
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)

        # Guardar nó atual para as actions
        self.context_menu_node = node

        print(f"✓ Popover configurado em ({x:.0f}, {y:.0f})")

        # Mostrar menu
        popover.popup()
        print(f"✓ popup() chamado")

    def _show_canvas_context_menu(self, x, y):
        """Mostra menu de contexto para o canvas vazio"""
        menu = Gio.Menu()

        # Opção de colar (se há algo no clipboard)
        window = self.get_root()
        if window and window.clipboard_nodes:
            menu.append("Paste", "canvas.paste")

        # Se menu está vazio, não mostrar
        if menu.get_n_items() == 0:
            return

        # Guardar posição do clique em coordenadas de canvas (para paste)
        canvas_x, canvas_y = self._screen_to_canvas(x, y)
        self.context_menu_position = (canvas_x, canvas_y)

        # Criar popover
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(self)

        # Usar Gdk.Rectangle para posicionar no ponto do clique
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)

        # Mostrar menu
        popover.popup()

    def _show_multi_selection_menu(self, x, y):
        """Mostra menu de contexto para múltipla seleção"""
        menu = Gio.Menu()

        # Seção de alinhamento
        align_section = Gio.Menu()
        align_section.append("Align Left", "canvas.align-left")
        align_section.append("Align Center H", "canvas.align-center-h")
        align_section.append("Align Right", "canvas.align-right")
        align_section.append("Align Top", "canvas.align-top")
        align_section.append("Align Center V", "canvas.align-center-v")
        align_section.append("Align Bottom", "canvas.align-bottom")
        menu.append_section("Alignment", align_section)

        # Seção de distribuição
        distribute_section = Gio.Menu()
        distribute_section.append("Distribute Horizontally", "canvas.distribute-h")
        distribute_section.append("Distribute Vertically", "canvas.distribute-v")
        menu.append_section("Distribution", distribute_section)

        # Criar popover
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(self)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)

        popover.popup()

    def edit_node_code(self):
        """Abre dialog para editar código do nó"""
        if not hasattr(self, 'context_menu_node') or self.context_menu_node is None:
            return

        node = self.context_menu_node
        window = self.get_root()

        dialog = CodeEditorDialog(window, node)
        dialog.on_apply_callback = lambda code: self._on_code_editor_apply(node, code)
        dialog.present()

    def _on_code_editor_apply(self, node, new_code):
        """Callback quando código é aplicado"""
        node.code = new_code
        print(f"✓ Code updated: {node.title}")
        self.queue_draw()

    def rename_node(self):
        """Abre dialog para renomear nó"""
        if not hasattr(self, 'context_menu_node') or self.context_menu_node is None:
            return

        node = self.context_menu_node
        window = self.get_root()

        dialog = RenameNodeDialog(window, node)
        dialog.connect("response", self._on_rename_response, node)
        dialog.present()

    def _on_rename_response(self, dialog, response, node):
        """Callback quando dialog de renomeação é fechado"""
        if response == "rename":  # Adw.MessageDialog usa strings
            new_name = dialog.get_name()
            if new_name:
                node.title = new_name
                print(f"✓ Nó renomeado: {new_name}")
                self.queue_draw()
        dialog.close()

    def show_node_properties(self):
        """Abre dialog de propriedades do nó"""
        if not hasattr(self, 'context_menu_node') or self.context_menu_node is None:
            return

        node = self.context_menu_node
        window = self.get_root()

        dialog = NodePropertiesDialog(window, node)
        dialog.on_apply_callback = lambda props: self._on_properties_apply(node, props)
        dialog.present()

    def _on_properties_apply(self, node, props):
        """Callback quando propriedades são aplicadas"""
        # Atualizar propriedades
        node.title = props["title"]
        node.num_inputs = props["num_inputs"]
        node.num_outputs = props["num_outputs"]
        node.code = props["code"]
        node.description = props.get("description", "")
        node.author = props.get("author", "")
        node.version = props.get("version", "1.0")
        node.tags = props.get("tags", [])
        node.category = props.get("category", "")
        node.custom_color = props.get("custom_color")

        # Atualizar tipos das portas
        node.input_types = props.get("input_types", ['any'] * node.num_inputs)
        node.output_types = props.get("output_types", ['any'] * node.num_outputs)

        # Ajustar listas de tipos se número de portas mudou
        while len(node.input_types) < node.num_inputs:
            node.input_types.append('any')
        while len(node.output_types) < node.num_outputs:
            node.output_types.append('any')
        node.input_types = node.input_types[:node.num_inputs]
        node.output_types = node.output_types[:node.num_outputs]

        # Recalcular altura do nó
        max_ports = max(node.num_inputs, node.num_outputs)
        node.body_height = max_ports * node.HEIGHT_PORT + node.PADDING * 2
        node.total_height = node.HEIGHT_HEADER + node.body_height

        print(f"✓ Propriedades atualizadas: {node.title}")
        self.queue_draw()

    def delete_context_node(self):
        """Deleta o nó do menu de contexto"""
        if not hasattr(self, 'context_menu_node') or self.context_menu_node is None:
            return

        node = self.context_menu_node

        # Remover conexões associadas
        self.connections = [
            conn for conn in self.connections
            if conn[0] != node and conn[2] != node
        ]

        # Remover o nó
        if node in self.nodes:
            self.nodes.remove(node)

        self.context_menu_node = None
        self._update_canvas_size()
        self.queue_draw()

    def save_node_to_library(self):
        """Salva o nó como template na biblioteca"""
        if not hasattr(self, 'context_menu_node') or self.context_menu_node is None:
            return

        node = self.context_menu_node
        window = self.get_root()

        dialog = SaveToLibraryDialog(window, node)
        dialog.on_save_callback = lambda info: self._on_save_to_library(node, info)
        dialog.present()

    def _on_save_to_library(self, node, info):
        """Callback quando nó é salvo na biblioteca"""
        # Atualizar título do nó se mudou
        if info["name"] != node.title:
            node.title = info["name"]

        # Atualizar categoria do nó
        node.category = info["category"]

        # Salvar na biblioteca
        library = _get_library()
        visibility = info.get("visibility", "private")
        success = library.save_node_template(node, info["category"], visibility)

        if success:
            print(f"✓ Nó '{info['name']}' salvo na categoria '{info['category']}'")

            # Recriar painel da biblioteca na janela
            window = self.get_root()
            if hasattr(window, '_recreate_library_panel'):
                window._recreate_library_panel()

        self.queue_draw()



    def align_selected_nodes(self, mode):
        """Alinha nós selecionados"""
        selected = [n for n in self.nodes if n.selected]
        if len(selected) < 2:
            return

        if mode == "left":
            # Alinhar à esquerda (menor x)
            min_x = min(n.x for n in selected)
            for node in selected:
                node.x = min_x
        elif mode == "center-h":
            # Alinhar ao centro horizontal
            avg_center_x = sum(n.x + n.WIDTH / 2 for n in selected) / len(selected)
            for node in selected:
                node.x = avg_center_x - node.WIDTH / 2
        elif mode == "right":
            # Alinhar à direita (maior x + width)
            max_right = max(n.x + n.WIDTH for n in selected)
            for node in selected:
                node.x = max_right - node.WIDTH
        elif mode == "top":
            # Alinhar ao topo (menor y)
            min_y = min(n.y for n in selected)
            for node in selected:
                node.y = min_y
        elif mode == "center-v":
            # Alinhar ao centro vertical
            avg_center_y = sum(n.y + n.total_height / 2 for n in selected) / len(selected)
            for node in selected:
                node.y = avg_center_y - node.total_height / 2
        elif mode == "bottom":
            # Alinhar à base (maior y + height)
            max_bottom = max(n.y + n.total_height for n in selected)
            for node in selected:
                node.y = max_bottom - node.total_height

        self.queue_draw()

    def distribute_selected_nodes(self, direction):
        """Distribui nós selecionados com espaçamento uniforme"""
        selected = [n for n in self.nodes if n.selected]
        if len(selected) < 3:
            return

        if direction == "horizontal":
            # Ordenar por posição X
            selected_sorted = sorted(selected, key=lambda n: n.x)
            
            # Calcular espaço total e espaçamento
            leftmost = selected_sorted[0].x
            rightmost = selected_sorted[-1].x + selected_sorted[-1].WIDTH
            total_width = sum(n.WIDTH for n in selected_sorted)
            available_space = rightmost - leftmost - total_width
            gap = available_space / (len(selected_sorted) - 1)
            
            # Distribuir
            current_x = leftmost
            for node in selected_sorted:
                node.x = current_x
                current_x += node.WIDTH + gap
                
        elif direction == "vertical":
            # Ordenar por posição Y
            selected_sorted = sorted(selected, key=lambda n: n.y)
            
            # Calcular espaço total e espaçamento
            topmost = selected_sorted[0].y
            bottommost = selected_sorted[-1].y + selected_sorted[-1].total_height
            total_height = sum(n.total_height for n in selected_sorted)
            available_space = bottommost - topmost - total_height
            gap = available_space / (len(selected_sorted) - 1)
            
            # Distribuir
            current_y = topmost
            for node in selected_sorted:
                node.y = current_y
                current_y += node.total_height + gap

        self.queue_draw()

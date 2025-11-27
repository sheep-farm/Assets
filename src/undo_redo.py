"""Sistema de Undo/Redo para Assets"""

import copy


class Command:
    """Classe base para comandos"""
    def execute(self):
        """Executa o comando"""
        pass

    def undo(self):
        """Desfaz o comando"""
        pass


class GraphStateCommand(Command):
    """Comando que salva estado completo do grafo"""
    def __init__(self, canvas, old_state, new_state):
        self.canvas = canvas
        self.old_state = old_state  # (nodes, connections, zoom, pan_x, pan_y)
        self.new_state = new_state

    def execute(self):
        """Aplica novo estado"""
        self._apply_state(self.new_state)

    def undo(self):
        """Volta ao estado anterior"""
        self._apply_state(self.old_state)

    def _apply_state(self, state):
        """Aplica um estado ao canvas"""
        nodes, connections, zoom = state

        # Deep copy dos nós
        new_nodes = copy.deepcopy(nodes)

        # Criar mapa usando UUID dos nós (que persiste após deep copy)
        # Mapear: node.id (UUID) -> novo nó
        uuid_to_new_node = {node.id: node for node in new_nodes}

        # Criar mapa dos nós antigos: node.id (UUID) -> nó antigo
        uuid_to_old_node = {node.id: node for node in nodes}

        # Reconstruir conexões usando os novos nós
        new_connections = []
        for src_node, src_port, dst_node, dst_port in connections:
            # Usar UUID para encontrar os novos nós correspondentes
            new_src = uuid_to_new_node.get(src_node.id)
            new_dst = uuid_to_new_node.get(dst_node.id)

            if new_src and new_dst:
                new_connections.append((new_src, src_port, new_dst, dst_port))

        # Aplicar ao canvas
        self.canvas.nodes = new_nodes
        self.canvas.connections = new_connections
        self.canvas.zoom_level = zoom

        # Recalcular posições das portas
        for node in self.canvas.nodes:
            node._calculate_port_positions()

        # Atualizar canvas
        self.canvas._update_canvas_size()
        self.canvas.queue_draw()


class UndoRedoManager:
    """Gerenciador de Undo/Redo"""
    def __init__(self, canvas, max_history=50):
        self.canvas = canvas
        self.max_history = max_history
        self.undo_stack = []
        self.redo_stack = []

    def capture_state(self):
        """Captura estado atual do canvas"""
        # Deep copy para preservar estado
        nodes = copy.deepcopy(self.canvas.nodes)
        connections = copy.deepcopy(self.canvas.connections)
        zoom = self.canvas.zoom_level
        return (nodes, connections, zoom)

    def execute_command(self, old_state, new_state):
        """Executa comando e adiciona ao histórico"""
        command = GraphStateCommand(self.canvas, old_state, new_state)
        command.execute()

        # Adicionar ao undo stack
        self.undo_stack.append(command)

        # Limitar tamanho do histórico
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

        # Limpar redo stack (nova ação invalida redo)
        self.redo_stack.clear()

    def record_action(self, old_state):
        """Registra ação capturando novo estado"""
        new_state = self.capture_state()
        self.execute_command(old_state, new_state)

    def undo(self):
        """Desfaz última ação"""
        if not self.undo_stack:
            print("⚠️ Nada para desfazer")
            return False

        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)
        print(f"↶ Undo ({len(self.undo_stack)} restantes)")
        return True

    def redo(self):
        """Refaz última ação desfeita"""
        if not self.redo_stack:
            print("⚠️ Nada para refazer")
            return False

        command = self.redo_stack.pop()
        command.execute()
        self.undo_stack.append(command)
        print(f"↷ Redo ({len(self.redo_stack)} restantes)")
        return True

    def can_undo(self):
        """Verifica se pode desfazer"""
        return len(self.undo_stack) > 0

    def can_redo(self):
        """Verifica se pode refazer"""
        return len(self.redo_stack) > 0

    def clear(self):
        """Limpa histórico"""
        self.undo_stack.clear()
        self.redo_stack.clear()

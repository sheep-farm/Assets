"""
ClipboardManager - Gerenciamento de operações de clipboard

Responsável por copy, paste, duplicate e cut de nós.
Extraído de canvas.py para melhor separação de responsabilidades.
"""

from .node import Node


class ClipboardManager:
    """
    Classe responsável pelas operações de clipboard do canvas.

    Attributes:
        canvas: Referência ao canvas que contém os nós
    """

    def __init__(self, canvas):
        """
        Inicializa o gerenciador de clipboard.

        Args:
            canvas: Instância do AssetsCanvas
        """
        self.canvas = canvas

    def copy_selected_nodes(self):
        """Copia os nós selecionados para o clipboard global (Ctrl+C)"""
        window = self.canvas.get_root()
        if not window:
            print("⚠️  Sem window!")
            return

        # Pegar todos os nós selecionados
        selected_nodes = [node for node in self.canvas.nodes if node.selected]

        if not selected_nodes:
            print("⚠️  Nenhum nó selecionado para copiar")
            return

        # Copiar nós
        window.clipboard_nodes = selected_nodes

        print(f"🔍 Debug - Total de conexões no canvas: {len(self.canvas.connections)}")
        print(f"🔍 Debug - Nós selecionados: {[node.title for node in selected_nodes]}")

        # Copiar conexões relacionadas aos nós selecionados
        # Incluir: conexões entre nós selecionados E conexões que chegam nos nós selecionados
        window.clipboard_connections = []
        for conn in self.canvas.connections:
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

    def paste_nodes(self, paste_x=None, paste_y=None):
        """
        Cola os nós do clipboard global (Ctrl+V ou menu).

        Args:
            paste_x: Posição X onde colar (em coordenadas de canvas). Se None, usa offset
            paste_y: Posição Y onde colar (em coordenadas de canvas). Se None, usa offset
        """
        window = self.canvas.get_root()
        if not window or not window.clipboard_nodes:
            #print("⚠️  Clipboard vazio")
            return

        # Verificar se estamos colando no mesmo projeto (adicionar "(cópia)" no título)
        is_same_project = any(node in self.canvas.nodes for node in window.clipboard_nodes)

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
            self.canvas.nodes.append(new_node)
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
                self.canvas.connections.append(new_conn)
                connections_recreated += 1
                print(f"   ✅ Conexão interna recriada: {new_source.title} -> {new_target.title}")

            # Caso 2: Apenas o target foi colado, source existe no canvas original (conexão de entrada)
            elif source_node not in node_map and target_node in node_map:
                # Procurar o nó de origem no canvas atual pelo ID
                existing_source = None
                for node in self.canvas.nodes:
                    if node.id == source_node.id:
                        existing_source = node
                        break

                if existing_source:
                    new_target = node_map[target_node]
                    # Criar conexão do nó existente para o nó colado
                    new_conn = (existing_source, source_port, new_target, target_port)
                    self.canvas.connections.append(new_conn)
                    connections_to_existing += 1
                    print(f"   ✅ Conexão para nó existente recriada: {existing_source.title} -> {new_target.title}")
                else:
                    print(f"   ⚠️  Nó de origem '{source_node.title}' não encontrado no canvas")

            else:
                print(f"⚠️  Conexão não recriada: source={source_node in node_map}, target={target_node in node_map}")

        total_connections = connections_recreated + connections_to_existing
        print(f"📌 Colado: {len(new_nodes)} nó(s), {connections_recreated} conexão(ões) internas, {connections_to_existing} para nós existentes ({total_connections} total)")

        # Desselecionar todos
        for node in self.canvas.nodes:
            node.set_selected(False)

        # Selecionar os novos nós
        for new_node in new_nodes:
            new_node.set_selected(True)

        # Atualizar foco para o último nó colado
        if new_nodes:
            self.canvas.focused_node_index = self.canvas.nodes.index(new_nodes[-1])

        self.canvas.queue_draw()

    def paste_nodes_as_reference(self, paste_x=None, paste_y=None):
        """
        Cola os nós do clipboard como REFERÊNCIA (Ctrl+R).
        Cria novos nós que referenciam o código do original, mas sem copiar conexões.

        Args:
            paste_x: Posição X onde colar (em coordenadas de canvas). Se None, usa offset
            paste_y: Posição Y onde colar (em coordenadas de canvas). Se None, usa offset
        """
        window = self.canvas.get_root()
        if not window or not window.clipboard_nodes:
            return

        # Se não foi fornecida posição, usar offset padrão
        if paste_x is None or paste_y is None:
            # Usar offset para Ctrl+R (teclado)
            offset = 30
            use_offset = True
        else:
            # Usar posição do mouse para colar via menu de contexto
            use_offset = False

        new_nodes = []
        node_map = {}  # Mapear nós antigos -> novos para recriar conexões

        # Calcular centro do grupo de nós copiados (para posicionar relativo ao mouse)
        if not use_offset:
            min_x = min(node.x for node in window.clipboard_nodes)
            min_y = min(node.y for node in window.clipboard_nodes)
            max_x = max(node.x for node in window.clipboard_nodes)
            max_y = max(node.y for node in window.clipboard_nodes)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

        # Criar nós por referência
        for clipboard_node in window.clipboard_nodes:
            # Título com indicador de referência
            title = f"{clipboard_node.title} (ref)"

            # Calcular posição do novo nó
            if use_offset:
                # Ctrl+R: offset simples
                new_x = clipboard_node.x + 30
                new_y = clipboard_node.y + 30
            else:
                # Menu contexto: posicionar relativo ao mouse
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

            # Copiar propriedades, EXCETO código (que será por referência)
            new_node.code = ""  # Código vazio (usa referência)
            new_node.code_ref = clipboard_node.id  # REFERÊNCIA ao nó original
            new_node.description = clipboard_node.description
            new_node.author = clipboard_node.author
            new_node.version = clipboard_node.version
            new_node.tags = clipboard_node.tags.copy() if clipboard_node.tags else []
            new_node.category = clipboard_node.category
            new_node.custom_color = clipboard_node.custom_color

            # Adicionar à lista
            self.canvas.nodes.append(new_node)
            new_nodes.append(new_node)

            # Mapear nó antigo -> novo para recriar conexões
            node_map[clipboard_node] = new_node

        # Recriar conexões entre os nós colados (igual ao paste_nodes)
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
                self.canvas.connections.append(new_conn)
                connections_recreated += 1

            # Caso 2: Apenas o target foi colado, source existe no canvas original (conexão de entrada)
            elif source_node not in node_map and target_node in node_map:
                # Procurar o nó de origem no canvas atual pelo ID
                existing_source = None
                for node in self.canvas.nodes:
                    if node.id == source_node.id:
                        existing_source = node
                        break

                if existing_source:
                    new_target = node_map[target_node]
                    # Criar conexão do nó existente para o nó colado
                    new_conn = (existing_source, source_port, new_target, target_port)
                    self.canvas.connections.append(new_conn)
                    connections_to_existing += 1

        total_connections = connections_recreated + connections_to_existing

        # Desselecionar todos
        for node in self.canvas.nodes:
            node.selected = False

        # Selecionar apenas os novos nós
        for new_node in new_nodes:
            new_node.selected = True

        # Atualizar foco para o último nó colado
        if new_nodes:
            self.canvas.focused_node_index = self.canvas.nodes.index(new_nodes[-1])

        print(f"📋 Colado como referência: {len(new_nodes)} nó(s), {total_connections} conexão(ões)")
        self.canvas.queue_draw()

    def duplicate_selected_nodes(self):
        """Duplica o nó focado (Ctrl+D) - atalho para copiar+colar"""
        if 0 <= self.canvas.focused_node_index < len(self.canvas.nodes):
            # Copiar
            self.copy_selected_nodes()
            # Colar imediatamente
            self.paste_nodes()
        #else:
         #   print("⚠️  Nenhum nó selecionado para duplicar")

    def cut_context_node(self):
        """Recorta o nó do menu de contexto (copia e remove)"""
        if not hasattr(self.canvas, 'context_menu_node') or self.canvas.context_menu_node is None:
            return

        # Selecionar o nó do contexto (se não estiver)
        if not self.canvas.context_menu_node.selected:
            for node in self.canvas.nodes:
                node.set_selected(False)
            self.canvas.context_menu_node.set_selected(True)

        # Copiar
        self.copy_selected_nodes()

        # Remover o nó
        node_to_delete = self.canvas.context_menu_node

        # Remover conexões associadas ao nó
        self.canvas.connections = [
            conn for conn in self.canvas.connections
            if conn[0] != node_to_delete and conn[2] != node_to_delete
        ]

        # Remover o nó
        if node_to_delete in self.canvas.nodes:
            self.canvas.nodes.remove(node_to_delete)

        self.canvas.context_menu_node = None
        self.canvas._update_canvas_size()
        self.canvas.queue_draw()

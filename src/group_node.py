#!/usr/bin/env python3
"""
group_node.py - Node que encapsula sub-grafo (versão profissional)
"""

from .node import Node
import cairo


class GroupNode(Node):
    """
    Node que contém um sub-grafo interno.

    Características:
    - Comportamento visual normal (não expande/contrai)
    - Edição em aba separada
    - Interface definida por InputNode/OutputNode internos
    - Pode ser salvo na biblioteca
    - Pode ser desempacotado
    """

    COLOR_HEADER = (0.5, 0.3, 0.7)  # Roxo
    COLOR_BODY = (0.95, 0.92, 0.97)  # Roxo claro

    def __init__(self, x, y, title="Group", node_id=None):
        # Número de inputs/outputs será determinado pelos InputNode/OutputNode internos
        super().__init__(
            x=x,
            y=y,
            title=title,
            num_inputs=1,   # Inicial, será ajustado
            num_outputs=1,  # Inicial, será ajustado
            node_id=node_id
        )

        # Sub-grafo interno
        self.inner_nodes = []           # Lista de nodes internos
        self.inner_connections = []     # Conexões: [(src_node, src_port, dst_node, dst_port), ...]

        # Referências aos nodes especiais internos
        self.input_node = None   # InputNode (único)
        self.output_node = None  # OutputNode (único)

        # Identificação
        self.is_group = True
        self.node_type = "group"

        # Código não editável diretamente
        self._code = "# [GROUP NODE - Edite em aba separada]"
        self.code_editable = False

        # Categoria
        self.category = "Groups"
        self.description = "Grupo de nodes encapsulados"

        # Cor customizada para grupos
        self.custom_color = self.COLOR_HEADER

    @property
    def code(self):
        """GroupNode não tem código editável"""
        return self._code

    @code.setter
    def code(self, value):
        """Ignora tentativas de editar código"""
        pass

    def set_input_node(self, input_node):
        """
        Define o InputNode interno e ajusta portas do GroupNode.

        Args:
            input_node: InputNode instance
        """
        self.input_node = input_node

        # Ajustar número de inputs do GroupNode
        self.num_inputs = input_node.num_outputs
        self.input_types = input_node.output_types.copy()
        self.input_docs = input_node.output_docs.copy()

        # Recalcular altura
        self._recalculate_height()

    def set_output_node(self, output_node):
        """
        Define o OutputNode interno e ajusta portas do GroupNode.

        Args:
            output_node: OutputNode instance
        """
        self.output_node = output_node

        # Ajustar número de outputs do GroupNode
        self.num_outputs = output_node.num_inputs
        self.output_types = output_node.input_types.copy()
        self.output_docs = output_node.input_docs.copy()

        # Recalcular altura
        self._recalculate_height()

    def _recalculate_height(self):
        """Recalcula altura baseado no número de portas"""
        max_ports = max(self.num_inputs, self.num_outputs)
        self.body_height = max_ports * self.HEIGHT_PORT + self.PADDING * 2
        self.total_height = self.HEIGHT_HEADER + self.body_height

    def add_inner_node(self, node):
        """Adiciona node ao sub-grafo"""
        if node not in self.inner_nodes:
            self.inner_nodes.append(node)

    def remove_inner_node(self, node):
        """Remove node do sub-grafo"""
        if node in self.inner_nodes:
            self.inner_nodes.remove(node)

            # Remover conexões relacionadas
            self.inner_connections = [
                conn for conn in self.inner_connections
                if conn[0] != node and conn[2] != node
            ]

    def add_inner_connection(self, src_node, src_port, dst_node, dst_port):
        """Adiciona conexão interna"""
        conn = (src_node, src_port, dst_node, dst_port)
        if conn not in self.inner_connections:
            self.inner_connections.append(conn)

    def remove_inner_connection(self, src_node, src_port, dst_node, dst_port):
        """Remove conexão interna"""
        conn = (src_node, src_port, dst_node, dst_port)
        if conn in self.inner_connections:
            self.inner_connections.remove(conn)

    def draw(self, cr, theme_colors=None, dimmed=False):
        """Desenha GroupNode com badge especial"""
        # Desenho base
        super().draw(cr, theme_colors)

        # Ícone de grupo
        cr.set_source_rgb(1, 1, 1)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(18)
        cr.move_to(self.x + self.WIDTH - 35, self.y + 28)
        cr.show_text("📦")

        # Badge "GROUP"
        cr.set_font_size(9)
        badge_x = self.x + 10
        badge_y = self.y + self.total_height - 8

        cr.set_source_rgb(0.5, 0.3, 0.7)
        cr.move_to(badge_x, badge_y)
        inner_count = len([n for n in self.inner_nodes if getattr(n, 'node_type', 'normal') not in ['input', 'output']])
        cr.show_text(f"GROUP ({inner_count} nodes)")

    def execute_inner_graph(self, external_inputs, project_dir=None):
        """
        Executa o sub-grafo interno.

        Flow:
        1. external_inputs → InputNode
        2. InputNode outputs → grafo interno
        3. Grafo interno → OutputNode inputs
        4. OutputNode → return

        Args:
            external_inputs: Tuple de valores de entrada
            project_dir: Diretório do projeto (opcional, para data_helpers)

        Returns:
            tuple: Valores de saída
        """
        print(f"\n📦 Executando GroupNode: {self.title}")
        print(f"   External inputs: {external_inputs}")
        print(f"   Nodes internos: {len(self.inner_nodes)}")
        print(f"   Conexões internas: {len(self.inner_connections)}")
        if self.output_node:
            print(f"   OutputNode tem {self.output_node.num_inputs} portas de entrada")

        # 1. Verificar se tem InputNode e OutputNode
        if not self.input_node:
            print("   ⚠️  GroupNode sem InputNode, criando um padrão...")
            # Criar InputNode padrão se não existir
            from .input_node import InputNode
            self.input_node = InputNode(50, 50, num_outputs=self.num_inputs)
            self.add_inner_node(self.input_node)

        if not self.output_node:
            print("   ⚠️  GroupNode sem OutputNode, criando um padrão...")
            # Criar OutputNode padrão se não existir
            from .output_node import OutputNode
            self.output_node = OutputNode(400, 50, num_inputs=self.num_outputs)
            self.add_inner_node(self.output_node)

        # 2. Criar dicionário de resultados, começando com InputNode
        node_results = {}

        # InputNode "retorna" os external_inputs
        node_results[self.input_node] = external_inputs
        print(f"   InputNode outputs: {external_inputs}")

        # 3. Ordenar nós internos topologicamente
        execution_order = self._topological_sort_inner()

        if execution_order is None:
            print("   ❌ Grafo interno contém ciclos!")
            return (None,) * self.num_outputs

        print(f"   Ordem de execução: {[n.title for n in execution_order]}")

        # 4. Executar cada nó interno (exceto InputNode que já foi "executado")
        for node in execution_order:
            # Pular InputNode (já processado)
            node_type = getattr(node, 'node_type', 'normal')
            if node_type == 'input' or node == self.input_node:
                continue  # Já processado

            try:
                # Coletar inputs deste nó
                inputs = self._collect_inner_node_inputs(node, node_results)
                print(f"      Inputs de {node.title} ({node.num_inputs} portas): {inputs}")

                # Se é OutputNode, apenas guardar inputs
                if node_type == 'output' or node == self.output_node:
                    node_results[node] = inputs
                    print(f"      ✓ {node.title} (coletou outputs)")
                    continue

                # Se é GroupNode aninhado, executar recursivamente
                if isinstance(node, GroupNode):
                    print(f"      📦 GroupNode aninhado: {node.title}")
                    result = node.execute_inner_graph(inputs, project_dir=project_dir)
                    if not isinstance(result, tuple):
                        result = (result,)
                    node_results[node] = result
                    print(f"      ✓ {node.title} (GroupNode) → outputs: {result if len(str(result)) < 100 else str(result)[:100] + '...'}")
                    continue

                # Executar código do nó
                effective_code = node.get_effective_code({n.id: n for n in self.inner_nodes})

                # Verificar se há código executável (não apenas comentários/whitespace)
                has_executable_code = False
                if effective_code:
                    for line in effective_code.split('\n'):
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#'):
                            has_executable_code = True
                            break

                if has_executable_code:
                    # Transformar código em função
                    code_as_function = "def __node_function(inputs):\n"
                    for line in effective_code.split('\n'):
                        code_as_function += f"    {line}\n"

                    # Criar namespace com bibliotecas comuns (igual ao graph_executor)
                    from pathlib import Path
                    namespace = {
                        '__builtins__': __builtins__,
                        # Bibliotecas comuns
                        'pd': __import__('pandas'),
                        'np': __import__('numpy'),
                        'plt': __import__('matplotlib.pyplot'),
                        'Path': Path,
                        # Diretórios úteis
                        'nodes_dir': Path.home() / ".nodes",
                        'home_dir': Path.home(),
                    }

                    # Adicionar data_helpers se project_dir disponível
                    if project_dir:
                        from .data_helpers import create_data_helpers
                        helpers = create_data_helpers(project_dir)
                        namespace.update({
                            'load_data': helpers['load_data'],
                            'save_data': helpers['save_data'],
                            'load': helpers['load'],
                            'save': helpers['save'],
                            'project_dir': helpers['project_dir'],
                        })

                    exec(code_as_function, namespace)

                    # Executar
                    result = namespace['__node_function'](inputs)

                    # Garantir tupla
                    if not isinstance(result, tuple):
                        result = (result,)

                    node_results[node] = result
                    print(f"      ✓ {node.title} → outputs: {result if len(str(result)) < 100 else str(result)[:100] + '...'}")
                else:
                    # Nó sem código: passar inputs como outputs
                    node_results[node] = inputs
                    print(f"      ⚠️  {node.title} (sem código)")

            except Exception as e:
                print(f"      ✗ {node.title}: {e}")
                import traceback
                traceback.print_exc()
                node_results[node] = (None,) * node.num_outputs

        # 5. Extrair outputs do OutputNode
        output_found = False
        outputs = None

        # Buscar OutputNode nos resultados (por tipo, não por identidade)
        for node, result in node_results.items():
            node_type = getattr(node, 'node_type', 'normal')
            if node_type == 'output' or node == self.output_node:
                outputs = result
                output_found = True
                break

        if output_found and outputs is not None:
            print(f"✓ GroupNode {self.title} concluído")
            return outputs
        else:
            print(f"❌ OutputNode não foi executado!")
            return (None,) * self.num_outputs

    def _topological_sort_inner(self):
        """Ordena nós internos topologicamente usando Kahn's algorithm"""
        from .input_node import InputNode
        from .output_node import OutputNode

        # Criar mapa de in_degree
        in_degree = {node: 0 for node in self.inner_nodes}
        adjacency = {node: [] for node in self.inner_nodes}

        # Construir grafo
        for src_node, src_port, dst_node, dst_port in self.inner_connections:
            if src_node in adjacency and dst_node in in_degree:
                adjacency[src_node].append(dst_node)
                in_degree[dst_node] += 1

        # Nós sem dependências (começar com InputNode)
        queue = [node for node in self.inner_nodes if in_degree[node] == 0]
        result = []

        # Garantir que InputNode vem primeiro
        if self.input_node and self.input_node in queue:
            queue.remove(self.input_node)
            queue.insert(0, self.input_node)

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Verificar ciclos
        if len(result) != len(self.inner_nodes):
            return None

        return result

    def _collect_inner_node_inputs(self, node, node_results):
        """Coleta inputs de um nó interno baseado nas conexões"""
        # Usar listas para acumular múltiplas conexões na mesma porta
        inputs_accumulator = [[] for _ in range(node.num_inputs)]

        # Criar mapa de IDs para resultados (para evitar problemas de identidade)
        id_to_result = {n.id: result for n, result in node_results.items()}

        # Debug: contar conexões encontradas
        connections_found = 0

        # Para cada conexão que entra neste nó
        for src_node, src_port, dst_node, dst_port in self.inner_connections:
            # Comparar por ID ao invés de identidade de objeto
            if dst_node.id == node.id and src_node.id in id_to_result:
                source_outputs = id_to_result[src_node.id]
                if src_port < len(source_outputs):
                    # Acumular valor na lista da porta
                    inputs_accumulator[dst_port].append(source_outputs[src_port])
                    connections_found += 1
                    print(f"         └─ Conexão: {src_node.title}[{src_port}] → {node.title}[{dst_port}] = {source_outputs[src_port]}")

        if connections_found == 0 and node.num_inputs > 0:
            print(f"         ⚠️  Nenhuma conexão encontrada para {node.title}")

        # Converter acumuladores para valores finais
        inputs = []
        for port_values in inputs_accumulator:
            if len(port_values) == 0:
                # Nenhuma conexão: None
                inputs.append(None)
            elif len(port_values) == 1:
                # Uma conexão: valor direto
                inputs.append(port_values[0])
            else:
                # Múltiplas conexões: lista
                inputs.append(port_values)

        return tuple(inputs)

    def to_dict(self):
        """Serializa GroupNode"""
        data = super().to_dict()
        data.update({
            'node_type': 'group',
            'is_group': True,
            'inner_nodes': [n.to_dict() for n in self.inner_nodes],
            'inner_connections': [
                {
                    'src_id': src.id,
                    'src_port': src_p,
                    'dst_id': dst.id,
                    'dst_port': dst_p
                }
                for src, src_p, dst, dst_p in self.inner_connections
            ],
            'input_node_id': self.input_node.id if self.input_node else None,
            'output_node_id': self.output_node.id if self.output_node else None
        })
        return data

    @staticmethod
    def from_dict(data):
        """Deserializa GroupNode"""
        from .input_node import InputNode
        from .output_node import OutputNode

        group = GroupNode(
            x=data['x'],
            y=data['y'],
            title=data['title'],
            node_id=data.get('id')
        )

        # Reconstruir nodes internos
        node_map = {}
        for node_data in data.get('inner_nodes', []):
            node_type = node_data.get('node_type', 'normal')

            if node_type == 'input':
                inner_node = InputNode.from_dict(node_data)
                group.set_input_node(inner_node)
            elif node_type == 'output':
                inner_node = OutputNode.from_dict(node_data)
                group.set_output_node(inner_node)
            elif node_type == 'group':
                inner_node = GroupNode.from_dict(node_data)
            else:
                inner_node = Node.from_dict(node_data)

            group.add_inner_node(inner_node)
            node_map[inner_node.id] = inner_node

        # Reconstruir conexões
        for conn_data in data.get('inner_connections', []):
            src = node_map.get(conn_data['src_id'])
            dst = node_map.get(conn_data['dst_id'])
            if src and dst:
                group.add_inner_connection(
                    src, conn_data['src_port'],
                    dst, conn_data['dst_port']
                )

        return group

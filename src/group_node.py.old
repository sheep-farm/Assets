#!/usr/bin/env python3
"""
group_node.py - Implementação de GroupNode (nó que contém sub-grafo)
"""

import cairo
from .node import Node


class GroupNode(Node):
    """
    Nó que contém um sub-grafo de nós internos.
    Comporta-se como um nó normal externamente, mas internamente executa múltiplos nós.
    """
    
    # Cores específicas para grupos
    COLOR_HEADER = (0.6, 0.3, 0.8)  # Roxo
    COLOR_BODY_COLLAPSED = (0.95, 0.92, 0.97)  # Roxo muito claro
    COLOR_BODY_EXPANDED = (0.92, 0.92, 0.96)  # Azul muito claro
    
    def __init__(self, x, y, title="Group", num_inputs=1, num_outputs=1, node_id=None):
        super().__init__(x, y, title, num_inputs, num_outputs, node_id)
        
        # Sub-grafo interno
        self.inner_nodes = []           # Lista de nós internos
        self.inner_connections = []     # Conexões internas: (src_node, src_port, dst_node, dst_port)
        
        # Mapeamento de portas externas para internas
        # Format: {porta_externa: (node_id_interno, porta_interna)}
        self.input_mapping = {}   # Mapeia entradas externas para nós internos
        self.output_mapping = {}  # Mapeia saídas internas para portas externas
        
        # Estado visual
        self.expanded = False
        self.collapsed_height = self.total_height
        self.expanded_height = 400
        
        # Posição original dos nós internos (relativa ao grupo)
        self._original_positions = {}
    
    def add_inner_node(self, node):
        """
        Adiciona um nó ao sub-grafo interno.
        
        Args:
            node: Node a ser adicionado
        """
        # Guardar posição original (relativa ao grupo)
        self._original_positions[node.id] = (node.x, node.y)
        self.inner_nodes.append(node)
    
    def add_inner_connection(self, src_node, src_port, dst_node, dst_port):
        """
        Adiciona uma conexão interna.
        
        Args:
            src_node: Nó de origem
            src_port: Porta de saída
            dst_node: Nó de destino
            dst_port: Porta de entrada
        """
        self.inner_connections.append((src_node, src_port, dst_node, dst_port))
    
    def map_input(self, external_port, internal_node_id, internal_port):
        """
        Mapeia porta de entrada externa para porta interna.
        
        Args:
            external_port: Índice da porta externa (0, 1, ...)
            internal_node_id: ID do nó interno que receberá o input
            internal_port: Porta do nó interno
        """
        self.input_mapping[external_port] = (internal_node_id, internal_port)
    
    def map_output(self, external_port, internal_node_id, internal_port):
        """
        Mapeia porta de saída interna para porta externa.
        
        Args:
            external_port: Índice da porta externa (0, 1, ...)
            internal_node_id: ID do nó interno que fornecerá o output
            internal_port: Porta do nó interno
        """
        self.output_mapping[external_port] = (internal_node_id, internal_port)
    
    def toggle_expanded(self):
        """Alterna entre estado colapsado e expandido"""
        self.expanded = not self.expanded
        if self.expanded:
            self.total_height = self.expanded_height
            self.body_height = self.expanded_height - self.HEIGHT_HEADER
        else:
            self.total_height = self.collapsed_height
            # Recalcular body_height baseado em num de portas
            max_ports = max(self.num_inputs, self.num_outputs)
            self.body_height = max_ports * self.HEIGHT_PORT + self.PADDING * 2
    
    def draw(self, context):
        """Desenha o grupo (sobrescreve Node.draw)"""
        if self.expanded:
            self._draw_expanded(context)
        else:
            self._draw_collapsed(context)
    
    def _draw_collapsed(self, context):
        """Desenha versão colapsada (como nó normal com ícone)"""
        # Corpo
        context.set_source_rgb(*self.COLOR_BODY_COLLAPSED)
        context.rectangle(
            self.x,
            self.y + self.HEIGHT_HEADER,
            self.WIDTH,
            self.body_height
        )
        context.fill()
        
        # Header
        self._draw_header(context)
        
        # Ícone de grupo no canto superior direito
        context.set_source_rgb(1, 1, 1)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(18)
        context.move_to(self.x + self.WIDTH - 35, self.y + 28)
        context.show_text("📦")
        
        # Indicador de expansão (seta para baixo)
        context.set_font_size(14)
        context.move_to(self.x + self.WIDTH - 55, self.y + 28)
        context.show_text("▼")
        
        # Portas
        self._draw_input_ports(context)
        self._draw_output_ports(context)
        
        # Borda
        self._draw_border(context)
        
        # Indicador de seleção
        if self.selected:
            self._draw_selection_indicator(context)
    
    def _draw_expanded(self, context):
        """Desenha versão expandida (mostrando conteúdo interno)"""
        # Fundo expandido
        context.set_source_rgb(*self.COLOR_BODY_EXPANDED)
        context.rectangle(
            self.x,
            self.y,
            self.WIDTH,
            self.expanded_height
        )
        context.fill()
        
        # Header
        self._draw_header(context)
        
        # Indicador de colapso (seta para cima)
        context.set_source_rgb(1, 1, 1)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(14)
        context.move_to(self.x + self.WIDTH - 55, self.y + 28)
        context.show_text("▲")
        
        # Linha separadora
        context.set_source_rgb(0.5, 0.5, 0.5)
        context.set_line_width(1)
        context.move_to(self.x, self.y + self.HEIGHT_HEADER)
        context.line_to(self.x + self.WIDTH, self.y + self.HEIGHT_HEADER)
        context.stroke()
        
        # Desenhar nós internos (versão mini)
        y_offset = self.y + self.HEIGHT_HEADER + 10
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(10)
        
        max_nodes_to_show = min(len(self.inner_nodes), 10)
        for i in range(max_nodes_to_show):
            node = self.inner_nodes[i]
            
            # Caixinha mini do nó
            mini_h = 25
            context.set_source_rgb(0.75, 0.75, 0.75)
            context.rectangle(
                self.x + 10,
                y_offset + i * (mini_h + 5),
                self.WIDTH - 20,
                mini_h
            )
            context.fill()
            
            # Borda
            context.set_source_rgb(0.5, 0.5, 0.5)
            context.set_line_width(1)
            context.rectangle(
                self.x + 10,
                y_offset + i * (mini_h + 5),
                self.WIDTH - 20,
                mini_h
            )
            context.stroke()
            
            # Nome do nó
            context.set_source_rgb(0.1, 0.1, 0.1)
            node_name = node.title[:25] + "..." if len(node.title) > 25 else node.title
            context.move_to(self.x + 15, y_offset + i * (mini_h + 5) + 16)
            context.show_text(node_name)
        
        # Se houver mais nós, mostrar "..."
        if len(self.inner_nodes) > max_nodes_to_show:
            context.set_source_rgb(0.4, 0.4, 0.4)
            context.move_to(self.x + 15, y_offset + max_nodes_to_show * 30 + 16)
            context.show_text(f"... +{len(self.inner_nodes) - max_nodes_to_show} more")
        
        # Portas
        self._draw_input_ports(context)
        self._draw_output_ports(context)
        
        # Borda
        self._draw_border(context)
        
        # Indicador de seleção
        if self.selected:
            self._draw_selection_indicator(context)
    
    def execute_inner_graph(self, external_inputs):
        """
        Executa o sub-grafo interno.
        
        Args:
            external_inputs: Tupla com valores das portas externas
            
        Returns:
            Tupla com valores das portas de saída externas
        """
        import sys
        out = sys.__stdout__
        
        print(f"\n📦 Executando GroupNode: {self.title}", file=out)
        print(f"   Nós internos: {len(self.inner_nodes)}", file=out)
        print(f"   Conexões internas: {len(self.inner_connections)}", file=out)
        
        # Dicionário para armazenar resultados de nós internos
        node_results = {}
        
        # 1. Injetar inputs externos nos nós internos mapeados
        for ext_port, value in enumerate(external_inputs):
            if ext_port in self.input_mapping:
                internal_node_id, int_port = self.input_mapping[ext_port]
                print(f"   Mapeando in[{ext_port}] → node_id={internal_node_id[:8]}...", file=out)
                
                # Encontrar nó interno
                internal_node = next((n for n in self.inner_nodes if n.id == internal_node_id), None)
                if internal_node:
                    # Criar entrada "virtual" para este nó
                    # (será usado na coleta de inputs)
                    if internal_node not in node_results:
                        node_results[internal_node] = (None,) * internal_node.num_outputs
                    
                    # IMPORTANTE: Injetar o valor na "porta virtual"
                    # Vamos usar um dicionário separado para inputs externos
                    if not hasattr(self, '_injected_inputs'):
                        self._injected_inputs = {}
                    if internal_node not in self._injected_inputs:
                        self._injected_inputs[internal_node] = [None] * internal_node.num_inputs
                    self._injected_inputs[internal_node][int_port] = value
        
        # 2. Executar nós internos em ordem topológica
        execution_order = self._topological_sort_inner()
        
        if execution_order is None:
            print(f"   ❌ Grafo interno tem ciclos!", file=out)
            return (None,) * self.num_outputs
        
        print(f"   Ordem de execução: {[n.title for n in execution_order]}", file=out)
        
        # 3. Executar cada nó interno
        for node in execution_order:
            try:
                # Coletar inputs deste nó
                inputs = self._collect_inner_node_inputs(node, node_results)
                
                # Executar código do nó
                if node.code and node.code.strip():
                    # Transformar código em função
                    code_as_function = "def __node_function(inputs):\n"
                    for line in node.code.split('\n'):
                        code_as_function += f"    {line}\n"
                    
                    namespace = {'__builtins__': __builtins__}
                    exec(code_as_function, namespace)
                    
                    # Executar
                    result = namespace['__node_function'](inputs)
                    
                    # Garantir tupla
                    if not isinstance(result, tuple):
                        result = (result,)
                    
                    node_results[node] = result
                    print(f"      ✓ {node.title}", file=out)
                else:
                    # Nó sem código: passar inputs como outputs
                    node_results[node] = inputs
                    print(f"      ⚠️  {node.title} (sem código)", file=out)
            
            except Exception as e:
                print(f"      ✗ {node.title}: {e}", file=out)
                import traceback
                traceback.print_exc()
                node_results[node] = (None,) * node.num_outputs
        
        # 4. Coletar outputs dos nós internos mapeados
        external_outputs = []
        for ext_port in range(self.num_outputs):
            if ext_port in self.output_mapping:
                internal_node_id, int_port = self.output_mapping[ext_port]
                
                # Encontrar nó interno
                internal_node = next((n for n in self.inner_nodes if n.id == internal_node_id), None)
                
                if internal_node and internal_node in node_results:
                    output_value = node_results[internal_node][int_port]
                    external_outputs.append(output_value)
                    print(f"   Mapeando out[{ext_port}] ← node_id={internal_node_id[:8]}...", file=out)
                else:
                    external_outputs.append(None)
                    print(f"   ⚠️  out[{ext_port}] não mapeado ou nó não executado", file=out)
            else:
                external_outputs.append(None)
        
        # Limpar inputs injetados
        if hasattr(self, '_injected_inputs'):
            delattr(self, '_injected_inputs')
        
        print(f"✓ GroupNode {self.title} concluído", file=out)
        return tuple(external_outputs)
    
    def _topological_sort_inner(self):
        """Ordena nós internos topologicamente"""
        in_degree = {node: 0 for node in self.inner_nodes}
        adjacency = {node: [] for node in self.inner_nodes}
        
        for src_node, src_port, dst_node, dst_port in self.inner_connections:
            adjacency[src_node].append(dst_node)
            in_degree[dst_node] += 1
        
        # Kahn's algorithm
        queue = [node for node in self.inner_nodes if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Verificar ciclos
        if len(result) != len(self.inner_nodes):
            return None
        
        return result
    
    def _collect_inner_node_inputs(self, node, node_results):
        """Coleta inputs de um nó interno"""
        inputs = [None] * node.num_inputs
        
        # Primeiro, aplicar inputs externos injetados (se houver)
        if hasattr(self, '_injected_inputs') and node in self._injected_inputs:
            for port_idx, value in enumerate(self._injected_inputs[node]):
                if value is not None:
                    inputs[port_idx] = value
        
        # Depois, aplicar inputs de conexões internas (podem sobrescrever)
        for src_node, src_port, dst_node, dst_port in self.inner_connections:
            if dst_node == node and src_node in node_results:
                source_outputs = node_results[src_node]
                if src_port < len(source_outputs):
                    inputs[dst_port] = source_outputs[src_port]
        
        return tuple(inputs)
    
    def to_dict(self):
        """Serializa o grupo"""
        base_dict = super().to_dict()
        base_dict.update({
            "type": "group",
            "inner_nodes": [n.to_dict() for n in self.inner_nodes],
            "inner_connections": [
                {
                    "src_id": src.id,
                    "src_port": src_p,
                    "dst_id": dst.id,
                    "dst_port": dst_p
                }
                for src, src_p, dst, dst_p in self.inner_connections
            ],
            "input_mapping": {str(k): v for k, v in self.input_mapping.items()},
            "output_mapping": {str(k): v for k, v in self.output_mapping.items()},
            "expanded": self.expanded
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data):
        """Deserializa o grupo"""
        group = cls(
            x=data["x"],
            y=data["y"],
            title=data["title"],
            num_inputs=data["num_inputs"],
            num_outputs=data["num_outputs"],
            node_id=data.get("id")
        )
        
        # Reconstruir nós internos
        for node_data in data.get("inner_nodes", []):
            if node_data.get("type") == "group":
                inner_node = GroupNode.from_dict(node_data)
            else:
                inner_node = Node.from_dict(node_data)
            group.inner_nodes.append(inner_node)
        
        # Reconstruir conexões internas
        node_map = {n.id: n for n in group.inner_nodes}
        for conn_data in data.get("inner_connections", []):
            src = node_map.get(conn_data["src_id"])
            dst = node_map.get(conn_data["dst_id"])
            if src and dst:
                group.inner_connections.append((
                    src, conn_data["src_port"],
                    dst, conn_data["dst_port"]
                ))
        
        # Mapeamentos (converter chaves de volta para int)
        group.input_mapping = {int(k): v for k, v in data.get("input_mapping", {}).items()}
        group.output_mapping = {int(k): v for k, v in data.get("output_mapping", {}).items()}
        group.expanded = data.get("expanded", False)
        
        return group
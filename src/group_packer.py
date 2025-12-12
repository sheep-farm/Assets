#!/usr/bin/env python3
"""
group_packer.py - Lógica para empacotar/desempacotar nodes em GroupNode
"""

from .group_node import GroupNode
from .input_node import InputNode
from .output_node import OutputNode


class GroupPacker:
    """
    Responsável por empacotar e desempacotar nodes.

    Features:
    - Detecção inteligente de entradas/saídas
    - Mapeamento automático de conexões
    - Preservação de posições relativas
    - Detecção de fontes compartilhadas (otimização de portas)
    """

    @staticmethod
    def pack_nodes(nodes, all_connections, title="New Group", canvas_x=None, canvas_y=None):
        """
        Empacota nodes selecionados em um GroupNode.

        Args:
            nodes: Lista de nodes a empacotar
            all_connections: Lista de TODAS as conexões do canvas
            title: Título do GroupNode
            canvas_x: Posição X do GroupNode (None = auto)
            canvas_y: Posição Y do GroupNode (None = auto)

        Returns:
            tuple: (GroupNode, conexões_externas_a_criar, conexões_a_remover)
        """
        if not nodes:
            raise ValueError("Nenhum node para empacotar")

        print(f"\n📦 Empacotando {len(nodes)} nodes em '{title}'...")

        # 1. Identificar conexões EXTERNAS (entram/saem do grupo)
        external_inputs_data = GroupPacker._find_external_inputs(nodes, all_connections)
        external_outputs_data = GroupPacker._find_external_outputs(nodes, all_connections)

        print(f"   Entradas externas: {len(external_inputs_data)}")
        print(f"   Saídas externas: {len(external_outputs_data)}")

        # 2. Criar GroupNode
        # Posição: centro dos nodes selecionados (se não especificada)
        if canvas_x is None or canvas_y is None:
            center_x = sum(n.x for n in nodes) / len(nodes)
            center_y = sum(n.y for n in nodes) / len(nodes)
        else:
            center_x = canvas_x
            center_y = canvas_y

        group = GroupNode(x=center_x, y=center_y, title=title)

        # 3. Criar InputNode e OutputNode
        num_inputs = len(external_inputs_data)
        num_outputs = len(external_outputs_data)

        input_node = InputNode(
            x=50,
            y=100,
            num_outputs=num_inputs if num_inputs > 0 else 1
        )

        output_node = OutputNode(
            x=500,
            y=100,
            num_inputs=num_outputs if num_outputs > 0 else 1
        )

        group.add_inner_node(input_node)
        group.add_inner_node(output_node)
        group.set_input_node(input_node)
        group.set_output_node(output_node)

        # 4. Adicionar nodes ao grupo (ajustar posições relativas)
        if nodes:
            min_x = min(n.x for n in nodes)
            min_y = min(n.y for n in nodes)

            for node in nodes:
                # Posição relativa
                node.x = node.x - min_x + 150  # Offset para deixar espaço para InputNode
                node.y = node.y - min_y + 50
                group.add_inner_node(node)

        # 5. Mapear conexões INTERNAS (entre nodes do grupo)
        internal_connections = [
            conn for conn in all_connections
            if conn[0] in nodes and conn[2] in nodes
        ]

        for src, src_p, dst, dst_p in internal_connections:
            group.add_inner_connection(src, src_p, dst, dst_p)

        print(f"   Conexões internas: {len(internal_connections)}")

        # 6. Conectar InputNode aos nodes internos
        for idx, input_data in enumerate(external_inputs_data):
            internal_dst = input_data['internal_node']
            internal_port = input_data['internal_port']

            # InputNode.out[idx] → internal_dst.in[internal_port]
            group.add_inner_connection(
                input_node, idx,
                internal_dst, internal_port
            )
            print(f"      Input[{idx}] → {internal_dst.title}[in{internal_port}]")

        # 7. Conectar nodes internos ao OutputNode
        for idx, output_data in enumerate(external_outputs_data):
            internal_src = output_data['internal_node']
            internal_port = output_data['internal_port']

            # internal_src.out[internal_port] → OutputNode.in[idx]
            group.add_inner_connection(
                internal_src, internal_port,
                output_node, idx
            )
            print(f"      {internal_src.title}[out{internal_port}] → Output[{idx}]")

        # 8. Criar novas conexões externas (para o GroupNode)
        new_external_connections = []

        # Conexões de entrada (external → GroupNode)
        for idx, input_data in enumerate(external_inputs_data):
            external_src = input_data['external_node']
            external_port = input_data['external_port']

            # external_src.out[external_port] → group.in[idx]
            new_external_connections.append((external_src, external_port, group, idx))
            print(f"      Nova conexão IN: {external_src.title}[{external_port}] → Group[in{idx}]")

        # Conexões de saída (GroupNode → external)
        for idx, output_data in enumerate(external_outputs_data):
            external_dst = output_data['external_node']
            external_port = output_data['external_port']

            # group.out[idx] → external_dst.in[external_port]
            new_external_connections.append((group, idx, external_dst, external_port))
            print(f"      Nova conexão OUT: Group[out{idx}] → {external_dst.title}[{external_port}]")

        # 9. Identificar conexões antigas a remover
        connections_to_remove = []

        # Remover todas as conexões que envolvem nodes empacotados
        for conn in all_connections:
            src, src_p, dst, dst_p = conn
            if src in nodes or dst in nodes:
                connections_to_remove.append(conn)

        print(f"✓ Grupo criado: {group.title}")
        print(f"   Inputs: {group.num_inputs}, Outputs: {group.num_outputs}")

        return group, new_external_connections, connections_to_remove

    @staticmethod
    def _find_external_inputs(nodes, connections):
        """
        Encontra conexões que ENTRAM no grupo.

        SMART DETECTION: Se múltiplos nodes dentro do grupo recebem
        da MESMA fonte externa, cria APENAS UMA entrada no GroupNode.

        Returns:
            list: [{'external_node', 'external_port', 'internal_node', 'internal_port'}, ...]
        """
        node_set = set(nodes)
        external_inputs_data = []
        seen_sources = {}  # {(src_node_id, src_port): input_index}

        for src, src_p, dst, dst_p in connections:
            # Se dst está no grupo mas src NÃO está
            if dst in node_set and src not in node_set:
                # Verificar se já vimos essa fonte
                key = (src.id, src_p)

                if key not in seen_sources:
                    # Nova entrada!
                    input_idx = len(external_inputs_data)
                    seen_sources[key] = input_idx

                    external_inputs_data.append({
                        'external_node': src,
                        'external_port': src_p,
                        'internal_node': dst,
                        'internal_port': dst_p
                    })

                    print(f"      Input {input_idx}: {src.title}[{src_p}] → {dst.title}[{dst_p}]")
                else:
                    # Fonte já existe! Precisamos criar conexão adicional DENTRO do grupo
                    # do InputNode para este node interno
                    existing_idx = seen_sources[key]
                    print(f"      ⚠️  Input {existing_idx} compartilhado: {src.title} → {dst.title}")

                    # Adicionar entrada duplicada (será conectada ao mesmo InputNode output)
                    external_inputs_data.append({
                        'external_node': src,
                        'external_port': src_p,
                        'internal_node': dst,
                        'internal_port': dst_p,
                        'shared_input_idx': existing_idx
                    })

        return external_inputs_data

    @staticmethod
    def _find_external_outputs(nodes, connections):
        """
        Encontra conexões que SAEM do grupo.

        Returns:
            list: [{'internal_node', 'internal_port', 'external_node', 'external_port'}, ...]
        """
        node_set = set(nodes)
        external_outputs_data = []

        for src, src_p, dst, dst_p in connections:
            # Se src está no grupo mas dst NÃO está
            if src in node_set and dst not in node_set:
                output_idx = len(external_outputs_data)

                external_outputs_data.append({
                    'internal_node': src,
                    'internal_port': src_p,
                    'external_node': dst,
                    'external_port': dst_p
                })

                print(f"      Output {output_idx}: {src.title}[{src_p}] → {dst.title}[{dst_p}]")

        return external_outputs_data

    @staticmethod
    def unpack_group(group_node, canvas_connections):
        """
        Desempacota um GroupNode, retornando nodes ao canvas principal.

        Args:
            group_node: GroupNode a desempacotar
            canvas_connections: Conexões atuais do canvas (para reconstruir externas)

        Returns:
            tuple: (unpacked_nodes, new_connections, connections_to_remove)
        """
        print(f"\n📤 Desempacotando: {group_node.title}")

        # 1. Nodes a retornar (exceto InputNode e OutputNode)
        unpacked_nodes = [
            node for node in group_node.inner_nodes
            if getattr(node, 'node_type', 'normal') not in ['input', 'output']
        ]

        # 2. Ajustar posições (relativas ao GroupNode no canvas)
        for node in unpacked_nodes:
            node.x += group_node.x - 150  # Compensar offset que foi aplicado ao empacotar
            node.y += group_node.y - 50

        # 3. Conexões internas (exceto as que envolvem Input/OutputNode)
        internal_connections = []
        for conn in group_node.inner_connections:
            src, src_p, dst, dst_p = conn

            src_type = getattr(src, 'node_type', 'normal')
            dst_type = getattr(dst, 'node_type', 'normal')

            # Ignorar conexões com InputNode/OutputNode
            if src_type not in ['input', 'output'] and dst_type not in ['input', 'output']:
                internal_connections.append((src, src_p, dst, dst_p))

        print(f"   Desempacotados: {len(unpacked_nodes)} nodes")
        print(f"   Conexões internas: {len(internal_connections)}")

        # 4. Reconstruir conexões externas
        new_external_connections = []
        input_node = group_node.input_node
        output_node = group_node.output_node

        # Conexões que ENTRAM no grupo (external → GroupNode → internal)
        for src, src_p, dst, dst_p in canvas_connections:
            if dst == group_node:
                # Esta é uma conexão externa → GroupNode
                # Precisamos encontrar para qual node interno ela vai

                # GroupNode.in[dst_p] mapeia para qual internal node?
                if input_node:
                    # Procurar conexão InputNode.out[dst_p] → internal_node
                    for i_src, i_src_p, i_dst, i_dst_p in group_node.inner_connections:
                        if i_src == input_node and i_src_p == dst_p:
                            # Achamos! src → i_dst
                            new_external_connections.append((src, src_p, i_dst, i_dst_p))
                            print(f"      Reconectando IN: {src.title}[{src_p}] → {i_dst.title}[{i_dst_p}]")
                            break

        # Conexões que SAEM do grupo (internal → GroupNode → external)
        for src, src_p, dst, dst_p in canvas_connections:
            if src == group_node:
                # Esta é uma conexão GroupNode → external
                # Precisamos encontrar de qual node interno ela vem

                # GroupNode.out[src_p] vem de qual internal node?
                if output_node:
                    # Procurar conexão internal_node → OutputNode.in[src_p]
                    for i_src, i_src_p, i_dst, i_dst_p in group_node.inner_connections:
                        if i_dst == output_node and i_dst_p == src_p:
                            # Achamos! i_src → dst
                            new_external_connections.append((i_src, i_src_p, dst, dst_p))
                            print(f"      Reconectando OUT: {i_src.title}[{i_src_p}] → {dst.title}[{dst_p}]")
                            break

        # 5. Conexões a remover (todas envolvendo o GroupNode)
        connections_to_remove = [
            conn for conn in canvas_connections
            if conn[0] == group_node or conn[2] == group_node
        ]

        print(f"✓ Desempacotamento concluído")
        print(f"   Novas conexões externas: {len(new_external_connections)}")

        return unpacked_nodes, internal_connections + new_external_connections, connections_to_remove

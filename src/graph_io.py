#!/usr/bin/env python3
"""
graph_io.py - Sistema de salvar/carregar grafos
"""

import json
from pathlib import Path


class GraphSerializer:
    """Serializa e deserializa grafos de nós"""
    
    VERSION = "1.0"
    
    @staticmethod
    def save_graph(nodes, connections, filepath):
        """
        Salva grafo em arquivo JSON.
        
        Args:
            nodes: Lista de objetos Node
            connections: Lista de tuplas (node_origem, porta_saida, node_destino, porta_entrada)
            filepath: Caminho do arquivo
            
        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Criar mapa de node ID para índice
            node_id_to_index = {node.id: i for i, node in enumerate(nodes)}
            
            # Serializar nós
            nodes_data = [node.to_dict() for node in nodes]
            
            # Serializar conexões (usar IDs ao invés de referências)
            connections_data = []
            for conn in connections:
                src_node, src_port, dst_node, dst_port = conn
                connections_data.append({
                    "source_node_id": src_node.id,
                    "source_port": src_port,
                    "target_node_id": dst_node.id,
                    "target_port": dst_port
                })
            
            # Estrutura completa
            graph_data = {
                "version": GraphSerializer.VERSION,
                "nodes": nodes_data,
                "connections": connections_data
            }
            
            # Salvar em arquivo
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Grafo salvo: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar grafo: {e}")
            return False
    
    @staticmethod
    def load_graph(filepath):
        """
        Carrega grafo de arquivo JSON.
        
        Args:
            filepath: Caminho do arquivo
            
        Returns:
            tuple: (nodes, connections) ou (None, None) se erro
        """
        try:
            from .node import Node
            
            with open(filepath, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            # Verificar versão
            version = graph_data.get("version", "1.0")
            if version != GraphSerializer.VERSION:
                print(f"⚠️  Versão do arquivo ({version}) diferente da atual ({GraphSerializer.VERSION})")
            
            # Deserializar nós
            nodes = []
            node_id_map = {}  # Map ID -> node object
            
            for node_data in graph_data.get("nodes", []):
                node = Node.from_dict(node_data)
                nodes.append(node)
                node_id_map[node.id] = node
            
            # Deserializar conexões
            connections = []
            for conn_data in graph_data.get("connections", []):
                src_id = conn_data["source_node_id"]
                dst_id = conn_data["target_node_id"]
                
                if src_id in node_id_map and dst_id in node_id_map:
                    connection = (
                        node_id_map[src_id],
                        conn_data["source_port"],
                        node_id_map[dst_id],
                        conn_data["target_port"]
                    )
                    connections.append(connection)
                else:
                    print(f"⚠️  Conexão inválida ignorada: {src_id} -> {dst_id}")
            
            print(f"✓ Grafo carregado: {filepath}")
            print(f"  - {len(nodes)} nós")
            print(f"  - {len(connections)} conexões")
            
            return nodes, connections
            
        except Exception as e:
            print(f"❌ Erro ao carregar grafo: {e}")
            import traceback
            traceback.print_exc()
            return None, None


def get_default_save_directory():
    """Retorna diretório padrão para salvar grafos"""
    home = Path.home()
    assets_dir = home / ".local" / "share" / "assets" / "graphs"
    assets_dir.mkdir(parents=True, exist_ok=True)
    return assets_dir


def get_recent_files(max_files=10):
    """
    Retorna lista de arquivos recentes.
    
    Args:
        max_files: Número máximo de arquivos
        
    Returns:
        list: Lista de caminhos de arquivos
    """
    save_dir = get_default_save_directory()
    
    # Pegar todos arquivos .assets
    files = list(save_dir.glob("*.assets"))
    
    # Ordenar por data de modificação (mais recente primeiro)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return files[:max_files]

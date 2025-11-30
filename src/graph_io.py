#!/usr/bin/env python3
"""
graph_io.py - Sistema de salvar/carregar grafos

IMPORTANTE: A partir de agora, .assets são arquivos ZIP contendo:
  - graph.json: dados do grafo
  - wheels/: pasta com dependências .whl
"""

import json
from pathlib import Path
from .zip_project import AssetsProject, create_new_project


class GraphSerializer:
    """Serializa e deserializa grafos de nós"""
    
    VERSION = "1.0"
    
    @staticmethod
    def save_graph(nodes, connections, filepath, view_state=None, project_metadata=None):
        """
        Salva grafo em arquivo .assets (ZIP).

        Args:
            nodes: Lista de objetos Node
            connections: Lista de tuplas (node_origem, porta_saida, node_destino, porta_entrada)
            filepath: Caminho do arquivo .assets
            view_state: Dicionário com estado visual (zoom, scroll position, etc.)
            project_metadata: Dicionário com metadados do projeto (requirements, author, etc.)

        Returns:
            bool: True se salvou com sucesso
        """
        try:
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

            # Adicionar estado visual se fornecido
            if view_state:
                graph_data["view_state"] = view_state

            # Adicionar metadados do projeto
            if project_metadata:
                graph_data["project_metadata"] = project_metadata
            else:
                # Metadados padrão com dependências essenciais
                graph_data["project_metadata"] = {
                    "requirements": ["pandas", "numpy", "matplotlib"],
                    "python_mode": "system",  # "system" ou "flatpak"
                    "blacklist": [],
                    "author": "",
                    "description": "",
                    "created_at": None,
                    "modified_at": None
                }

            # Salvar como ZIP usando AssetsProject
            project = AssetsProject(filepath)
            return project.save_graph(graph_data)

        except Exception as e:
            print(f"❌ Erro ao salvar grafo: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def load_graph(filepath, check_dependencies=True):
        """
        Carrega grafo de arquivo .assets (ZIP).

        Args:
            filepath: Caminho do arquivo .assets
            check_dependencies: Se True, verifica dependências (obsoleto, wheels são carregados automaticamente)

        Returns:
            dict: Dicionário com dados brutos {"nodes": [...], "connections": [...]}
                  ou None se erro
        """
        try:
            # Carregar usando AssetsProject
            project = AssetsProject(filepath)
            graph_data = project.load_graph()

            if graph_data is None:
                return None

            # Verificar versão
            version = graph_data.get("version", "1.0")
            if version != GraphSerializer.VERSION:
                print(f"⚠️  Versão do arquivo ({version}) diferente da atual ({GraphSerializer.VERSION})")

            # Retorna apenas o dict - window.py faz a deserialização e setup do ambiente isolado
            return graph_data

        except Exception as e:
            print(f"❌ Erro ao carregar grafo: {e}")
            import traceback
            traceback.print_exc()
            return None


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


def get_templates_directory():
    """Retorna diretório padrão para templates de grafos"""
    home = Path.home()
    templates_dir = home / ".local" / "share" / "assets" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def save_graph_template(nodes, connections, template_name, description=""):
    """
    Salva grafo atual como template.

    Args:
        nodes: Lista de objetos Node
        connections: Lista de conexões
        template_name: Nome do template
        description: Descrição do template

    Returns:
        bool: True se salvou com sucesso
    """
    try:
        templates_dir = get_templates_directory()

        # Serializar grafo
        nodes_data = [node.to_dict() for node in nodes]

        connections_data = []
        for conn in connections:
            src_node, src_port, dst_node, dst_port = conn
            connections_data.append({
                "source_node_id": src_node.id,
                "source_port": src_port,
                "target_node_id": dst_node.id,
                "target_port": dst_port
            })

        # Estrutura do template
        template_data = {
            "name": template_name,
            "description": description,
            "created_at": Path.ctime(Path.home()),  # Timestamp
            "nodes": nodes_data,
            "connections": connections_data
        }

        # Salvar em arquivo
        template_file = templates_dir / f"{template_name}.template"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Template salvo: {template_file}")
        return True

    except Exception as e:
        print(f"❌ Erro ao salvar template: {e}")
        return False


def load_graph_template(template_name):
    """
    Carrega template de grafo.

    Args:
        template_name: Nome do template

    Returns:
        dict: Dicionário com dados do template ou None se erro
    """
    try:
        templates_dir = get_templates_directory()
        template_file = templates_dir / f"{template_name}.template"

        if not template_file.exists():
            print(f"❌ Template não encontrado: {template_name}")
            return None

        with open(template_file, 'r', encoding='utf-8') as f:
            template_data = json.load(f)

        return template_data

    except Exception as e:
        print(f"❌ Erro ao carregar template: {e}")
        return None


def get_all_templates():
    """
    Retorna lista de todos os templates disponíveis.

    Returns:
        list: Lista de dicionários com info dos templates
    """
    templates_dir = get_templates_directory()
    templates = []

    for template_file in templates_dir.glob("*.template"):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            templates.append({
                "name": data.get("name", template_file.stem),
                "description": data.get("description", ""),
                "file": str(template_file),
                "num_nodes": len(data.get("nodes", [])),
                "num_connections": len(data.get("connections", []))
            })
        except Exception as e:
            print(f"⚠️  Erro ao ler template {template_file.name}: {e}")

    return templates

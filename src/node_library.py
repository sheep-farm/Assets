"""
node_library.py - Biblioteca de nós pré-configurados
Carrega nós de arquivos JSON em diretório configurável
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class NodeLibrary:
    """Gerenciador de biblioteca de nós carregada de arquivos JSON"""

    def __init__(self, nodes_dir: Optional[str] = None):
        """
        Inicializa a biblioteca de nós

        Args:
            nodes_dir: Diretório contendo arquivos .json de nós.
                      Se None, usa '~/.nodes' relativo ao arquivo atual.
        """
        if nodes_dir is None:
            # nodes_dir = Path(__file__).parent / "nodes"
            nodes_dir = "/home/flavio/.nodes"

        self.nodes_dir = Path(nodes_dir)
        self.library: Dict = {}
        self._load_all_nodes()

    def _load_all_nodes(self):
        """Carrega todos os arquivos .json do diretório de nós"""
        if not self.nodes_dir.exists():
            print(f"⚠️  Diretório de nós não encontrado: {self.nodes_dir}")
            return

        json_files = list(self.nodes_dir.glob("*.json"))

        if not json_files:
            print(f"⚠️  Nenhum arquivo .json encontrado em: {self.nodes_dir}")
            return

        print(f"📚 Carregando biblioteca de nós de: {self.nodes_dir}")

        for json_file in json_files:
            try:
                self._load_node_file(json_file)
            except Exception as e:
                print(f"❌ Erro ao carregar {json_file.name}: {e}")

    def _load_node_file(self, filepath: Path):
        """Carrega um arquivo JSON de nós"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Arquivo deve conter um objeto JSON")

        # Processa cada categoria no arquivo
        for category_name, category_data in data.items():
            if category_name not in self.library:
                self.library[category_name] = {
                    "icon": category_data.get("icon", "📦"),
                    "nodes": []
                }

            # Adiciona nós da categoria
            nodes = category_data.get("nodes", [])
            self.library[category_name]["nodes"].extend(nodes)

            print(f"  ✓ {category_name}: {len(nodes)} nó(s) de {filepath.name}")

    def get_all_categories(self) -> List[str]:
        """Retorna lista de categorias"""
        return list(self.library.keys())

    def get_nodes_in_category(self, category: str) -> List[Dict]:
        """Retorna lista de nós em uma categoria"""
        if category in self.library:
            return self.library[category]["nodes"]
        return []

    def get_category_icon(self, category: str) -> str:
        """Retorna ícone de uma categoria"""
        if category in self.library:
            return self.library[category]["icon"]
        return "📦"

    def reload(self):
        """Recarrega todos os nós do diretório"""
        self.library.clear()
        self._load_all_nodes()

    def add_nodes_directory(self, directory: str):
        """Adiciona nós de um diretório adicional"""
        additional_dir = Path(directory)
        if not additional_dir.exists():
            print(f"⚠️  Diretório não encontrado: {directory}")
            return

        for json_file in additional_dir.glob("*.json"):
            try:
                self._load_node_file(json_file)
            except Exception as e:
                print(f"❌ Erro ao carregar {json_file.name}: {e}")


# Instância global (mantém compatibilidade com código existente)
_default_library = None


def _get_library() -> NodeLibrary:
    """Obtém a instância padrão da biblioteca"""
    global _default_library
    if _default_library is None:
        _default_library = NodeLibrary()
    return _default_library


# Funções de compatibilidade (mantém API original)
def get_all_categories():
    """Retorna lista de categorias"""
    return _get_library().get_all_categories()


def get_nodes_in_category(category):
    """Retorna lista de nós em uma categoria"""
    return _get_library().get_nodes_in_category(category)


def get_category_icon(category):
    """Retorna ícone de uma categoria"""
    return _get_library().get_category_icon(category)


def create_node_from_template(template, x, y):
    """
    Cria um nó a partir de um template.

    Args:
        template: Dict com definição do nó
        x, y: Posição inicial

    Returns:
        Node object
    """
    from .node import Node

    node = Node(
        x=x,
        y=y,
        title=template["name"],
        num_inputs=template["num_inputs"],
        num_outputs=template["num_outputs"]
    )

    # Suporta default_code como string ou array de linhas
    code = template.get("default_code", "")
    if isinstance(code, list):
        code = "\n".join(code)

    node.code = code

    return node


# Funções utilitárias adicionais
def reload_library():
    """Recarrega a biblioteca de nós"""
    _get_library().reload()


def set_nodes_directory(directory: str):
    """Define um novo diretório de nós"""
    global _default_library
    _default_library = NodeLibrary(directory)


def add_nodes_directory(directory: str):
    """Adiciona um diretório adicional de nós"""
    _get_library().add_nodes_directory(directory)

"""
node_library.py - Biblioteca de nós pré-configurados
Carrega nós de arquivos JSON em diretório configurável
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime


class NodeLibrary:
    """Gerenciador de biblioteca de nós carregada de arquivos JSON"""

    # Schema de validação
    NODE_SCHEMA = {
        "required": ["name", "num_inputs", "num_outputs"],
        "optional": ["description", "default_code", "tags", "author", "version",
                    "input_docs", "output_docs", "color", "category", "visibility"]
    }

    def __init__(self, nodes_dir: Optional[str] = None):
        """
        Inicializa a biblioteca de nós

        Args:
            nodes_dir: Diretório contendo arquivos .json de nós.
                      Se None, usa '~/.nodes' do usuário.
        """
        if nodes_dir is None:
            nodes_dir = str(Path.home() / ".nodes")

        self.nodes_dir = Path(nodes_dir).expanduser()
        self.library: Dict = {}
        self.favorites: Set[str] = set()  # Set de nomes de nodes favoritos
        self._load_favorites()
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

    def save_node_template(self, node, category_name: str, visibility: str = "private"):
        """
        Salva um nó como template na biblioteca.

        Args:
            node: Objeto Node a ser salvo
            category_name: Nome da categoria
            visibility: "private" (local apenas) ou "public" (compartilhável)

        Returns:
            bool: True se salvou com sucesso
        """
        try:
            # Garantir que diretório existe
            self.nodes_dir.mkdir(parents=True, exist_ok=True)

            # Nome do arquivo: my_nodes.json (arquivo do usuário)
            user_file = self.nodes_dir / "my_nodes.json"

            # Carregar arquivo existente ou criar novo
            if user_file.exists():
                try:
                    with open(user_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Arquivo corrompido: {user_file}")
                    print(f"⚠️  Erro: {e}")
                    # Fazer backup do arquivo corrompido
                    backup_file = user_file.with_suffix('.json.backup')
                    import shutil
                    shutil.copy2(user_file, backup_file)
                    print(f"⚠️  Backup criado: {backup_file}")
                    # Começar com dados vazios
                    data = {}
            else:
                data = {}

            # Criar categoria se não existir
            if category_name not in data:
                data[category_name] = {
                    "icon": "",  # Sem ícone para categorias criadas pelo usuário
                    "nodes": []
                }

            # Criar template do nó com todos os metadados
            node_template = {
                "name": node.title,
                "description": node.description or f"Custom node: {node.title}",
                "num_inputs": node.num_inputs,
                "num_outputs": node.num_outputs,
                "default_code": node.code.split('\n') if node.code else [],
                "author": node.author,
                "version": node.version,
                "tags": node.tags,
                "category": node.category,
                "input_docs": node.input_docs,
                "output_docs": node.output_docs,
                "input_types": node.input_types,
                "output_types": node.output_types,
                "color": list(node.custom_color) if node.custom_color else None,
                "visibility": visibility  # "private" ou "public"
            }

            # Verificar se já existe nó com mesmo nome
            existing_nodes = data[category_name]["nodes"]
            existing_names = [n["name"] for n in existing_nodes]

            if node.title in existing_names:
                # Substituir existente
                for i, n in enumerate(existing_nodes):
                    if n["name"] == node.title:
                        existing_nodes[i] = node_template
                        print(f"✓ Nó atualizado: {node.title}")
                        break
            else:
                # Adicionar novo
                existing_nodes.append(node_template)
                print(f"✓ Nó adicionado: {node.title}")

            # Salvar arquivo
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"💾 Salvo em: {user_file}")

            # Recarregar biblioteca
            self.reload()

            return True

        except Exception as e:
            print(f"❌ Erro ao salvar template: {e}")
            import traceback
            traceback.print_exc()
            return False

    def validate_node(self, node_data: Dict) -> tuple[bool, str]:
        """
        Valida se um node segue o schema correto.

        Args:
            node_data: Dicionário com dados do node

        Returns:
            tuple: (is_valid, error_message)
        """
        # Verificar campos obrigatórios
        for field in self.NODE_SCHEMA["required"]:
            if field not in node_data:
                return False, f"Campo obrigatório ausente: {field}"

        # Validar tipos
        if not isinstance(node_data.get("num_inputs"), int):
            return False, "num_inputs deve ser inteiro"

        if not isinstance(node_data.get("num_outputs"), int):
            return False, "num_outputs deve ser inteiro"

        if node_data.get("num_inputs", 0) < 0 or node_data.get("num_outputs", 0) < 0:
            return False, "num_inputs e num_outputs devem ser >= 0"

        # Validar tags (se presente)
        if "tags" in node_data and not isinstance(node_data["tags"], list):
            return False, "tags deve ser uma lista"

        return True, ""

    def search_nodes(self, query: str) -> List[Dict]:
        """
        Busca nodes por nome, descrição ou tags.

        Args:
            query: String de busca

        Returns:
            Lista de nodes que correspondem à busca
        """
        query_lower = query.lower()
        results = []

        for category_name, category_data in self.library.items():
            for node in category_data["nodes"]:
                # Buscar no nome
                if query_lower in node.get("name", "").lower():
                    results.append({**node, "_category": category_name})
                    continue

                # Buscar na descrição
                if query_lower in node.get("description", "").lower():
                    results.append({**node, "_category": category_name})
                    continue

                # Buscar nas tags
                tags = node.get("tags", [])
                if any(query_lower in tag.lower() for tag in tags):
                    results.append({**node, "_category": category_name})
                    continue

        return results

    def get_nodes_by_tags(self, tags: List[str]) -> List[Dict]:
        """
        Retorna nodes que contêm TODAS as tags especificadas.

        Args:
            tags: Lista de tags para filtrar

        Returns:
            Lista de nodes
        """
        tags_lower = [t.lower() for t in tags]
        results = []

        for category_name, category_data in self.library.items():
            for node in category_data["nodes"]:
                node_tags = [t.lower() for t in node.get("tags", [])]
                if all(tag in node_tags for tag in tags_lower):
                    results.append({**node, "_category": category_name})

        return results

    def _load_favorites(self):
        """Carrega lista de favoritos do arquivo"""
        favorites_file = self.nodes_dir / ".favorites.json"
        if favorites_file.exists():
            try:
                with open(favorites_file, 'r') as f:
                    self.favorites = set(json.load(f))
            except Exception as e:
                print(f"⚠️  Erro ao carregar favoritos: {e}")
                self.favorites = set()

    def _save_favorites(self):
        """Salva lista de favoritos no arquivo"""
        favorites_file = self.nodes_dir / ".favorites.json"
        try:
            self.nodes_dir.mkdir(parents=True, exist_ok=True)
            with open(favorites_file, 'w') as f:
                json.dump(list(self.favorites), f, indent=2)
        except Exception as e:
            print(f"❌ Erro ao salvar favoritos: {e}")

    def toggle_favorite(self, node_name: str):
        """Adiciona ou remove um node dos favoritos"""
        if node_name in self.favorites:
            self.favorites.remove(node_name)
        else:
            self.favorites.add(node_name)
        self._save_favorites()

    def is_favorite(self, node_name: str) -> bool:
        """Verifica se um node é favorito"""
        return node_name in self.favorites

    def get_favorites(self) -> List[Dict]:
        """Retorna lista de nodes favoritos"""
        results = []
        for category_name, category_data in self.library.items():
            for node in category_data["nodes"]:
                if node["name"] in self.favorites:
                    results.append({**node, "_category": category_name})
        return results

    def set_node_visibility(self, node_name: str, category_name: str, visibility: str) -> bool:
        """
        Define a visibilidade de um nó na biblioteca.

        Args:
            node_name: Nome do nó
            category_name: Nome da categoria
            visibility: "private" ou "public"

        Returns:
            bool: True se alterou com sucesso
        """
        try:
            # Arquivo do usuário
            user_file = self.nodes_dir / "my_nodes.json"

            if not user_file.exists():
                print(f"❌ Arquivo não encontrado: {user_file}")
                return False

            # Carregar arquivo
            with open(user_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Encontrar e alterar nó
            if category_name not in data:
                print(f"❌ Categoria não encontrada: {category_name}")
                return False

            nodes = data[category_name]["nodes"]
            for node in nodes:
                if node["name"] == node_name:
                    node["visibility"] = visibility

                    # Salvar arquivo
                    with open(user_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    # Recarregar biblioteca
                    self.reload()

                    print(f"✓ Visibilidade de '{node_name}' alterada para '{visibility}'")
                    return True

            print(f"❌ Nó não encontrado: {node_name}")
            return False

        except Exception as e:
            print(f"❌ Erro ao alterar visibilidade: {e}")
            return False

    def get_public_nodes(self) -> List[Dict]:
        """Retorna apenas nós marcados como públicos"""
        results = []
        for category_name, category_data in self.library.items():
            for node in category_data["nodes"]:
                if node.get("visibility", "private") == "public":
                    results.append({**node, "_category": category_name})
        return results

    def get_private_nodes(self) -> List[Dict]:
        """Retorna apenas nós marcados como privados"""
        results = []
        for category_name, category_data in self.library.items():
            for node in category_data["nodes"]:
                if node.get("visibility", "private") == "private":
                    results.append({**node, "_category": category_name})
        return results

    def export_library(self, output_path: str, categories: Optional[List[str]] = None,
                      include_private: bool = False):
        """
        Exporta biblioteca (ou categorias específicas) para arquivo .zip

        Args:
            output_path: Caminho do arquivo .zip de saída
            categories: Lista de categorias para exportar (None = todas)
            include_private: Se True, inclui nós privados; False = apenas públicos
        """
        try:
            output_file = Path(output_path)

            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Metadata do pacote
                metadata = {
                    "exported_at": datetime.now().isoformat(),
                    "categories": categories or list(self.library.keys())
                }
                zipf.writestr("metadata.json", json.dumps(metadata, indent=2))

                # Exportar arquivos JSON das categorias
                for json_file in self.nodes_dir.glob("*.json"):
                    if json_file.name.startswith("."):
                        continue

                    # Carregar e filtrar por categoria e visibilidade
                    with open(json_file, 'r') as f:
                        data = json.load(f)

                    # Filtrar por categoria
                    if categories:
                        filtered_data = {k: v for k, v in data.items() if k in categories}
                    else:
                        filtered_data = data

                    # Filtrar por visibilidade (se include_private=False)
                    if not include_private:
                        for category_name in list(filtered_data.keys()):
                            # Filtrar apenas nós públicos
                            public_nodes = [
                                node for node in filtered_data[category_name]["nodes"]
                                if node.get("visibility", "private") == "public"
                            ]

                            if public_nodes:
                                filtered_data[category_name]["nodes"] = public_nodes
                            else:
                                # Remove categoria se não houver nós públicos
                                del filtered_data[category_name]

                    if filtered_data:
                        zipf.writestr(f"nodes/{json_file.name}",
                                    json.dumps(filtered_data, indent=2))

            print(f"✓ Biblioteca exportada: {output_file}")
            return True

        except Exception as e:
            print(f"❌ Erro ao exportar biblioteca: {e}")
            import traceback
            traceback.print_exc()
            return False

    def import_library(self, zip_path: str, merge: bool = True):
        """
        Importa biblioteca de um arquivo .zip

        Args:
            zip_path: Caminho do arquivo .zip
            merge: Se True, mescla com biblioteca existente; se False, substitui

        Returns:
            bool: True se sucesso
        """
        try:
            zip_file = Path(zip_path)

            if not zip_file.exists():
                print(f"❌ Arquivo não encontrado: {zip_path}")
                return False

            with zipfile.ZipFile(zip_file, 'r') as zipf:
                # Ler metadata
                try:
                    metadata_str = zipf.read("metadata.json").decode('utf-8')
                    metadata = json.loads(metadata_str)
                    print(f"📦 Importando biblioteca exportada em: {metadata.get('exported_at')}")
                except:
                    print("⚠️  Metadata não encontrada, continuando...")

                # Extrair nodes/*.json
                for file_info in zipf.namelist():
                    if file_info.startswith("nodes/") and file_info.endswith(".json"):
                        filename = Path(file_info).name
                        target_file = self.nodes_dir / filename

                        # Se merge=True e arquivo existe, mesclar
                        if merge and target_file.exists():
                            with open(target_file, 'r') as f:
                                existing_data = json.load(f)

                            new_data = json.loads(zipf.read(file_info).decode('utf-8'))

                            # Mesclar categorias
                            for category, content in new_data.items():
                                if category in existing_data:
                                    # Mesclar nodes, evitando duplicatas por nome
                                    existing_names = {n["name"] for n in existing_data[category]["nodes"]}
                                    for node in content["nodes"]:
                                        if node["name"] not in existing_names:
                                            existing_data[category]["nodes"].append(node)
                                else:
                                    existing_data[category] = content

                            # Salvar mesclado
                            with open(target_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_data, f, indent=2, ensure_ascii=False)
                        else:
                            # Substituir completamente
                            self.nodes_dir.mkdir(parents=True, exist_ok=True)
                            with open(target_file, 'wb') as f:
                                f.write(zipf.read(file_info))

                        print(f"  ✓ Importado: {filename}")

            # Recarregar biblioteca
            self.reload()
            print("✓ Importação concluída")
            return True

        except Exception as e:
            print(f"❌ Erro ao importar biblioteca: {e}")
            import traceback
            traceback.print_exc()
            return False


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

    # Metadata adicional
    node.description = template.get("description", "")
    node.author = template.get("author", "")
    node.version = template.get("version", "1.0")
    node.tags = template.get("tags", [])
    node.category = template.get("_category", template.get("category", ""))
    node.input_docs = template.get("input_docs", [])
    node.output_docs = template.get("output_docs", [])

    # Cor customizada
    if "color" in template:
        color = template["color"]
        if isinstance(color, list) and len(color) == 3:
            node.custom_color = tuple(color)

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

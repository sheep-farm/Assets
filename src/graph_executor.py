"""
GraphExecutor - Execução de grafos de nós

Responsável pela execução de grafos em ordem topológica com paralelização por níveis.
Extraído de canvas.py para melhor separação de responsabilidades.
"""

import threading
import pickle
import base64
import time
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from gi.repository import GLib
from .node import NodeExecutionState
from .data_helpers import create_data_helpers, process_folder_output


class GraphExecutor:
    """
    Classe responsável pela execução de grafos de nós.

    Attributes:
        canvas: Referência ao canvas que contém os nós e conexões
    """

    def __init__(self, canvas):
        """
        Inicializa o executor de grafos.

        Args:
            canvas: Instância do AssetsCanvas que contém nodes e connections
        """
        self.canvas = canvas

    def execute_graph(self):
        """
        Executa o grafo completo em ordem topológica com paralelização por níveis.

        Returns:
            bool: True se execução foi bem sucedida, False caso contrário
        """
        if not self.canvas.nodes:
            print("⚠️  Nenhum nó para executar")
            return False

        # Limpar output_values e estado de erro de TODOS os nós antes de executar
        # Isso garante execução limpa sem resultados antigos
        for node in self.canvas.nodes:
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
        node_results = {}
        results_lock = threading.Lock()

        # Obter referência à janela para acessar output_panel
        window = self.canvas.get_root()

        # Obter output_panel do projeto atual (mais confiável)
        output_panel = None
        if hasattr(self.canvas, 'project_tab') and self.canvas.project_tab:
            output_panel = self.canvas.project_tab.output_panel
            print(f"✓ Usando output_panel do project_tab")
        elif hasattr(window, 'output_panel'):
            output_panel = window.output_panel
            print(f"✓ Usando output_panel da window")
        else:
            print(f"⚠️  Nenhum output_panel encontrado!")

        # Limpar outputs anteriores antes de executar
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
                        GLib.idle_add(self.canvas.queue_draw)

                        # Coletar inputs deste nó
                        with results_lock:
                            inputs = self._collect_node_inputs(node, node_results)

                        # Executar código do nó
                        outputs = self._execute_node_code(node, inputs)

                        # Marcar nó como COMPLETED
                        node.execution_state = NodeExecutionState.COMPLETED
                        GLib.idle_add(self.canvas.queue_draw)

                        # Armazenar resultados (thread-safe)
                        with results_lock:
                            node_results[node] = outputs

                        # RETORNAR outputs para processar na main thread
                        return (node, outputs, None)  # (node, outputs, error)

                    except Exception as e:
                        # Marcar nó como ERROR
                        node.execution_state = NodeExecutionState.ERROR
                        GLib.idle_add(self.canvas.queue_draw)
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
            traceback.print_exc()
            return False

    def _process_special_output(self, output, node, output_panel):
        """
        Processa outputs especiais e envia para o painel apropriado.
        Usa GLib.idle_add para garantir que está na main thread.

        Suporta metadados:
        - _table_name, _table_format (csv, parquet, xlsx)
        - _plot_name

        Args:
            output: Output do nó
            node: Nó que gerou o output
            output_panel: Painel de output
        """
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
                # Extrair nome customizado se fornecido
                plot_name = output.get("_plot_name", None)
                if plot_name:
                    title = f"{plot_name} ({node.title})"
                else:
                    title = f"Plot from: {node.title}"

                print(f"  → Processando plot output de '{node.title}' com título: {title}")
                GLib.idle_add(output_panel.add_plot, output["_plot"], title)
                return

            # Tabela (DataFrame)
            if "_table" in output:
                # Extrair metadados
                table_name = output.get("_table_name", None)
                table_format = output.get("_table_format", None)

                # Definir título da aba
                if table_name:
                    title = f"{table_name} ({node.title})"
                else:
                    title = f"Table from: {node.title}"

                print(f"  → Processando table output de '{node.title}' com título: {title}")

                # Adicionar ao output panel (sempre mostra)
                GLib.idle_add(output_panel.add_table, output["_table"], title)

                # Se formato foi especificado, salvar arquivo também
                if table_format:
                    self._save_table(output["_table"], table_name, table_format, node.title)

                return

            # Dados estruturados
            if "_data" in output:
                print(f"  → Processando data output de '{node.title}'")
                GLib.idle_add(output_panel.add_data, output["_data"], f"Data from: {node.title}")
                return

        # Output normal - não fazer nada (só passa para próximo nó)

    def _save_table(self, table, table_name, table_format, node_title):
        """
        Salva tabela em arquivo (CSV, Parquet ou XLSX).

        Args:
            table: DataFrame para salvar
            table_name: Nome customizado ou None
            table_format: 'csv', 'parquet' ou 'xlsx'
            node_title: Título do nó (fallback para nome)
        """
        try:
            import pandas as pd
            from pathlib import Path
            import re

            # Garantir que é DataFrame
            if not isinstance(table, pd.DataFrame):
                print(f"  ⚠️  _table não é DataFrame, não pode salvar como {table_format}")
                return

            # Criar diretório tables/ se não existir
            output_dir = Path("tables")
            output_dir.mkdir(exist_ok=True)

            # Sanitizar nome para arquivo seguro
            if table_name:
                safe_name = re.sub(r'[^0-9a-zA-Z_-]+', '_', str(table_name).strip())
            else:
                safe_name = re.sub(r'[^0-9a-zA-Z_-]+', '_', node_title.strip())

            if not safe_name:
                safe_name = "table"

            # Validar formato
            fmt = str(table_format).lower()
            if fmt not in ("csv", "parquet", "xlsx"):
                print(f"  ⚠️  Formato '{table_format}' inválido. Use: csv, parquet ou xlsx")
                fmt = "csv"

            # Caminho completo
            filename = output_dir / f"{safe_name}.{fmt}"

            # Salvar de acordo com o formato
            if fmt == "csv":
                table.to_csv(filename, index=False)
            elif fmt == "parquet":
                table.to_parquet(filename, index=False)
            elif fmt == "xlsx":
                table.to_excel(filename, index=False)

            print(f"  📁 Tabela salva ({fmt}): {filename}")

        except Exception as e:
            print(f"  ❌ Erro ao salvar tabela: {e}")
            import traceback
            traceback.print_exc()

    def _topological_sort(self):
        """
        Ordena os nós em ordem topológica (dependências primeiro).

        Returns:
            list: Lista de nós em ordem de execução, ou None se houver ciclos
        """
        # Construir grafo de dependências
        in_degree = {node: 0 for node in self.canvas.nodes}
        adjacency = {node: [] for node in self.canvas.nodes}

        for source_node, out_port, target_node, in_port in self.canvas.connections:
            adjacency[source_node].append(target_node)
            in_degree[target_node] += 1

        # Algoritmo de Kahn para ordenação topológica
        queue = [node for node in self.canvas.nodes if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Se não processou todos os nós, há ciclos
        if len(result) != len(self.canvas.nodes):
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
        for source_node, out_port, target_node, in_port in self.canvas.connections:
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
        active_nodes = [node for node in self.canvas.nodes if self._node_has_connections(node)]
        inactive_nodes = [node for node in self.canvas.nodes if not self._node_has_connections(node)]

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
        for source_node, out_port, target_node, in_port in self.canvas.connections:
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
        for source_node, out_port, target_node, in_port in self.canvas.connections:
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
        # Debug: verificar se venv foi passado corretamente
        if venv is None:
            print(f"❌ ERRO: venv é None para nó '{node.title}'")
            print(f"   project_tab.isolated_env = {getattr(self.canvas.project_tab, 'isolated_env', 'N/A') if hasattr(self.canvas, 'project_tab') else 'no project_tab'}")
            print(f"   project_tab.python_mode = {getattr(self.canvas.project_tab, 'python_mode', 'N/A') if hasattr(self.canvas, 'project_tab') else 'no project_tab'}")
            raise RuntimeError("System venv not configured. Please reopen the project or check Project Settings.")

        try:
            start_time = time.perf_counter()

            # Criar dicionário de nós para resolver referências de código
            nodes_dict = {n.id: n for n in self.canvas.nodes}

            # Obter código efetivo (resolve referência se necessário)
            effective_code = node.get_effective_code(nodes_dict)

            # Serializar inputs para passar ao subprocess
            inputs_b64 = base64.b64encode(pickle.dumps(inputs)).decode('ascii')

            # Obter project_dir para helpers
            project_dir = None
            if hasattr(self.canvas, 'project_tab') and self.canvas.project_tab.current_file:
                project_dir = Path(self.canvas.project_tab.current_file).parent

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
def _node_func(inputs):
{chr(10).join("    " + line for line in effective_code.splitlines())}

result = _node_func(inputs)

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
                    if hasattr(self.canvas, 'project_tab') and self.canvas.project_tab.current_file:
                        project_dir = Path(self.canvas.project_tab.current_file).parent

                    result = process_folder_output(result, node.title, project_dir)

                    return result

            # Se não encontrou output, erro
            raise RuntimeError("Nenhum resultado retornado")

        except Exception as e:
            print(f"❌ ERRO em '{node.title}' (system venv):")
            print(f"   {type(e).__name__}: {e}")
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
        # DETECTAR E EXECUTAR GROUPNODE
        from .group_node import GroupNode

        if isinstance(node, GroupNode):
            print(f"📦 Executando GroupNode: {node.title}")
            project_dir = self._get_project_directory()
            return node.execute_inner_graph(inputs, project_dir=project_dir)

        # Criar dicionário de nós para resolver referências de código
        nodes_dict = {n.id: n for n in self.canvas.nodes}

        # Obter código efetivo (resolve referência se necessário)
        effective_code = node.get_effective_code(nodes_dict)

        if not effective_code or effective_code.strip() == "":
            print(f"  ⚠️  Nó sem código, retornando inputs como outputs")
            return inputs

        # Verificar se deve usar system venv
        if hasattr(self.canvas, 'project_tab'):
            project = self.canvas.project_tab
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
            for line in effective_code.split('\n'):
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
            node.has_error = True
            node.error_message = str(e)
            node.execution_state = NodeExecutionState.ERROR

            # Imprimir erro detalhado
            print(f"❌ ERRO em '{node.title}':")
            print(f"   {type(e).__name__}: {e}")
            traceback.print_exc()

            # Redesenhar canvas para mostrar erro visualmente
            GLib.idle_add(self.canvas.queue_draw)

            return None

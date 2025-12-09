"""
export_to_code.py - Exporta grafo de nós para código Python executável

Converte um grafo visual em script Python mantendo:
- Execução em ordem topológica
- Paralelização por níveis (concorrência)
- Nós por referência (code_ref)
- Detecção automática de dependências
"""

import re
from pathlib import Path
from datetime import datetime


class CodeExporter:
    """Exporta grafo de nós para código Python executável"""

    # Imports Python comuns que podem aparecer no código
    COMMON_IMPORTS = {
        'pandas': 'pd',
        'numpy': 'np',
        'matplotlib.pyplot': 'plt',
        'seaborn': 'sns',
        'scipy': None,
        'sklearn': None,
        'requests': None,
        'json': None,
        'datetime': None,
        'pathlib': None,
        'os': None,
        'sys': None,
        're': None,
    }

    def __init__(self, canvas):
        """
        Inicializa o exportador

        Args:
            canvas: Instância do AssetsCanvas com nodes e connections
        """
        self.canvas = canvas
        # Mapear id -> node para resolver code_ref
        self.nodes_dict = {node.id: node for node in canvas.nodes}

    # ============================================================
    # API principal
    # ============================================================

    def export_to_file(self, filepath: str) -> bool:
        """
        Exporta grafo para arquivo Python

        Args:
            filepath: Caminho do arquivo .py de saída

        Returns:
            bool: True se exportado com sucesso
        """
        try:
            code = self._generate_code()

            path = Path(filepath)
            path.write_text(code, encoding='utf-8')

            print(f"✓ Graph exported to: {filepath}")
            return True

        except Exception as e:
            print(f"❌ Error exporting graph: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ============================================================
    # Geração de código
    # ============================================================

    def _generate_code(self) -> str:
        """Gera o código Python completo"""

        # 1. Ordenação topológica (para detectar ciclos)
        execution_order = self._topological_sort()
        if execution_order is None:
            raise ValueError("Graph contains cycles! Cannot export.")

        # 2. Agrupar por níveis de execução (para paralelização)
        levels = self._group_by_execution_level()

        # 3. Detectar dependências
        dependencies = self._detect_dependencies()

        # 4. Gerar partes do código
        parts = []

        # Header
        parts.append(self._generate_header(dependencies))

        # Imports
        parts.append(self._generate_imports(dependencies))

        # Node functions
        parts.append(self._generate_node_functions())

        # Execution engine
        parts.append(self._generate_execution_engine(levels))

        # Main
        parts.append(self._generate_main())

        return '\n\n'.join(parts)

    def _generate_header(self, dependencies):
        """Gera cabeçalho com informações e pip install"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Gerar comando pip install
        pip_packages = []
        for pkg in dependencies:
            # Remover submódulos (ex: matplotlib.pyplot -> matplotlib)
            base_pkg = pkg.split('.')[0]
            if base_pkg not in ['os', 'sys', 're', 'json', 'datetime', 'pathlib', 'threading', 'concurrent']:
                pip_packages.append(base_pkg)

        pip_cmd = ""
        if pip_packages:
            unique = sorted(set(pip_packages))
            pip_cmd = f"# pip install {' '.join(unique)}"

        header = f"""#!/usr/bin/env python3
\"\"\"Auto-generated from Assets visual graph

Generated: {timestamp}
Nodes: {len(self.canvas.nodes)}
Connections: {len(self.canvas.connections)}

This script maintains the parallel execution structure of the original graph.
Nodes in the same execution level can run concurrently using ThreadPoolExecutor.

Dependencies:
{pip_cmd}
\"\"\""""
        return header

    def _generate_imports(self, dependencies):
        """Gera imports necessários"""
        imports = [
            "import sys",
            "from concurrent.futures import ThreadPoolExecutor, as_completed",
            "from typing import Dict, Any, List, Callable",
        ]

        # Adicionar imports detectados
        for pkg in sorted(dependencies):
            alias = self.COMMON_IMPORTS.get(pkg)
            if alias:
                imports.append(f"import {pkg} as {alias}")
            else:
                imports.append(f"import {pkg}")

        return '\n'.join(imports)

    # ============================================================
    # Node functions
    # ============================================================

    def _generate_node_functions(self):
        """Gera funções para cada nó"""
        functions = [
            "# " + "=" * 70,
            "# Node Functions",
            "# " + "=" * 70,
        ]

        processed_nodes = set()

        for node in self.canvas.nodes:
            # Nó com code_ref: gera função do nó referenciado se ainda não gerada
            if getattr(node, "code_ref", None):
                if node.code_ref not in processed_nodes:
                    ref_node = self.nodes_dict.get(node.code_ref)
                    if ref_node is not None:
                        func_code = self._generate_node_function(ref_node)
                        functions.append(func_code)
                        processed_nodes.add(node.code_ref)

                # Este nó apenas chama a função do referenciado
                func_code = self._generate_reference_node_function(node)
                functions.append(func_code)

            else:
                func_code = self._generate_node_function(node)
                functions.append(func_code)
                processed_nodes.add(node.id)

        return '\n\n'.join(functions)

    def _generate_node_function(self, node):
        """Gera função para um nó específico"""
        func_name = f"node_{node.id.replace('-', '_')}"

        # Pega código efetivo (resolve referência se necessário)
        code = node.get_effective_code(self.nodes_dict)

        # Indentar código do usuário
        indented_code = '\n    '.join(code.split('\n'))

        # Função recebe apenas 'inputs' como lista (como no Assets GUI)
        params_str = "inputs=None"

        # Monta docstring básica
        doc_lines = [f'"""{getattr(node, "title", "Node")}']
        desc = getattr(node, "description", "")
        if desc:
            doc_lines.append(f"\n\n    {desc}")

        n_in = getattr(node, "num_inputs", 0)
        n_out = getattr(node, "num_outputs", 0)

        if n_in > 0:
            doc_lines.append("\n\n    Inputs:")
            for i in range(n_in):
                input_type = ""
                if hasattr(node, "input_types") and i < len(node.input_types):
                    input_type = node.input_types[i]
                else:
                    input_type = "any"
                doc_lines.append(f"\n        input_{i} ({input_type}) -> accessible as inputs[{i}]")

        if n_out > 0:
            doc_lines.append("\n\n    Outputs:")
            for i in range(n_out):
                output_type = ""
                if hasattr(node, "output_types") and i < len(node.output_types):
                    output_type = node.output_types[i]
                else:
                    output_type = "any"
                doc_lines.append(f"\n        output[{i}] ({output_type}) -> set as _output{i}")

        doc_lines.append('\n    """')
        doc = ''.join(doc_lines)

        # Corpo da função
        body_lines = [f"def {func_name}({params_str}):",
                      f"    {doc}",
                      f"    # Node ID: {node.id}"]

        body_lines.append("\n    # Code:")
        body_lines.append(f"    {indented_code}")

        # # Coleta padrão via _output0, _output1 etc (para nós que não usam return)
        # body_lines.append("\n    # Return outputs")
        # body_lines.append("    output_values = {}")
        # body_lines.append(f"    for i in range({n_out}):")
        # body_lines.append("        var_name = f\"_output{i}\"")
        # body_lines.append("        if var_name in locals():")
        # body_lines.append("            output_values[i] = locals()[var_name]")

        # # Especiais
        # body_lines.append("\n    # Collect special outputs (_console, _table, _plot)")
        # body_lines.append("    special_outputs = {}")
        # body_lines.append("    if '_console' in locals():")
        # body_lines.append("        special_outputs['console'] = locals()['_console']")
        # body_lines.append("    if '_table' in locals():")
        # body_lines.append("        special_outputs['table'] = locals()['_table']")
        # body_lines.append("    if '_plot' in locals():")
        # body_lines.append("        special_outputs['plot'] = locals()['_plot']")

        # body_lines.append("    if special_outputs:")
        # body_lines.append("        output_values['__special__'] = special_outputs")

        # body_lines.append("\n    return output_values")

        return '\n'.join(body_lines)

    def _generate_reference_node_function(self, node):
        """Gera função para nó que referencia outro nó"""
        func_name = f"node_{node.id.replace('-', '_')}"
        ref_func_name = f"node_{node.code_ref.replace('-', '_')}"

        ref_node = self.nodes_dict.get(node.code_ref)
        ref_title = ref_node.title if ref_node is not None else "Unknown"

        doc_lines = [f'"""{getattr(node, "title", "Reference Node")} (References: {ref_title})']
        doc_lines.append("\n\n    This node calls the code from another node.")
        doc_lines.append('\n    """')
        doc = ''.join(doc_lines)

        lines = [
            f"def {func_name}(inputs=None):",
            f"    {doc}",
            f"    # This is a reference node - calls {ref_func_name}",
            f"    return {ref_func_name}(inputs)",
        ]
        return '\n'.join(lines)

    # ============================================================
    # Execution Engine
    # ============================================================

    def _generate_execution_engine(self, levels):
        """Gera código de execução paralela por níveis"""

        # Mapear níveis para funções pelo nome
        level_functions = []
        for level_nodes in levels:
            funcs = []
            for node in level_nodes:
                func_name = f"node_{node.id.replace('-', '_')}"
                funcs.append(func_name)
            level_functions.append(funcs)

        # Mapa de conexões como literal Python
        connections_literal = self._generate_connections_map()
        levels_literal = repr(level_functions)

        template = '''# ======================================================================
# Execution Engine
# ======================================================================

# Helpers: load_data e save_data
def load_data(filename):
    """Carrega arquivo do projeto (auto-detecta formato)"""
    from pathlib import Path
    import pandas as pd
    import json

    path = Path(filename).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / filename
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
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
        raise ValueError(f"Formato não suportado: {suffix}")

def save_data(data, filename, **kwargs):
    """Salva dados no projeto (auto-detecta formato)"""
    from pathlib import Path
    import pandas as pd
    import numpy as np
    import json

    path = Path(filename).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / filename
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
            raise ValueError(f"Formato não suportado para DataFrame: {suffix}")
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
            raise ValueError(f"Formato não suportado para array: {suffix}")
    else:
        raise TypeError(f"Tipo de dado não suportado: {type(data)}")
    return path

# Aliases
load = load_data
save = save_data


def _normalize_node_result(result):
    \"\"\"Normaliza o retorno de um nó para o formato interno esperado.

    Casos tratados:

    - None -> {}
    - valor simples -> {0: valor}
    - list -> {0: lista_completa} (lista é tratada como valor único)
    - tuple -> índices de saída 0,1,... para cada elemento (desempacota a tupla);
      dicts com '_console'/'_table'/'_plot' vão para __special__
    - dict já no formato interno (com '__special__' ou chaves inteiras) -> retorna como está
    - dict com chaves '_console'/'_table'/'_plot' (e meta) -> vira {'__special__': ...}

    Meta suportada (opcional):
    - _plot_name
    - _table_name
    - _table_format
    \"\"\"
    # Nada retornado
    if result is None:
        return {}

    # Valor simples (não-dict, não-tuple): vira saída padrão na porta 0
    # Nota: listas são tratadas como valor simples (não desempacotadas)
    if not isinstance(result, (dict, tuple)):
        return {0: result}

    # Se já é dict, pode ser formato interno ou special puro
    if isinstance(result, dict):
        # Caso já esteja no formato interno (gerado pelo próprio boilerplate)
        if "__special__" in result or any(
            isinstance(k, int) or (isinstance(k, str) and k.isdigit())
            for k in result.keys()
        ):
            return result

        # Se for dict com chaves especiais explícitas
        special_main_keys = {'_console', '_table', '_plot'}
        meta_keys = {'_table_name', '_table_format', '_plot_name'}
        special_keys = special_main_keys | meta_keys

        if any(k in special_keys for k in result.keys()):
            special = {}

            for k, v in result.items():
                # specials principais
                if k == '_console':
                    if 'console' in special:
                        if isinstance(special['console'], list):
                            special['console'].append(v)
                        else:
                            special['console'] = [special['console'], v]
                    else:
                        special['console'] = v

                elif k == '_table':
                    if 'table' in special:
                        if isinstance(special['table'], list):
                            special['table'].append(v)
                        else:
                            special['table'] = [special['table'], v]
                    else:
                        special['table'] = v

                elif k == '_plot':
                    if 'plot' in special:
                        if isinstance(special['plot'], list):
                            special['plot'].append(v)
                        else:
                            special['plot'] = [special['plot'], v]
                    else:
                        special['plot'] = v

                # meta
                elif k == '_table_name':
                    if 'table_names' in special:
                        if isinstance(special['table_names'], list):
                            special['table_names'].append(v)
                        else:
                            special['table_names'] = [special['table_names'], v]
                    else:
                        special['table_names'] = v

                elif k == '_table_format':
                    if 'table_formats' in special:
                        if isinstance(special['table_formats'], list):
                            special['table_formats'].append(v)
                        else:
                            special['table_formats'] = [special['table_formats'], v]
                    else:
                        special['table_formats'] = v

                elif k == '_plot_name':
                    if 'plot_names' in special:
                        if isinstance(special['plot_names'], list):
                            special['plot_names'].append(v)
                        else:
                            special['plot_names'] = [special['plot_names'], v]
                    else:
                        special['plot_names'] = v

            return {'__special__': special}

        # Dict genérico sem formato conhecido: trata como valor simples
        return {0: result}

    # Lista: trata como valor único (não desempacota)
    if isinstance(result, list):
        return {0: result}

    # Tupla: desempacota cada elemento em uma porta diferente
    outputs = {}
    for idx, elem in enumerate(result):
        outputs[idx] = elem
    return outputs


def execute_graph(verbose=False):
    \"\"\"Executa o grafo em ordem topológica, com paralelização por níveis.

    Args:
        verbose: Se True, imprime progresso da execução.

    Returns:
        Dict[str, Any]: Resultados de todos os nós.
    \"\"\"
    if verbose:
        print("=" * 70)
        print("GRAPH EXECUTION STARTED")
        print("=" * 70)
        print()

    # Store results of each node (key = node_id)
    results = {}

    # Connection map: (source_node_id, output_port) -> [(target_node_id, input_port)]
    connections = __CONNECTIONS__

    # Execute each level in order (levels are sequential, nodes within level are parallel)
    levels = __LEVELS__

    for level_idx, level_funcs in enumerate(levels):
        if verbose:
            print(f"⚡ Executing level {level_idx} ({len(level_funcs)} nodes in parallel)...")

        # Executa todos os nós deste nível
        if len(level_funcs) == 1:
            # Single node - sem ThreadPool
            func_name = level_funcs[0]
            func = globals()[func_name]
            node_id = func_name.replace('node_', '').replace('_', '-')
            inputs = _collect_node_inputs(node_id, connections, results, verbose)

            try:
                raw_result = func(inputs)
                result = _normalize_node_result(raw_result)
                results[node_id] = result
                if verbose:
                    print(f"  ✓ {func_name}")
            except Exception as e:
                print(f"  ❌ {func_name}: {e}")
                import traceback
                traceback.print_exc()
                results[node_id] = {}
        else:
            # Múltiplos nós - usar ThreadPoolExecutor
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=len(level_funcs)) as executor:
                futures = {}

                for func_name in level_funcs:
                    func = globals()[func_name]
                    node_id = func_name.replace('node_', '').replace('_', '-')
                    inputs = _collect_node_inputs(node_id, connections, results, verbose)
                    future = executor.submit(func, inputs)
                    futures[future] = (func_name, node_id)

                for future in as_completed(futures):
                    func_name, node_id = futures[future]
                    try:
                        raw_result = future.result()
                        result = _normalize_node_result(raw_result)
                        results[node_id] = result
                        if verbose:
                            print(f"  ✓ {func_name}")
                    except Exception as e:
                        print(f"  ❌ {func_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        results[node_id] = {}

        if verbose:
            print()

    if verbose:
        print("=" * 70)
        print("✅ GRAPH EXECUTION COMPLETED")
        print("=" * 70)

    return results


def _collect_node_inputs(node_id: str, connections: dict, results: dict, verbose: bool = False) -> list:
    """Coleta inputs para um nó a partir de resultados anteriores.

    Retorna uma lista onde cada posição corresponde a uma porta de input.
    Se um input não está conectado, fica como None.
    """
    # Primeiro, descobrir quantas portas de input este nó tem
    max_port = -1
    for (source_id, out_port), targets in connections.items():
        for (target_id, in_port) in targets:
            if target_id == node_id:
                max_port = max(max_port, in_port)

    # Se não tem inputs conectados, retorna None
    if max_port == -1:
        return None

    # Criar lista com tamanho adequado, inicializada com None
    inputs = [None] * (max_port + 1)

    for (source_id, out_port), targets in connections.items():
        for (target_id, in_port) in targets:
            if target_id == node_id:
                if source_id in results:
                    source_outputs = results[source_id]
                    if verbose:
                        print(f"    Collecting input port {in_port} from {source_id}[{out_port}]")
                        if isinstance(source_outputs, dict):
                            print(f"    Available outputs: {list(source_outputs.keys())}")
                        else:
                            print("    Source outputs not a dict")

                    if isinstance(source_outputs, dict) and out_port in source_outputs:
                        value = source_outputs[out_port]
                        inputs[in_port] = value
                        if verbose:
                            preview = str(value)
                            if len(preview) > 80:
                                preview = preview[:77] + "..."
                            print(f"    ✓ Set inputs[{in_port}] = {preview}")
                    else:
                        if verbose:
                            print(f"    ⚠️  Output port {out_port} not found in {source_id}")
                else:
                    if verbose:
                        print(f"    ⚠️  Source node {source_id} not in results")

    return inputs
'''
        code = template.replace("__CONNECTIONS__", connections_literal).replace("__LEVELS__", levels_literal)
        return code

    # ============================================================
    # Conexões
    # ============================================================

    def _generate_connections_map(self):
        """Gera mapa de conexões para o código.

        Formato: {(source_id, out_port): [(target_id, in_port), ...]}
        """
        conn_map = {}

        for conn in self.canvas.connections:
            source_node, out_port, target_node, in_port = conn
            key = (source_node.id, out_port)
            if key not in conn_map:
                conn_map[key] = []
            conn_map[key].append((target_node.id, in_port))

        # Transformar em literal Python de dict
        lines = ["{"]
        for (source_id, out_port), targets in conn_map.items():
            targets_str = ", ".join([f"('{t[0]}', {t[1]})" for t in targets])
            lines.append(f"    ('{source_id}', {out_port}): [{targets_str}],")
        lines.append("}")
        return "\n".join(lines)

    # ============================================================
    # Main e processamento de saídas especiais
    # ============================================================

    def _generate_main(self):
        """Gera função main e process_special_outputs"""
        return '''# ======================================================================
# Main Entry Point
# ======================================================================

def process_special_outputs(results, verbose=False):
    \"\"\"Process and save special outputs: _console, _table, _plot

    - _console → imprime no terminal
    - _table   → salva CSV/Parquet/XLSX
    - _plot    → salva PNG

    Meta suportada (opcional nos nós):
    - _table_name
    - _table_format
    - _plot_name
    \"\"\"

    import re
    from pathlib import Path

    def _sanitize_name(name, default):
        \"\"\"Garante nome seguro para arquivo.\"\"\"
        if not isinstance(name, str) or not name.strip():
            return default
        slug = re.sub(r'[^0-9a-zA-Z_-]+', '_', name.strip())
        return slug or default

    for node_id, outputs in results.items():
        if not outputs:
            continue

        if '__special__' not in outputs:
            continue

        special = outputs['__special__']

        # ---------------------------------------------------------
        # _console
        # ---------------------------------------------------------
        if 'console' in special:
            vals = special['console']
            if not isinstance(vals, list):
                vals = [vals]

            if verbose:
                print(f"\\n💬 Console output from {node_id}:")
                print("-" * 70)

            for msg in vals:
                print(msg)

            if verbose:
                print("-" * 70)

        # ---------------------------------------------------------
        # _table → salva CSV/parquet/xlsx
        # ---------------------------------------------------------
        if 'table' in special:
            import pandas as pd

            tables = special['table']
            if not isinstance(tables, list):
                tables = [tables]

            table_names = special.get('table_names')
            table_formats = special.get('table_formats')

            output_dir = Path("tables")
            output_dir.mkdir(exist_ok=True)

            for i, tbl in enumerate(tables):
                # nome base
                if isinstance(table_names, list) and i < len(table_names):
                    base_name = _sanitize_name(table_names[i], f"table_{node_id}_{i}")
                elif isinstance(table_names, str):
                    base_name = _sanitize_name(table_names, f"table_{node_id}_{i}")
                else:
                    base_name = f"table_{node_id}_{i}"

                # formato
                if isinstance(table_formats, list) and i < len(table_formats):
                    fmt = str(table_formats[i]).lower()
                elif isinstance(table_formats, str):
                    fmt = table_formats.lower()
                else:
                    fmt = "csv"

                if fmt not in ("csv", "parquet", "xlsx"):
                    fmt = "csv"

                filename = output_dir / f"{base_name}.{fmt}"

                try:
                    if isinstance(tbl, pd.DataFrame):
                        if fmt == "csv":
                            tbl.to_csv(filename, index=False)
                        elif fmt == "parquet":
                            tbl.to_parquet(filename, index=False)
                        elif fmt == "xlsx":
                            tbl.to_excel(filename, index=False)
                    else:
                        # Fallback: salva texto simples
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(str(tbl))

                    if verbose:
                        print(f"📁 Saved table ({fmt}): {filename}")

                except Exception as e:
                    print(f"⚠️ Error saving table for node {node_id}: {e}")

        # ---------------------------------------------------------
        # _plot → salva PNG
        # ---------------------------------------------------------
        if 'plot' in special:
            import matplotlib
            import matplotlib.pyplot as plt
            import matplotlib.figure

            figs = special['plot']
            if not isinstance(figs, list):
                figs = [figs]

            plot_names = special.get('plot_names')

            output_dir = Path("plots")
            output_dir.mkdir(exist_ok=True)

            for i, fig in enumerate(figs):
                # nome base
                if isinstance(plot_names, list) and i < len(plot_names):
                    base_name = _sanitize_name(plot_names[i], f"plot_{node_id}_{i}")
                elif isinstance(plot_names, str):
                    base_name = _sanitize_name(plot_names, f"plot_{node_id}_{i}")
                else:
                    base_name = f"plot_{node_id}_{i}"

                filename = output_dir / f"{base_name}.png"

                try:
                    if isinstance(fig, matplotlib.figure.Figure):
                        fig.savefig(filename, dpi=150, bbox_inches='tight')
                    else:
                        plt.savefig(filename, dpi=150, bbox_inches='tight')

                    if verbose:
                        print(f"📁 Saved plot: {filename}")

                except Exception as e:
                    print(f"⚠️ Error saving plot for node {node_id}: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Execute exported graph from Assets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=\"\"\"
Examples:
  python3 %(prog)s              # Run quietly
  python3 %(prog)s -v           # Run with verbose output
  python3 %(prog)s --verbose    # Run with verbose output
        \"\"\"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output (shows execution progress)'
    )

    args = parser.parse_args()

    # Execute graph
    results = execute_graph(verbose=args.verbose)

    # Process and save special outputs
    process_special_outputs(results, verbose=args.verbose)

    # Show summary if verbose
    if args.verbose:
        print("\\n" + "=" * 70)
        print("📊 EXECUTION SUMMARY")
        print("=" * 70)
        total_nodes = len(results)
        total_outputs = sum(len(outputs) for outputs in results.values())
        print(f"Total nodes executed: {total_nodes}")
        print(f"Total outputs generated: {total_outputs}")
        print("=" * 70)
'''

    # ============================================================
    # Detecção de dependências
    # ============================================================

    def _detect_dependencies(self):
        """Detecta dependências Python no código dos nós"""
        dependencies = set()

        for node in self.canvas.nodes:
            code = node.get_effective_code(self.nodes_dict)

            # imports explícitos
            import_pattern = r'import\\s+([\\w.]+)(?:\\s+as\\s+\\w+)?'
            from_pattern = r'from\\s+([\\w.]+)\\s+import'

            for match in re.finditer(import_pattern, code):
                pkg = match.group(1)
                dependencies.add(pkg)

            for match in re.finditer(from_pattern, code):
                pkg = match.group(1)
                dependencies.add(pkg)

            # uso implícito de libs comuns
            for pkg, alias in self.COMMON_IMPORTS.items():
                if alias:
                    if f"{alias}." in code:
                        dependencies.add(pkg)
                else:
                    base_pkg = pkg.split('.')[0]
                    if f"{base_pkg}." in code:
                        dependencies.add(pkg)

        return dependencies

    # ============================================================
    # Utilitários de grafo
    # ============================================================

    def _get_node_inputs_info(self, node):
        """Obtém informações sobre inputs de um nó"""
        inputs = []
        for conn in self.canvas.connections:
            source_node, out_port, target_node, in_port = conn
            if target_node.id == node.id:
                inputs.append({
                    'port': in_port,
                    'source': source_node.title,
                    'source_port': out_port,
                })
        return inputs

    def _topological_sort(self):
        """Ordenação topológica dos nós (detecta ciclos)"""
        in_degree = {node: 0 for node in self.canvas.nodes}

        for conn in self.canvas.connections:
            source_node, _, target_node, _ = conn
            in_degree[target_node] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for conn in self.canvas.connections:
                source_node, _, target_node, _ = conn
                if source_node == node:
                    in_degree[target_node] -= 1
                    if in_degree[target_node] == 0:
                        queue.append(target_node)

        if len(result) != len(self.canvas.nodes):
            return None  # ciclo detectado

        return result

    def _group_by_execution_level(self):
        """Agrupa nós por nível de execução (para paralelização)"""
        in_degree = {node: 0 for node in self.canvas.nodes}

        for conn in self.canvas.connections:
            source_node, _, target_node, _ = conn
            in_degree[target_node] += 1

        levels = []
        remaining = set(self.canvas.nodes)

        while remaining:
            current_level = [node for node in remaining if in_degree[node] == 0]

            if not current_level:
                break

            levels.append(current_level)
            remaining -= set(current_level)

            for node in current_level:
                for conn in self.canvas.connections:
                    source_node, _, target_node, _ = conn
                    if source_node == node and target_node in remaining:
                        in_degree[target_node] -= 1

        return levels




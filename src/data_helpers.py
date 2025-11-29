"""
data_helpers.py - Funções helper para carregar/salvar dados nos nodes
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np


def create_data_helpers(project_dir):
    """
    Cria funções helper configuradas para um projeto específico.

    Args:
        project_dir: Path do diretório do projeto

    Returns:
        dict: Dicionário com funções helper prontas para uso
    """
    project_dir = Path(project_dir) if project_dir else Path.home() / "Documents"

    def load_data(filename):
        """
        Carrega arquivo do diretório do projeto (auto-detecta formato).
        Aceita paths absolutos, relativos ou com ~.

        Args:
            filename: Nome do arquivo ou path completo
                     - "dados.csv" → busca em project_dir
                     - "~/GitHub/data.csv" → path absoluto (expande ~)
                     - "/home/user/file.csv" → path absoluto

        Returns:
            DataFrame ou dict dependendo do formato

        Examples:
            >>> df = load_data("vendas.csv")  # Relativo ao projeto
            >>> df = load_data("~/Downloads/dados.csv")  # Path absoluto
            >>> data = load_data("/tmp/config.json")  # Path absoluto
        """
        # Converter para Path e expandir ~ se necessário
        path = Path(filename).expanduser()

        # Se não for absoluto, usa project_dir como base
        if not path.is_absolute():
            path = project_dir / filename

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
            # Tentar converter para DataFrame se for lista de dicts
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
        """
        Salva dados no diretório do projeto (auto-detecta formato pela extensão).
        Aceita paths absolutos, relativos ou com ~.

        Args:
            data: Dados a salvar (DataFrame, dict, Figure, etc)
            filename: Nome do arquivo de destino ou path completo
                     - "resultado.csv" → salva em project_dir
                     - "~/Downloads/output.csv" → path absoluto (expande ~)
                     - "/tmp/dados.json" → path absoluto
            **kwargs: Argumentos extras para funções de save (index=False, etc)

        Examples:
            >>> save_data(df, "resultado.csv")  # Relativo ao projeto
            >>> save_data(fig, "~/Desktop/grafico.png")  # Path absoluto
            >>> save_data({"resultado": 123}, "/tmp/metricas.json")  # Path absoluto
        """
        # Converter para Path e expandir ~ se necessário
        path = Path(filename).expanduser()

        # Se não for absoluto, usa project_dir como base
        if not path.is_absolute():
            path = project_dir / filename

        path.parent.mkdir(parents=True, exist_ok=True)

        suffix = path.suffix.lower()

        # DataFrame
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

        # Matplotlib/Seaborn Figure
        elif hasattr(data, 'savefig'):  # Matplotlib Figure
            data.savefig(path, dpi=kwargs.get('dpi', 150), bbox_inches='tight')

        # Dict ou JSON-serializable
        elif isinstance(data, (dict, list)):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

        # Texto
        elif isinstance(data, str):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data)

        # NumPy array
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

    return {
        'load_data': load_data,
        'save_data': save_data,
        'load': load,
        'save': save,
        'project_dir': project_dir,
    }


def process_folder_output(result, node_title, project_dir):
    """
    Processa outputs com convenção {"_folder": data} para auto-save.

    Args:
        result: Resultado do node (pode ser tupla com dicts)
        node_title: Título do node (para nome do arquivo)
        project_dir: Diretório do projeto

    Returns:
        tuple: Resultado processado (paths dos arquivos salvos substituem _folder)
    """
    if not isinstance(result, tuple):
        result = (result,)

    project_dir = Path(project_dir) if project_dir else Path.home() / "Documents"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    processed = []

    for item in result:
        if isinstance(item, dict) and "_folder" in item:
            print(f"📁 _folder detectado! Processando auto-save...")
            folder_data = item["_folder"]

            # Caso 1: Múltiplos arquivos - {"file1.csv": data1, "file2.png": fig}
            if isinstance(folder_data, dict):
                print(f"  📂 Múltiplos arquivos: {list(folder_data.keys())}")
                saved_paths = {}
                for filename, data in folder_data.items():
                    try:
                        print(f"  💾 Salvando {filename}...")
                        path = _save_single_file(data, filename, project_dir)
                        saved_paths[filename] = str(path)
                        print(f"  ✅ Salvo: {path}")
                    except Exception as e:
                        print(f"  ❌ Erro ao salvar {filename}: {e}")
                        import traceback
                        traceback.print_exc()
                        saved_paths[filename] = f"ERROR: {e}"

                processed.append(saved_paths)

            # Caso 2: Arquivo único - auto-gera nome
            else:
                print(f"  📄 Arquivo único (tipo: {type(folder_data).__name__})")
                filename = _generate_filename(folder_data, node_title, timestamp)
                print(f"  💾 Salvando como: {filename}")
                try:
                    path = _save_single_file(folder_data, filename, project_dir)
                    processed.append(str(path))
                    print(f"  ✅ Salvo: {path}")
                except Exception as e:
                    print(f"  ❌ Erro ao salvar: {e}")
                    import traceback
                    traceback.print_exc()
                    processed.append(f"ERROR: {e}")
        else:
            processed.append(item)

    return tuple(processed)


def _save_single_file(data, filename, project_dir):
    """Salva um único arquivo detectando o tipo automaticamente."""
    # Converter para Path e expandir ~ se necessário
    path = Path(filename).expanduser()

    # Se não for absoluto, usar project_dir como base
    if not path.is_absolute():
        path = project_dir / filename

    path.parent.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()

    # DataFrame
    if isinstance(data, pd.DataFrame):
        if suffix == '.csv' or not suffix:
            path = path.with_suffix('.csv')
            data.to_csv(path, index=False)
        elif suffix in ['.xlsx', '.xls']:
            data.to_excel(path, index=False)
        elif suffix == '.parquet':
            data.to_parquet(path)
        else:
            data.to_csv(path.with_suffix('.csv'), index=False)

    # Matplotlib Figure
    elif hasattr(data, 'savefig'):
        if suffix in ['.png', '.jpg', '.jpeg', '.svg', '.pdf'] or not suffix:
            if not suffix:
                path = path.with_suffix('.png')
            data.savefig(path, dpi=150, bbox_inches='tight')
        else:
            data.savefig(path, dpi=150, bbox_inches='tight')

    # Dict/List (JSON)
    elif isinstance(data, (dict, list)):
        if suffix == '.json' or not suffix:
            path = path.with_suffix('.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    # String
    elif isinstance(data, str):
        if not suffix:
            path = path.with_suffix('.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)

    # NumPy array
    elif isinstance(data, np.ndarray):
        if suffix == '.npy' or not suffix:
            path = path.with_suffix('.npy')
            np.save(path, data)
        elif suffix == '.csv':
            pd.DataFrame(data).to_csv(path, index=False, header=False)

    else:
        raise TypeError(f"Tipo não suportado para auto-save: {type(data)}")

    print(f"✅ Arquivo salvo: {path.name}")
    return path


def _generate_filename(data, node_title, timestamp):
    """Gera nome de arquivo baseado no tipo de dados."""
    # Sanitizar título do node
    safe_title = "".join(c for c in node_title if c.isalnum() or c in (' ', '_', '-'))
    safe_title = safe_title.replace(' ', '_')[:30]

    # Determinar extensão pelo tipo
    if isinstance(data, pd.DataFrame):
        ext = '.csv'
    elif hasattr(data, 'savefig'):
        ext = '.png'
    elif isinstance(data, (dict, list)):
        ext = '.json'
    elif isinstance(data, np.ndarray):
        ext = '.npy'
    else:
        ext = '.txt'

    return f"{safe_title}_{timestamp}{ext}"

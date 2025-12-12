# 🚀 Export to Code - Funcionalidade Completa

## 📋 O que faz

A funcionalidade **Export to Code** converte seu grafo visual de nós em um arquivo Python executável standalone, mantendo:

✅ **Execução em ordem topológica** (sem ciclos)
✅ **Paralelização por níveis** (ThreadPoolExecutor)
✅ **Nós por referência** (code_ref)
✅ **Detecção automática de dependências**
✅ **Comentários pip install no cabeçalho**

---

## 🎮 Como Usar

### Opção 1: Menu Principal (Recomendado)

1. Abra seu projeto no Assets
2. **Menu → File → Export to Python** (ou pressione **Ctrl+Shift+E**)
3. Escolha o nome e local do arquivo `.py`
4. Pronto! Arquivo exportado com sucesso

### Opção 2: Via Código Python

```python
from export_to_code import CodeExporter

# Seu canvas com nós
exporter = CodeExporter(canvas)
exporter.export_to_file("my_graph.py")
```

---

## 📄 Exemplo de Arquivo Exportado

### Input: Grafo Visual

```
[Fetch Data] → [Process] → [Visualize]
      ↓
  [Save CSV]
```

### Output: Python Executável

```python
#!/usr/bin/env python3
"""
Auto-generated from Assets visual graph
Generated: 2025-12-08 11:30:45
Nodes: 4
Connections: 4

Dependencies:
# pip install pandas matplotlib
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Callable
import pandas as pd
import matplotlib.pyplot as plt

# ======================================================================
# Node Functions
# ======================================================================

def node_abc123(...):
    """Fetch Data

    Outputs:
        output[0] (dataframe)
    """
    # Node ID: abc-123-def

    # Code:
    import pandas as pd
    _output0 = pd.read_csv("data.csv")

    # Return outputs
    output_values = {}
    for i in range(1):
        var_name = f"_output{i}"
        if var_name in locals():
            output_values[i] = locals()[var_name]

    return output_values

def node_def456(input_0=None):
    """Process

    Inputs:
        input_0 (dataframe)

    Outputs:
        output[0] (dataframe)
    """
    # Node ID: def-456-ghi

    # Code:
    df = input_0
    _output0 = df.dropna()

    # Return outputs
    ...

# ======================================================================
# Execution Engine
# ======================================================================

def execute_graph():
    """
    Executes the graph in topological order with parallel execution per level.
    """
    print("="*70)
    print("GRAPH EXECUTION STARTED")
    print("="*70)
    print(f"Total levels: 2")
    print()

    results = {}

    # Connection map
    connections = {
        ('abc-123-def', 0): [('def-456-ghi', 0), ('xyz-789-abc', 0)],
        ('def-456-ghi', 0): [('mno-012-pqr', 0)],
    }

    # Execute each level in order
    levels = [
        ['node_abc123'],                      # Level 0 (1 node)
        ['node_def456', 'node_xyz789'],       # Level 1 (2 nodes in parallel)
        ['node_mno012'],                      # Level 2 (1 node)
    ]

    for level_idx, level_funcs in enumerate(levels):
        print(f"⚡ Executing level {level_idx} ({len(level_funcs)} nodes in parallel)...")

        # Multiple nodes - use ThreadPool for concurrency
        with ThreadPoolExecutor(max_workers=len(level_funcs)) as executor:
            futures = {}

            for func_name in level_funcs:
                func = globals()[func_name]
                node_id = func_name.replace('node_', '').replace('_', '-')
                inputs = _collect_node_inputs(node_id, connections, results)
                future = executor.submit(func, **inputs)
                futures[future] = (func_name, node_id)

            # Collect results as they complete
            for future in as_completed(futures):
                func_name, node_id = futures[future]
                try:
                    result = future.result()
                    results[node_id] = result
                    print(f"  ✓ {func_name}")
                except Exception as e:
                    print(f"  ❌ {func_name}: {e}")
                    results[node_id] = {}

    print("="*70)
    print("✅ GRAPH EXECUTION COMPLETED")
    print("="*70)

    return results


def _collect_node_inputs(node_id, connections, results):
    """Collects inputs for a node from previous results"""
    inputs = {}

    for (source_id, out_port), targets in connections.items():
        for (target_id, in_port) in targets:
            if target_id == node_id:
                if source_id in results:
                    source_outputs = results[source_id]
                    if out_port in source_outputs:
                        inputs[f"input_{in_port}"] = source_outputs[out_port]

    return inputs


# ======================================================================
# Main Entry Point
# ======================================================================

if __name__ == "__main__":
    results = execute_graph()

    print("\nFinal Results:")
    for node_id, outputs in results.items():
        if outputs:
            print(f"  {node_id}: {len(outputs)} outputs")
```

---

## 🔑 Características Principais

### 1. **Nós por Referência**

Se você tem nós que referenciam o código de outros nós (via `code_ref`):

```python
def node_abc123():
    """Original Node"""
    # código original
    return outputs

def node_xyz789(input_0=None):
    """Reference Node (References: Original Node)

    This node calls the code from node: Original Node
    """
    # This is a reference node - calls node_abc123
    return node_abc123(input_0)
```

O exportador detecta e cria chamadas de função apropriadas!

### 2. **Paralelização por Níveis**

Nós no mesmo nível de execução rodam **em paralelo** usando `ThreadPoolExecutor`:

```python
# Level 0: 1 node (sequential)
[Fetch Data]

# Level 1: 3 nodes (PARALLEL)
[Process A] | [Process B] | [Process C]  ← Executam simultaneamente!

# Level 2: 1 node (sequential)
[Merge Results]
```

### 3. **Detecção Automática de Dependências**

O exportador detecta imports no código dos nós:

```python
# Código do nó
import pandas as pd
df = pd.read_csv("data.csv")
```

**Resultado no cabeçalho:**
```python
# pip install pandas
```

Bibliotecas da stdlib (os, sys, json, etc.) são detectadas mas **não** incluídas no pip install.

### 4. **Mapa de Conexões**

Todas as conexões entre nós são preservadas:

```python
connections = {
    ('source-node-id', output_port): [
        ('target-node-id-1', input_port),
        ('target-node-id-2', input_port),
    ],
}
```

Isso garante que os dados fluam corretamente entre os nós!

---

## 🧪 Teste Completo

### 1. Criar Grafo de Teste

No Assets, crie:

```
[Node A: Gerar Dados]
    _output0 = list(range(10))

[Node B: Processar] (input_0)
    _output0 = [x * 2 for x in input_0]

[Node C: Imprimir] (input_0)
    print(f"Resultado: {input_0}")
```

Conecte: `A → B → C`

### 2. Exportar

**Ctrl+Shift+E** → Salve como `test_graph.py`

### 3. Executar

```bash
python3 test_graph.py
```

**Saída esperada:**
```
======================================================================
GRAPH EXECUTION STARTED
======================================================================
Total levels: 3

⚡ Executing level 0 (1 nodes in parallel)...
  ✓ node_abc123

⚡ Executing level 1 (1 nodes in parallel)...
  ✓ node_def456

⚡ Executing level 2 (1 nodes in parallel)...
Resultado: [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
  ✓ node_ghi789

======================================================================
✅ GRAPH EXECUTION COMPLETED
======================================================================
```

---

## 🎯 Use Cases

### 1. **Deploy de Produção**

Exporte seu grafo visual e rode em servidores sem o Assets instalado:

```bash
# No servidor
pip install -r requirements.txt  # baseado no header
python3 exported_graph.py
```

### 2. **CI/CD Pipelines**

Use o script exportado em pipelines automatizados:

```yaml
# .github/workflows/data-pipeline.yml
- name: Run data pipeline
  run: python3 exported_graph.py
```

### 3. **Versionamento Git**

Versione o código exportado junto com o `.assets`:

```
project/
  ├── analysis.assets         # Grafo visual
  ├── analysis_exported.py    # Código exportado
  └── README.md
```

### 4. **Debugging Avançado**

Exporte para Python e adicione breakpoints/logs específicos:

```python
def node_abc123():
    import pdb; pdb.set_trace()  # Debug aqui
    # código do nó
```

### 5. **Performance Profiling**

Profile o código exportado:

```bash
python3 -m cProfile -o profile.stats exported_graph.py
```

---

## ⚙️ Configuração Avançada

### Personalizar Detecção de Dependências

Edite `export_to_code.py:42`:

```python
COMMON_IMPORTS = {
    'pandas': 'pd',
    'numpy': 'np',
    'your_custom_lib': 'custom',  # Adicione aqui
}
```

### Modificar Template do Código

Edite os métodos `_generate_*()` em `CodeExporter`:

- `_generate_header()`: Cabeçalho e pip install
- `_generate_node_functions()`: Funções dos nós
- `_generate_execution_engine()`: Engine de execução
- `_generate_main()`: Função main

---

## 🐛 Troubleshooting

### Problema: "Graph contains cycles!"

**Causa:** Seu grafo tem dependências circulares (A → B → A).

**Solução:** Remova o ciclo no grafo visual antes de exportar.

### Problema: Dependência não detectada

**Causa:** Import não explícito no código do nó.

**Solução:** Adicione `import library` no código do nó, ou adicione à `COMMON_IMPORTS`.

### Problema: Código exportado não executa

**Causa:** Variáveis `_output0`, `_output1`, etc. não definidas no código do nó.

**Solução:** Certifique-se que cada nó define suas saídas corretamente:
```python
_output0 = resultado  # Para porta de saída 0
_output1 = outro      # Para porta de saída 1
```

---

## ✅ Checklist de Qualidade

Antes de exportar, verifique:

- [ ] Grafo não tem ciclos
- [ ] Todos os nós executam sem erro (teste com F5 no Assets)
- [ ] Nós definem `_output0`, `_output1`, etc. corretamente
- [ ] Imports estão explícitos no código dos nós
- [ ] Conexões entre nós estão corretas

---

## 📊 Comparação: Assets vs Python Exportado

| Aspecto | Assets (Visual) | Python Exportado |
|---------|----------------|------------------|
| **Edição** | Visual, intuitiva | Código direto |
| **Execução** | Dentro do Assets | Standalone Python |
| **Depuração** | Output panel | pdb, logging |
| **Versionamento** | .assets (binário) | .py (texto) |
| **Deploy** | Requer Assets | Apenas Python |
| **Paralelização** | Automática | Preservada |
| **Performance** | Igual | Igual |

---

## 🚀 Próximos Passos

1. **Teste básico:** Exporte grafo simples (3 nós)
2. **Teste concorrência:** Exporte grafo com múltiplos branches paralelos
3. **Teste referências:** Exporte grafo com nós por referência
4. **Deploy:** Use script exportado em produção

---

## 📝 Limitações Conhecidas

1. **Variáveis globais:** Nós que dependem de variáveis globais podem não funcionar
2. **Side effects:** Operações de I/O (arquivos, rede) são preservadas
3. **Estado compartilhado:** Threads não compartilham estado (use outputs explícitos)

---

## ✨ Exemplo Real: Pipeline de Dados

### Grafo Visual

```
[Fetch Yahoo Finance] → [Calculate Returns] → [Plot Results]
         ↓
    [Save to CSV]
```

### Código Exportado

```bash
python3 export_to_code.py
```

**Resultado:** Script standalone que busca dados, calcula retornos, salva CSV e plota gráfico - tudo em paralelo onde possível!

---
**Projeto:** Assets - Visual Node-Based Data Analysis
**Data:** 2025-12-08

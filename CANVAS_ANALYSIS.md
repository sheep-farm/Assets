# 🔍 Análise do canvas.py - "Frankenstein Code"

## 📊 Estatísticas Gerais

- **Total de linhas**: 2760
- **Total de métodos**: 69
- **Média de linhas por método**: 39.7
- **Métodos longos (>100 linhas)**: 7
- **Métodos curtos (<20 linhas)**: 21

## 🚨 Problemas Críticos

### 1. **Imports Duplicados** ❌
```
5x: from pathlib import Path
5x: from gi.repository import GLib
4x: import traceback
2x: import threading
2x: from .node import NodeExecutionState
2x: import pickle
2x: import base64
2x: import time
```

**Impacto**: Confusão, possível overhead no carregamento.

### 2. **Métodos Gigantes** 🐘

| Linhas | Método | Linha |
|--------|--------|-------|
| 173 | `_execute_via_system_venv` | 1661 |
| 170 | `on_key_pressed` | 752 |
| 139 | `_paste_node` | 1151 |
| 131 | `execute_graph` | 1331 |
| 126 | `on_draw` | 2159 |
| 123 | `on_mouse_pressed` | 414 |
| 109 | `_execute_node_code` | 1834 |

**Problemas**:
- Difícil de manter
- Difícil de testar
- Múltiplas responsabilidades
- Viola Single Responsibility Principle

### 3. **Código Comentado** 💀
- **92 linhas** de código comentado (heurística)
- Código morto que deveria estar no git, não no arquivo

### 4. **Print Statements de Debug** 🐛
- **65 print statements**
- Deveria usar logging adequado
- Poluição do console

### 5. **Nested Ifs Profundos** 🌲
- **4 casos** com 6+ níveis de indentação
- Complexidade ciclomática alta
- Difícil de entender e debugar

### 6. **TODOs/FIXMEs** 📝
- **2 itens** pendentes no código

---

## 🏗️ Problemas de Arquitetura

### Responsabilidades Misturadas

O arquivo `canvas.py` está fazendo **MUITA COISA**:

1. ✅ **Renderização** (correto para Canvas)
   - `on_draw()`
   - `_draw_connections()`
   - `_draw_connection()`

2. ❌ **Execução de Código Python** (deveria estar em executor separado)
   - `execute_graph()` (131 linhas!)
   - `_execute_via_system_venv()` (173 linhas!!)
   - `_execute_node_code()` (109 linhas)
   - `_collect_node_inputs()`
   - `_process_special_output()`

3. ❌ **Gerenciamento de UI** (deveria estar em dialogs/controllers)
   - `_show_node_context_menu()`
   - `_show_canvas_context_menu()`
   - `_show_multi_selection_menu()`
   - `edit_node_code()`
   - `rename_node()`
   - `show_node_properties()`

4. ❌ **Algoritmos de Grafo** (deveria estar em graph_algorithms.py)
   - `_topological_sort()`
   - `_group_by_execution_level()`

5. ❌ **Clipboard/Serialização** (deveria estar em clipboard_manager.py)
   - `_copy_focused_node()`
   - `_paste_node()` (139 linhas!)
   - `_duplicate_focused_node()`

6. ❌ **Keyboard/Mouse Handlers** (poderia estar em input_controller.py)
   - `on_key_pressed()` (170 linhas!!)
   - `on_mouse_pressed()` (123 linhas)
   - `on_drag_begin/update/end()`

---

## 📋 Recomendações de Refatoração

### Prioridade ALTA 🔴

1. **Extrair GraphExecutor**
   ```
   Mover para: src/graph_executor.py
   - execute_graph()
   - _execute_via_system_venv()
   - _execute_node_code()
   - _collect_node_inputs()
   - _topological_sort()
   - _group_by_execution_level()
   ```

2. **Limpar Imports Duplicados**
   - Consolidar todos os imports no topo
   - Remover duplicações

3. **Quebrar Métodos Gigantes**
   - `on_key_pressed`: separar em handlers individuais
   - `_execute_via_system_venv`: separar setup, execução, cleanup
   - `_paste_node`: separar validação, criação, posicionamento

### Prioridade MÉDIA 🟡

4. **Extrair ClipboardManager**
   ```
   Mover para: src/clipboard_manager.py
   - _copy_focused_node()
   - _paste_node()
   - _duplicate_focused_node()
   - _cut_context_node()
   ```

5. **Extrair InputController**
   ```
   Mover para: src/input_controller.py
   - Todos os handlers de mouse/keyboard
   - Gestão de gestures
   ```

6. **Remover Código Comentado**
   - Git guarda histórico
   - Limpar 92 linhas comentadas

### Prioridade BAIXA 🟢

7. **Substituir Print por Logging**
   - Criar logger: `logger = logging.getLogger(__name__)`
   - Substituir 65 prints por `logger.debug/info/warning`

8. **Refatorar Nested Ifs**
   - Early returns
   - Extract methods
   - Guard clauses

---

## 🎯 Estrutura Ideal Proposta

```
src/
├── canvas.py                    # APENAS rendering e coordenação
│   └── ~500 linhas (vs 2760 atual)
│
├── graph_executor.py            # NOVO - execução de grafos
│   ├── GraphExecutor
│   ├── topological_sort()
│   └── execute_via_venv()
│
├── clipboard_manager.py         # NOVO - copy/paste/duplicate
│   └── ClipboardManager
│
├── input_controller.py          # NOVO - mouse/keyboard
│   ├── MouseController
│   └── KeyboardController
│
├── canvas_drawing.py            # NOVO - métodos de desenho
│   ├── draw_connections()
│   ├── draw_nodes()
│   └── draw_selection_box()
│
└── graph_algorithms.py          # NOVO - algoritmos
    ├── topological_sort()
    └── group_by_execution_level()
```

---

## 📈 Métricas Antes vs Depois

| Métrica | Antes | Depois (estimado) |
|---------|-------|-------------------|
| Linhas em canvas.py | 2760 | ~500 |
| Método mais longo | 173 linhas | <50 linhas |
| Responsabilidades | 6+ | 1-2 |
| Testabilidade | ⭐ | ⭐⭐⭐⭐⭐ |
| Manutenibilidade | ⭐ | ⭐⭐⭐⭐⭐ |

---

## 🚀 Próximos Passos

1. **Criar branch de refatoração**: `git checkout -b refactor/canvas-cleanup`
2. **Extrair GraphExecutor primeiro** (maior impacto)
3. **Testes unitários** para cada classe extraída
4. **Iteração incremental** - não refatorar tudo de uma vez
5. **Code review** após cada extração

---

## ⚠️ Riscos da Refatoração

- **Alto**: Canvas é o coração da aplicação
- **Quebrar funcionalidades existentes**
- **Introduzir bugs sutis**

**Mitigação**:
- Testes automatizados ANTES de refatorar
- Refatoração incremental
- Feature flags para código novo vs antigo
- Testes extensivos após cada mudança

---

## 💡 Conclusão

O `canvas.py` está de fato um **"Frankenstein"**:
- Muito código (2760 linhas)
- Muitas responsabilidades misturadas
- Métodos gigantes (até 173 linhas)
- Imports duplicados
- Código comentado

**Porém**: O código **funciona**. A refatoração deve ser feita com cuidado e incrementalmente.

**Recomendação**: Começar extraindo **GraphExecutor** (maior ganho, menor risco).

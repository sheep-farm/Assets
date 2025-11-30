# Formato .assets - Metadados de Projeto

## Visão Geral

A partir de agora, arquivos `.assets` incluem metadados do projeto **dentro do próprio arquivo JSON**. Não há mais arquivos separados de requirements.

## Estrutura Completa

```json
{
  "version": "1.0",

  "nodes": [
    {
      "id": "uuid-here",
      "title": "Load Data",
      "code": "import pandas as pd\n...",
      "x": 100,
      "y": 200,
      ...
    }
  ],

  "connections": [
    {
      "source_node_id": "uuid-1",
      "source_port": 0,
      "target_node_id": "uuid-2",
      "target_port": 0
    }
  ],

  "view_state": {
    "zoom": 1.0,
    "offset_x": 0,
    "offset_y": 0
  },

  "project_metadata": {
    "requirements": ["pandas", "fredapi", "statsmodels"],
    "author": "Flávio de Vasconcellos Corrêa",
    "description": "Modelo VAR para análise de inflação",
    "created_at": "2025-01-29T10:00:00Z",
    "modified_at": "2025-01-29T15:30:00Z",
    "tags": ["economia", "inflação", "VAR"],
    "version": "1.0.0"
  }
}
```

## Campos de project_metadata

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `requirements` | list[str] | ✓ | Lista de pacotes Python necessários |
| `author` | str | - | Nome do autor do projeto |
| `description` | str | - | Descrição do que o projeto faz |
| `created_at` | str (ISO 8601) | - | Data/hora de criação |
| `modified_at` | str (ISO 8601) | - | Data/hora da última modificação |
| `tags` | list[str] | - | Tags para categorização |
| `version` | str | - | Versão do projeto (semver) |

## Comportamento Automático

### 1. Ao Abrir Projeto

```python
# Sistema automaticamente:
graph_data = load_graph("projeto.assets")

# 1. Lê metadados
metadata = graph_data["project_metadata"]
requirements = metadata["requirements"]

# 2. Verifica instalados
for pkg in requirements:
    if not is_installed(pkg):
        pip install --user pkg

# 3. Atualiza modified_at
metadata["modified_at"] = datetime.now().isoformat()
```

### 2. Ao Salvar Projeto

```python
# Sistema automaticamente:

# 1. Escaneia imports no código
detected = scan_imports(nodes)  # ['pandas', 'fredapi']

# 2. Atualiza requirements
metadata["requirements"] = list(detected)

# 3. Atualiza timestamp
metadata["modified_at"] = datetime.now().isoformat()

# 4. Salva tudo junto
save_graph(..., project_metadata=metadata)
```

## Vantagens

✅ **Arquivo único** - Tudo em um lugar
✅ **Portável** - Compartilhe `.assets` e as dependências vão junto
✅ **Versionável** - Git diff mostra mudanças em metadados
✅ **Autodocumentado** - Sabe quem criou, quando, para quê

## Compatibilidade

### Projetos Antigos (sem metadata)

```json
{
  "version": "1.0",
  "nodes": [...],
  "connections": [...]
  // SEM project_metadata
}
```

**Sistema cria automaticamente:**

```json
{
  "version": "1.0",
  "nodes": [...],
  "connections": [...],
  "project_metadata": {
    "requirements": [],  // Detectado no próximo save
    "author": "",
    "description": "",
    "created_at": null,
    "modified_at": null
  }
}
```

## Exemplo de Uso

### Criar Projeto Novo

```python
from graph_io import GraphSerializer

metadata = {
    "requirements": [],  # Detectado automaticamente
    "author": "Flávio Corrêa",
    "description": "Análise de séries temporais econômicas",
    "created_at": "2025-01-29T10:00:00Z",
    "tags": ["economia", "mestrado"]
}

GraphSerializer.save_graph(
    nodes,
    connections,
    "projeto.assets",
    project_metadata=metadata
)
```

### Ler Metadados

```python
import json

with open("projeto.assets") as f:
    data = json.load(f)

print(data["project_metadata"]["author"])
# → "Flávio Corrêa"

print(data["project_metadata"]["requirements"])
# → ["pandas", "fredapi", "statsmodels"]
```

### Atualizar Metadados

```python
# Carregar
data = load_graph("projeto.assets")

# Modificar
data["project_metadata"]["description"] = "Nova descrição"
data["project_metadata"]["version"] = "1.1.0"

# Salvar
save_graph(..., project_metadata=data["project_metadata"])
```

## Metadados Futuros (Expansível)

O formato permite adicionar novos campos sem quebrar compatibilidade:

```json
"project_metadata": {
  "requirements": [...],
  "author": "...",

  // Futuro: Configurações
  "settings": {
    "auto_execute": true,
    "parallel_execution": true
  },

  // Futuro: Publicação
  "publication": {
    "doi": "10.1234/example",
    "journal": "Economic Review",
    "year": 2025
  },

  // Futuro: Reprodutibilidade
  "environment": {
    "python_version": "3.12",
    "os": "Linux",
    "seed": 42
  }
}
```

## Migração

Projetos antigos são migrados automaticamente ao abrir. Basta:

1. Abrir `.assets` antigo
2. Sistema adiciona `project_metadata` vazio
3. Ao salvar, metadados são preenchidos
4. Pronto! Agora tem metadados

Sem intervenção manual necessária! 🎉

# Como Usar Metadados de Projeto

## Acessando Project Settings

### 3 Formas de Abrir:

1. **Atalho de teclado:** `Ctrl+,` (Ctrl + vírgula)
2. **Menu:** Project → Settings (quando implementado no menu)
3. **Botão:** (quando adicionado à toolbar)

## Interface do Dialog

### Aba "General" (Geral)

Informações básicas do projeto:

```
┌─ General ────────────────────────────┐
│                                      │
│ Project Information                  │
│ ──────────────────────────────────── │
│                                      │
│ Author:       Flávio Corrêa          │
│ Description:  Modelo VAR para...     │
│ Version:      1.0.0                  │
│ Tags:         economia, inflação     │
│               (comma-separated)      │
│                                      │
└──────────────────────────────────────┘
```

**Campos:**
- **Author:** Seu nome
- **Description:** O que o projeto faz
- **Version:** Versionamento semântico (1.0.0, 1.2.3, etc)
- **Tags:** Palavras-chave separadas por vírgula

### Aba "Dependencies" (Dependências)

Lista de pacotes Python necessários:

```
┌─ Dependencies ───────────────────────┐
│                                      │
│ Python Dependencies                  │
│ (auto-detected from code)            │
│ ──────────────────────────────────── │
│                                      │
│ ✓ pandas       Auto-detected         │
│ ✓ fredapi      Auto-detected         │
│ ✓ statsmodels  Auto-detected         │
│                                      │
│ Manual Override                      │
│ ──────────────────────────────────── │
│                                      │
│ Additional Packages:                 │
│ yfinance, scipy                      │
│ (comma-separated)                    │
│                                      │
└──────────────────────────────────────┘
```

**Como funciona:**
- **Auto-detected:** Escaneados automaticamente do código dos nós
- **Additional Packages:** Para imports não detectados (dinâmicos)

### Aba "Info" (Informações)

Estatísticas e metadados técnicos:

```
┌─ Info ───────────────────────────────┐
│                                      │
│ Timestamps                           │
│ ──────────────────────────────────── │
│ Created:       2025-01-29 10:00:00   │
│ Last Modified: 2025-01-29 15:30:00   │
│                                      │
│ Project Statistics                   │
│ ──────────────────────────────────── │
│ Total Nodes:       12                │
│ Total Connections: 15                │
│                                      │
│ Advanced                             │
│ ──────────────────────────────────── │
│ ▼ Raw Metadata (JSON)                │
│   {                                  │
│     "author": "...",                 │
│     "requirements": [...]            │
│   }                                  │
│                                      │
└──────────────────────────────────────┘
```

**Recursos:**
- **Timestamps:** Criação e última modificação (auto)
- **Statistics:** Contador de nós e conexões
- **Raw JSON:** Edição avançada de metadados

## Exemplos de Uso

### Exemplo 1: Documentar Projeto de Dissertação

```
General:
├─ Author: Flávio de Vasconcellos Corrêa
├─ Description: Modelo VAR para análise de inflação brasileira (2010-2025)
├─ Version: 2.1.0
└─ Tags: economia, inflação, VAR, mestrado, UFRGS

Dependencies:
├─ Auto: pandas, statsmodels, fredapi
└─ Manual: matplotlib, seaborn
```

### Exemplo 2: Compartilhar Projeto

Ao enviar `.assets` para colega:

```json
{
  "project_metadata": {
    "author": "Flávio Corrêa",
    "description": "Análise de cointegração entre PIB e taxa de juros",
    "requirements": ["pandas", "statsmodels"],
    "version": "1.0.0",
    "tags": ["economia", "cointegração"]
  }
}
```

Seu colega abre e:
1. Vê quem criou (author)
2. Entende o que faz (description)
3. Instala deps automaticamente (requirements)

### Exemplo 3: Versionamento

```
v1.0.0 → Modelo inicial
  ├─ Author: Flávio
  ├─ Requirements: pandas, statsmodels
  └─ Tags: VAR

v1.1.0 → Adicionei previsão
  ├─ Author: Flávio
  ├─ Requirements: pandas, statsmodels, scikit-learn
  └─ Tags: VAR, forecast

v2.0.0 → Modelo completo com API FRED
  ├─ Author: Flávio
  ├─ Requirements: pandas, statsmodels, fredapi, scikit-learn
  └─ Tags: VAR, forecast, FRED
```

## Workflow Recomendado

### 1. Ao Criar Projeto Novo

```
1. Criar grafo
2. Ctrl+, para abrir settings
3. Preencher Author, Description
4. Salvar (Ctrl+S)
```

### 2. Durante Desenvolvimento

```
Dependencies são atualizados automaticamente!
Você só adiciona "Additional Packages" se necessário.
```

### 3. Antes de Compartilhar

```
1. Ctrl+, para revisar settings
2. Verificar Description está clara
3. Verificar Requirements estão completos
4. Atualizar Version se mudou
5. Salvar
```

### 4. Publicar (Futuro)

```
1. Adicionar tags apropriadas
2. Documentar no Description
3. Versão final (1.0.0)
4. Exportar/compartilhar .assets
```

## Metadados Salvos Automaticamente

✅ **Requirements** - Detectados do código
✅ **Created_at** - Na primeira vez que salva
✅ **Modified_at** - Toda vez que salva

## Metadados Manuais

✍️ **Author** - Você preenche
✍️ **Description** - Você preenche
✍️ **Version** - Você preenche
✍️ **Tags** - Você preenche
✍️ **Additional Packages** - Você preenche (opcional)

## Dicas

### Tag Sugeridas para Economia:

```
economia, econometria, séries-temporais, VAR, ARIMA,
cointegração, inflação, PIB, câmbio, juros, FRED,
banco-central, mestrado, dissertação, UFRGS
```

### Nomenclatura de Versão:

```
1.0.0 - Major.Minor.Patch

Major: Mudança incompatível (redesign completo)
Minor: Nova funcionalidade (adicionou nós)
Patch: Bug fix (corrigiu cálculo)

Exemplos:
1.0.0 → Versão inicial
1.1.0 → Adicionei previsão
1.1.1 → Corrigi bug no VAR
2.0.0 → Mudei completamente o modelo
```

### Description Boa:

```
❌ Ruim:  "Modelo"
❌ Ruim:  "Projeto de mestrado"
✅ Bom:   "Modelo VAR para inflação brasileira"
✅ Melhor: "Modelo VAR bivariado analisando relação entre IPCA e taxa SELIC (2010-2025)"
```

## Buscar Metadados via Terminal

```bash
# Ver tudo
python3 -c "import json; print(json.dumps(json.load(open('projeto.assets'))['project_metadata'], indent=2))"

# Só author
python3 -c "import json; print(json.load(open('projeto.assets'))['project_metadata']['author'])"

# Só requirements
python3 -c "import json; print(json.load(open('projeto.assets'))['project_metadata']['requirements'])"
```

## Compatibilidade

Projetos antigos (sem metadata) ganham metadados vazios automaticamente ao abrir.
Basta preencher e salvar!

---

**Atalho:** `Ctrl+,` 🎯

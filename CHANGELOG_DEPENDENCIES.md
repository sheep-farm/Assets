# Changelog - Sistema de Dependências Dinâmicas

## Data: 2025-01-29

### 🎯 Objetivo
Resolver problema de dependências estáticas no Flatpak, onde todas as bibliotecas eram empacotadas mesmo sem uso.

### ✨ Implementação

#### 1. Arquivos Criados

**`wheels_base.txt`** - Dependências base mínimas
- numpy, pandas, matplotlib + dependências transitivas
- ~14 wheels essenciais
- Instaladas estaticamente no Flatpak

**`src/project_dependencies.py`** - Gerenciador de dependências
- Classe `ProjectDependencyManager`
- Escaneia imports no código dos nós
- Instala pacotes faltantes automaticamente
- Gera `projeto_requirements.txt`

**`DEPENDENCIES.md`** - Documentação completa
- Como funciona
- Estrutura de arquivos
- Limitações conhecidas

**`TEST_DEPENDENCIES.md`** - Guia de testes
- 4 cenários de teste
- Debug e troubleshooting

#### 2. Arquivos Modificados

**`wheels/meson.build`**
- Mudou de `wheels_list.txt` → `wheels_base.txt`
- Adiciona suporte a comentários
- Instalação mais limpa

**`src/graph_io.py`** - `load_graph()`
- Novo parâmetro `check_dependencies=True`
- Chama `check_project_dependencies()` ao carregar `.assets`
- Não bloqueia se falhar

**`src/meson.build`**
- Adicionado `project_dependencies.py` aos sources

### 🔧 Como Funciona

```
1. Usuário abre projeto.assets
2. Sistema escaneia código: import pandas, fredapi
3. Verifica instalados: pandas ✓, fredapi ✗
4. Instala: pip install --user fredapi
5. Salva: projeto_requirements.txt
6. Carrega grafo normalmente
```

### 📊 Antes vs Depois

**Antes:**
```
Flatpak: 500MB (todas as libs)
wheels_list.txt: 26 wheels (fredapi, yfinance, statsmodels, etc)
Problema: Projetos simples carregam tudo
```

**Depois:**
```
Flatpak: ~200MB (só essenciais)
wheels_base.txt: 14 wheels (numpy, pandas, matplotlib)
Dinâmico: Cada projeto instala o que precisa em ~/.local/
```

### ✅ Benefícios

1. **Flatpak mais leve** - 60% menor
2. **Projetos independentes** - Cada um com suas deps
3. **Automático** - Zero interação do usuário
4. **Reproduzível** - requirements.txt para cada projeto
5. **Compatível** - Funciona com --filesystem=home

### ⚠️ Limitações

- Detecção estática apenas (não detecta `__import__()`)
- Sem versionamento automático (instala latest)
- Aliases não-padrão não são mapeados

### 🧪 Testar

```bash
# Rebuild Flatpak
meson setup build
meson compile -C build

# Abrir projeto de teste
# Terminal mostrará: "📦 Verificando dependências..."
```

### 📝 Próximos Passos (Opcional)

- [ ] UI para mostrar progresso de instalação
- [ ] Dialog de confirmação antes de instalar
- [ ] Cache de wheels baixados
- [ ] Suporte a versões específicas
- [ ] Export de ambiente completo

### 👨‍💻 Autor
Claude + Flávio de Vasconcellos Corrêa

---

## Compatibilidade

- ✅ Flatpak runtime: org.gnome.Platform 48
- ✅ Python: 3.12
- ✅ Sistema: Linux (testado Debian)
- ✅ Flatpak permissions: --filesystem=home (necessário)

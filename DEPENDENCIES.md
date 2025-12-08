# Sistema de Gerenciamento de Dependências

## Visão Geral

A partir desta versão, os arquivos `.assets` são **arquivos ZIP** contendo:

```
project.assets (ZIP)
├── graph.json          # Dados do grafo (nós, conexões, metadados)
└── wheels/             # Dependências Python (.whl)
    ├── pandas-2.0.0-py3-none-any.whl
    ├── numpy-1.24.0-py3-none-any.whl
    └── ...
```

## Características Principais

### Isolamento por Projeto

- Cada projeto tem seu próprio conjunto de dependências
- Projetos com versões diferentes de uma mesma biblioteca **não conflitam**
- As dependências são carregadas **apenas quando o projeto está ativo**
- Ao fechar/trocar de projeto, o ambiente é limpo automaticamente

### Portabilidade

- Um arquivo `.assets` contém **tudo** que o projeto precisa
- Pode ser compartilhado entre máquinas sem preocupação com dependências
- Funciona dentro do Flatpak sem necessidade de instalar pacotes globalmente

## Uso via Interface Gráfica

### Carregando um Projeto

1. Abra o projeto `.assets` normalmente (File > Open)
2. O sistema automaticamente:
   - Extrai os wheels em um diretório temporário
   - Adiciona os wheels ao `sys.path` (isolado)
   - Verifica se há dependências faltando

### Adicionando Dependências

**Método 1: Via Menu (futuro)**
```
Menu > Manage Dependencies > Add Package
```

**Método 2: Via Terminal**
```bash
# Dentro do Flatpak
flatpak run --command=sh com.assets.Assets -c \
  "python3 -m src add-deps /path/to/project.assets yfinance pandas"

# Ou localmente
python3 -m src add-deps project.assets yfinance pandas
```

## Uso via CLI

### Comandos Disponíveis

```bash
# Adicionar dependências (baixa wheels automaticamente)
python3 -m src add-deps <project.assets> <package1> [package2 ...]

# Adicionar wheels de um diretório
python3 -m src add-wheels <project.assets> <wheels_dir/>

# Listar dependências
python3 -m src list-deps <project.assets>

# Migrar projeto antigo (JSON) para novo formato (ZIP)
python3 -m src migrate <old.assets> <new.assets>

# Criar novo projeto vazio
python3 -m src create <new.assets>
```

### Exemplos Práticos

#### Adicionar yfinance a um projeto

```bash
cd /home/flavio/GitHub/Assets

# Se tiver pip instalado
python3 -m src add-deps ~/mestrado/forex_analysis.assets yfinance

# Se não tiver pip, baixe manualmente e use:
# 1. Baixe os wheels em algum lugar
# 2. Adicione ao projeto:
python3 -m src add-wheels ~/mestrado/forex_analysis.assets ~/downloads/wheels/
```

#### Migrar projetos antigos

```bash
# Migrar projeto antigo
python3 -m src migrate \
  ~/mestrado/test_yfinance.assets \
  ~/mestrado/test_yfinance_new.assets

# Adicionar dependências
python3 -m src add-deps \
  ~/mestrado/test_yfinance_new.assets \
  yfinance matplotlib pandas
```

#### Verificar dependências

```bash
# Ver quais wheels estão incluídos
python3 -m src list-deps ~/mestrado/project.assets
```

## Funcionamento Interno

### Carregamento do Projeto

1. `window.py` abre o arquivo `.assets`
2. `ProjectTab.setup_isolated_environment()` é chamado
3. `AssetsProject` extrai wheels para `/tmp/assets_<project_name>_<random>/`
4. Wheels são adicionados ao início do `sys.path`
5. Código dos nós pode importar pacotes dos wheels

### Execução de Nós

1. `canvas.execute_graph()` executa topologicamente
2. Cada nó executa com os wheels disponíveis no `sys.path`
3. Imports funcionam normalmente: `import pandas as pd`

### Limpeza

1. Ao fechar projeto/aplicação, `ProjectTab.cleanup_isolated_environment()` é chamado
2. Wheels são removidos do `sys.path`
3. Diretório temporário é deletado
4. Outros projetos **não são afetados**

## Vantagens da Arquitetura

### Para Desenvolvedores

- Não precisa instalar dependências globalmente
- Testa com versões específicas de bibliotecas
- Reproduz ambientes facilmente

### Para Usuários

- Abra e execute projetos sem configuração
- Compartilhe projetos completos (grafo + deps)
- Não se preocupe com conflitos de versão

### Para o Sistema

- Flatpak não precisa de permissões extras
- Não polui ambiente Python do sistema
- Fácil de limpar (apenas delete /tmp)

## Limitações e Considerações

### Versão do Python

- Wheels são baixados para **Python 3.13** (versão do Flatpak)
- Se usar outra versão, pode haver incompatibilidades

### Plataforma

- Wheels são baixados para **Linux x86_64** (manylinux2014)
- Em outras plataformas, baixe wheels manualmente

### Dependências Nativas

- Bibliotecas com extensões C (numpy, pandas, etc.) funcionam via wheels
- Dependências de sistema (libxml2, etc.) **não são incluídas**
- Use bibliotecas Python puras quando possível

### Tamanho dos Arquivos

- Wheels podem ser grandes (ex: scipy ~50MB)
- Arquivo `.assets` cresce com as dependências
- Considere compartilhar apenas wheels necessários

## Troubleshooting

### "pip não disponível no sistema"

Se `add-deps` falhar porque pip não está instalado:

```bash
# Opção 1: Instalar pip
sudo apt install python3-pip

# Opção 2: Baixar wheels manualmente
# 1. Em uma máquina com pip:
pip3 download --dest ~/wheels --only-binary :all: yfinance

# 2. Copie para o sistema sem pip
scp -r ~/wheels user@target:/tmp/

# 3. Adicione ao projeto:
python3 -m src add-wheels project.assets /tmp/wheels/
```

### "Module not found" ao executar

Se um nó falha com `ModuleNotFoundError`:

1. Verifique se o wheel está no projeto:
   ```bash
   python3 -m src list-deps project.assets
   ```

2. Se não estiver, adicione:
   ```bash
   python3 -m src add-deps project.assets <package_name>
   ```

3. Se estiver mas ainda falha, pode ser nome diferente:
   - Import: `import cv2` → Package: `opencv-python`
   - Import: `import PIL` → Package: `Pillow`

### Conflitos entre Projetos

**Não deve acontecer!** Cada projeto tem ambiente isolado.

Se acontecer, reporte como bug com:
- Passos para reproduzir
- Output do terminal
- Projetos afetados

## Roadmap

### v1.1 (Próxima Release)

- [ ] UI para gerenciar dependências
- [ ] Auto-detecção de imports nos nós
- [ ] Sugestão de pacotes ao adicionar nós
- [ ] Cache de wheels comuns (~/.cache/assets/wheels/)

### v1.2 (Futuro)

- [ ] Resolver dependências transitivas automaticamente
- [ ] Compartilhar wheels entre projetos (hard links)
- [ ] Suporte a conda packages
- [ ] Verificar assinaturas de wheels

## Arquivos Relevantes

```
src/
├── zip_project.py           # Gerencia .assets como ZIP
├── dependency_manager.py    # Detecta imports e gerencia deps
├── graph_io.py              # Save/Load com suporte a ZIP
├── project_tab.py           # Gerencia ambiente isolado por aba
├── window.py                # Integração com UI
├── cli.py                   # Interface de linha de comando
└── __main__.py              # Entry point do CLI
```

## Contribuindo

Se quiser contribuir com melhorias no sistema de dependências:

1. Teste o isolamento entre projetos
2. Verifique compatibilidade com diferentes wheels
3. Documente casos de uso específicos
4. Reporte bugs com contexto completo

## Licença

GPL-3.0-or-later (mesma do projeto principal)

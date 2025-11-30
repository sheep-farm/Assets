# System Python Mode - Documentação

## Visão Geral

O Assets agora suporta **dois modos** de execução Python:

1. **Modo Flatpak** (padrão): Wheels empacotados dentro do .assets
2. **Modo System** (novo): Usa Python do sistema com venvs isolados

## Quando Usar Cada Modo

### Modo Flatpak (`python_mode: "flatpak"`)
**Use quando:**
- Quer portabilidade total (projeto funciona sem Python instalado)
- Dependências simples (pandas, numpy, matplotlib)
- Projeto precisa funcionar offline

**Limitações:**
- Problemas com bibliotecas que usam curl_cffi, browsers, etc.
- Limitado ao que funciona dentro do Flatpak

### Modo System (`python_mode: "system"`)
**Use quando:**
- Precisa de bibliotecas complexas (yfinance, selenium, etc.)
- Quer usar última versão das bibliotecas
- Tem controle sobre o ambiente (sabe que Python está instalado)

**Requisitos:**
- Python 3.8+ instalado no sistema (`/usr/bin/python3`)
- Pacote `python3-venv` instalado

## Como Configurar

### No project_metadata do .assets:

```json
{
  "project_metadata": {
    "python_mode": "system",
    "requirements": ["yfinance", "pandas", "scikit-learn"],
    "author": "Seu Nome",
    "description": "Projeto usando system Python"
  }
}
```

### Localização dos Venvs

Cada projeto cria seu venv em:
```
~/.local/share/assets/venvs/{nome_do_projeto}/
```

Por exemplo:
- `test_yfinance.assets` → `~/.local/share/assets/venvs/test_yfinance/`
- `analise_financeira.assets` → `~/.local/share/assets/venvs/analise_financeira/`

### O que Acontece ao Abrir um Projeto

1. Assets detecta `python_mode: "system"`
2. Verifica se venv existe em `~/.local/share/assets/venvs/{projeto}/`
3. Se não existe, cria com `/usr/bin/python3 -m venv`
4. Instala pacotes do `requirements` via pip
5. Executa nós via subprocess no venv

## Instalando Python no Sistema

### Debian/Ubuntu
```bash
sudo apt install python3 python3-venv python3-pip
```

### Fedora
```bash
sudo dnf install python3 python3-venv
```

### Arch
```bash
sudo pacman -S python python-pip
```

## Exemplos

### Exemplo 1: Projeto com yfinance

```json
{
  "project_metadata": {
    "python_mode": "system",
    "requirements": ["yfinance==0.2.28", "pandas", "matplotlib"]
  }
}
```

### Exemplo 2: Machine Learning

```json
{
  "project_metadata": {
    "python_mode": "system",
    "requirements": [
      "scikit-learn",
      "tensorflow",
      "pandas",
      "numpy"
    ]
  }
}
```

## Gerenciamento de Venvs

### Listar venvs criados
```bash
ls ~/.local/share/assets/venvs/
```

### Remover venv de um projeto
```bash
rm -rf ~/.local/share/assets/venvs/{nome_do_projeto}/
```

### Ativar venv manualmente (para debug)
```bash
source ~/.local/share/assets/venvs/{nome_do_projeto}/bin/activate
python --version
pip list
```

## Troubleshooting

### "Python não encontrado no sistema"
```bash
# Instale Python
sudo apt install python3 python3-venv
```

### "Erro ao criar venv"
```bash
# Verifique se python3-venv está instalado
python3 -m venv --help

# Se não, instale
sudo apt install python3-venv
```

### "Pacote não instala"
```bash
# Entre no venv e teste manualmente
source ~/.local/share/assets/venvs/{projeto}/bin/activate
pip install {pacote}
```

### Venv corrompido
```bash
# Delete e reabra o projeto no Assets
rm -rf ~/.local/share/assets/venvs/{projeto}/
```

## Permissões Flatpak

O Assets precisa destas permissões para acessar Python do host:

```json
"finish-args": [
  "--talk-name=org.freedesktop.Flatpak",
  "--filesystem=host:ro"
]
```

Já incluídas no manifest.

## Diferenças Técnicas

| Aspecto | Modo Flatpak | Modo System |
|---------|--------------|-------------|
| Execução | `exec()` in-process | `subprocess` via venv |
| Dependências | Wheels no .assets | pip install no venv |
| Portabilidade | Total | Requer Python no host |
| Isolamento | Por projeto (.assets) | Por projeto (venv) |
| Performance | Mais rápido | Mais lento (IPC) |
| Compatibilidade | Limitada | Total |

## Exemplo Completo

Arquivo: `test_system_venv.assets`

Criado em: `/home/flavio/mestrado/test_system_venv.assets`

Este projeto demonstra:
- Uso de yfinance no modo system
- Download de dados USD/BRL
- Exibição via console output

Ao abrir:
1. Cria venv em `~/.local/share/assets/venvs/test_system_venv/`
2. Instala yfinance e pandas
3. Executa nós via subprocess

## Notas Importantes

- **Venvs persistem** entre sessões (não são deletados ao fechar projeto)
- **Cada projeto tem seu venv** isolado (versões diferentes OK)
- **Código serializa via pickle** para passar dados entre processos
- **Timeout padrão**: 60s por nó (ajustável em `system_venv.py`)

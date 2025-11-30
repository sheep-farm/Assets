# Como Testar o Sistema de Dependências

## Teste 1: Projeto Básico (só pandas/numpy)

1. Crie um novo projeto com nós simples:

```python
# Nó 1: Load Data
import pandas as pd
data = pd.DataFrame({'x': [1, 2, 3]})
return (data,)
```

**Resultado esperado:**
```
✓ Grafo carregado: projeto.assets
📦 Verificando dependências do projeto...
✓ Todas as dependências já instaladas: pandas
```

---

## Teste 2: Projeto com FRED API

1. Crie nó usando fredapi:

```python
# Nó: Get FRED Data
from fredapi import Fred
fred = Fred(api_key='seu_key')
gdp = fred.get_series('GDP')
return ({'_table': gdp},)
```

**Resultado esperado:**
```
✓ Grafo carregado: projeto.assets
📦 Verificando dependências do projeto...
⚠️  Dependências faltando: fredapi
✓ Requirements salvos em: projeto_requirements.txt
📦 Instalando pacotes: fredapi
✓ Pacotes instalados com sucesso!
```

**Arquivo criado:** `projeto_requirements.txt`
```
fredapi
pandas
```

---

## Teste 3: Projeto Econométrico Completo

1. Crie nó com statsmodels:

```python
# Nó: VAR Model
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.api import VAR

# Dados de exemplo
data = load('data.csv')
model = VAR(data)
results = model.fit(2)

return ({'_console': str(results.summary())},)
```

**Resultado esperado:**
```
✓ Grafo carregado: modelo_var.assets
📦 Verificando dependências do projeto...
⚠️  Dependências faltando: statsmodels
✓ Requirements salvos em: modelo_var_requirements.txt
📦 Instalando pacotes: statsmodels
✓ Pacotes instalados com sucesso!
```

---

## Teste 4: Múltiplos Projetos Diferentes

**Projeto A:** `analise_fred.assets`
- Usa: pandas, fredapi
- Instala: fredapi

**Projeto B:** `modelo_arima.assets`
- Usa: pandas, statsmodels
- Instala: statsmodels

**Resultado:** Cada projeto tem seu `_requirements.txt` independente!

```
/home/usuario/mestrado/
├─ analise_fred.assets
├─ analise_fred_requirements.txt      # fredapi, pandas
├─ modelo_arima.assets
└─ modelo_arima_requirements.txt      # statsmodels, pandas
```

---

## Verificar Instalação Manual

```bash
# Ver o que foi instalado com --user
pip list --user

# Ver requirements de um projeto
cat ~/mestrado/projeto_requirements.txt

# Reinstalar manualmente se necessário
pip install --user -r ~/mestrado/projeto_requirements.txt
```

---

## Debug

Se algo não funcionar:

**1. Verificar se pip funciona:**
```bash
flatpak run com.github.sheep.farm.assets
# No terminal dentro do Flatpak:
python3 -m pip --version
```

**2. Verificar permissões:**
```bash
# Flatpak precisa de --filesystem=home
flatpak info --show-permissions com.github.sheep.farm.assets
```

**3. Testar import manual:**
```python
# Dentro da aplicação, em um nó:
try:
    import fredapi
    return ({'_console': 'fredapi OK!'},)
except ImportError as e:
    return ({'_console': f'Erro: {e}'},)
```

**4. Ver mensagens de debug:**
Ao abrir `.assets`, check terminal para mensagens:
```
📦 Verificando dependências do projeto...
  → Detectando imports...
  → Pacotes necessários: pandas, fredapi, statsmodels
  → Já instalados: pandas
  → Instalando: fredapi, statsmodels
✓ Pacotes instalados com sucesso!
```

---

## Logs Úteis

O sistema imprime tudo no terminal. Procure por:

- `📦 Verificando dependências...` - Início da verificação
- `⚠️  Dependências faltando:` - Lista o que vai instalar
- `✓ Pacotes instalados com sucesso!` - Tudo OK
- `❌ Erro ao instalar pacotes:` - Algo deu errado

---

## Troubleshooting

**Erro: "Permission denied"**
- Solução: Certifique que Flatpak tem `--filesystem=home`

**Erro: "No module named pip"**
- Solução: pip deve estar no runtime do Flatpak

**Pacotes não são detectados:**
- Verifique se usa padrão `import X` ou `from X import Y`
- Imports dinâmicos (`__import__()`) não são detectados

**Quer instalar versão específica:**
- Edite manualmente `projeto_requirements.txt`:
  ```
  fredapi==0.5.2
  statsmodels>=0.14.0
  ```
- Reinstale: `pip install --user -r projeto_requirements.txt`

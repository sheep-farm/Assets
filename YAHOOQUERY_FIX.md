# Como Corrigir o Erro do yahooquery

## Problema

```
ImpersonateError: Impersonating chrome123 is not supported
```

## Solução

O `yahooquery` usa `curl_cffi` para se passar por um browser. No Flatpak, versões muito novas do Chrome não são suportadas.

### Opção 1: Usar versão mais antiga do Chrome (Recomendado)

Edite o código do nó "Get USD/BRL" para:

```python
from yahooquery import Ticker

# Configurar para usar Chrome mais antigo
ticker = Ticker("USDBRL=X", impersonate="chrome110")
hist = ticker.history(period="1mo")

return (hist,)
```

### Opção 2: Usar requests simples (sem impersonation)

Se ainda não funcionar, use o `yfinance` que é mais simples:

```python
import yfinance as yf

# Baixar dados do dólar nos últimos 30 dias
ticker = yf.Ticker("USDBRL=X")
hist = ticker.history(period="1mo")

return (hist,)
```

### Opção 3: Usar pandas_datareader

```python
import pandas_datareader as pdr
from datetime import datetime, timedelta

# Últimos 30 dias
end = datetime.now()
start = end - timedelta(days=30)

df = pdr.get_data_yahoo("USDBRL=X", start=start, end=end)

return (df,)
```

## Como Atualizar o Nó

1. Abra o projeto
2. Clique duplo no nó "Get USD/BRL"
3. Substitua o código por uma das opções acima
4. Salve (Ctrl+S)
5. Execute o grafo novamente

## Nota sobre Dependências

- **yahooquery** → já instalado ✓
- **yfinance** → precisa adicionar (mais simples, recomendado)
- **pandas_datareader** → precisa adicionar

Para adicionar yfinance:
- Ctrl+D → Install Missing Dependencies
- Ou Menu → Manage Dependencies

## Recomendação

Use **yfinance** (opção 2) porque:
- ✅ Mais simples
- ✅ Mais estável
- ✅ Não precisa de impersonation
- ✅ Funciona bem no Flatpak

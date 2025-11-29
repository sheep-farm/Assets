# Guia de Programação de Nodes

Este guia mostra como usar as funções disponíveis dentro dos nodes para carregar e salvar dados.

## 📚 Funções Disponíveis

Todos os nodes têm acesso automático às seguintes funções e bibliotecas:

### Funções de I/O
- `load_data(filename)` ou `load(filename)` - Carrega arquivos do diretório do projeto
- `save_data(data, filename)` ou `save(data, filename)` - Salva dados no diretório do projeto
- `project_dir` - Path do diretório do projeto (pathlib.Path)

### Bibliotecas Pré-importadas
- `pd` - pandas
- `np` - numpy
- `plt` - matplotlib.pyplot

## 📂 Diretório de Trabalho

O diretório padrão é:
- **Se o projeto foi salvo**: O diretório onde está o arquivo `.assets`
- **Se não foi salvo**: `~/Documents/Assets/`

## 🔧 Funções de I/O

### `load_data(filename)` ou `load(filename)`

Carrega arquivos automaticamente detectando o formato pela extensão:

**Formatos suportados:**
- `.csv` → pandas DataFrame
- `.xlsx`, `.xls` → pandas DataFrame
- `.json` → dict ou DataFrame (se for lista de objetos)
- `.parquet` → pandas DataFrame
- `.txt`, `.log` → string

**Exemplos:**

```python
# Carregar CSV
vendas = load_data("vendas_2024.csv")

# Carregar Excel
produtos = load("catalogo.xlsx")

# Carregar JSON
config = load_data("parametros.json")

# Usar project_dir manualmente
from pathlib import Path
dados = pd.read_csv(project_dir / "subpasta" / "arquivo.csv")
```

### `save_data(data, filename)` ou `save(data, filename)`

Salva dados automaticamente detectando o formato pela extensão do filename:

**Tipos suportados:**
- `pandas.DataFrame` → CSV, Excel, Parquet, JSON
- `matplotlib.Figure` → PNG, SVG, PDF
- `dict`, `list` → JSON
- `str` → TXT
- `numpy.ndarray` → NPY, CSV

**Exemplos:**

```python
# Salvar DataFrame como CSV
resultado = df.groupby('categoria').sum()
save_data(resultado, "resultado.csv")

# Salvar gráfico
fig, ax = plt.subplots()
ax.plot(df['x'], df['y'])
save_data(fig, "grafico.png")

# Salvar JSON
metricas = {"total": 1000, "media": 45.6}
save_data(metricas, "metricas.json")
```

## ✨ Convenção `_folder` (Auto-Save Mágico)

Você pode retornar um dict com chave `"_folder"` e os dados serão salvos automaticamente:

### Caso 1: Arquivo Único (Auto-gera Nome)

```python
# O sistema gera o nome baseado no título do node + timestamp
resultado = df.describe()
return {"_folder": resultado}

# Salvo como: "Nome_do_Node_20250128_143052.csv"
```

### Caso 2: Múltiplos Arquivos (Dict de Arquivos)

```python
# Você define os nomes
resumo = df.describe()
fig, ax = plt.subplots()
ax.plot(df['Close'])

return {
    "_folder": {
        "resumo_estatistico.csv": resumo,
        "grafico_precos.png": fig,
        "metricas.json": {"total": len(df)}
    }
}

# Salva 3 arquivos com os nomes especificados
```

### Caso 3: Híbrido (Retornar Dados + Auto-Save)

```python
# Salvar E passar para frente
resultado = process_data(df)

return {"_folder": resultado}, resultado
# Primeiro output: salva e retorna path do arquivo
# Segundo output: passa os dados para o próximo node
```

## 📝 Exemplos Completos

### Exemplo 1: ETL Simples

```python
# ========================================
# NODE: "Limpar Dados de Vendas"
# Inputs: nenhum
# Outputs: dataframe limpo
# ========================================

# Carregar dados brutos
vendas = load_data("vendas_raw.csv")

# Limpar
vendas_limpo = vendas.dropna()
vendas_limpo = vendas_limpo[vendas_limpo['valor'] > 0]

# Salvar versão limpa
save_data(vendas_limpo, "vendas_limpo.csv")

return vendas_limpo
```

### Exemplo 2: Análise e Visualização

```python
# ========================================
# NODE: "Análise de Vendas Mensais"
# Inputs: dataframe
# Outputs: múltiplos arquivos
# ========================================

df = inputs[0]

# Agrupar por mês
mensal = df.groupby('mes').agg({
    'valor': ['sum', 'mean', 'count']
})

# Criar gráfico
fig, ax = plt.subplots(figsize=(10, 6))
mensal['valor']['sum'].plot(kind='bar', ax=ax)
ax.set_title('Vendas Mensais - Total')
ax.set_ylabel('Valor (R$)')
plt.tight_layout()

# Salvar tudo automaticamente
return {
    "_folder": {
        "vendas_mensais.csv": mensal,
        "grafico_vendas.png": fig,
        "resumo.json": {
            "total_geral": float(mensal['valor']['sum'].sum()),
            "media_mensal": float(mensal['valor']['sum'].mean())
        }
    }
}
```

### Exemplo 3: Pipeline com Yahoo Finance

```python
# ========================================
# NODE: "Download e Análise de Ação"
# Inputs: ticker (str)
# Outputs: análise completa
# ========================================

import yfinance as yf

ticker = inputs[0] if len(inputs) > 0 else "PETR4.SA"

# Download dados
stock = yf.Ticker(ticker)
df = stock.history(period="1y")

# Calcular indicadores
df['MA20'] = df['Close'].rolling(20).mean()
df['MA50'] = df['Close'].rolling(50).mean()
df['Retorno'] = df['Close'].pct_change()

# Criar visualização
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

ax1.plot(df.index, df['Close'], label='Preço', linewidth=2)
ax1.plot(df.index, df['MA20'], label='MA20', linestyle='--')
ax1.plot(df.index, df['MA50'], label='MA50', linestyle='--')
ax1.set_title(f'{ticker} - Análise Técnica')
ax1.legend()
ax1.grid(True, alpha=0.3)

ax2.bar(df.index, df['Volume'], alpha=0.5)
ax2.set_title('Volume')
ax2.grid(True, alpha=0.3)

plt.tight_layout()

# Métricas
metricas = {
    'ticker': ticker,
    'preco_atual': float(df['Close'].iloc[-1]),
    'maxima_52w': float(df['Close'].max()),
    'minima_52w': float(df['Close'].min()),
    'retorno_anual': float((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100),
    'volatilidade': float(df['Retorno'].std() * np.sqrt(252) * 100)
}

# Auto-save de tudo
return {
    "_folder": {
        f"{ticker}_dados.csv": df,
        f"{ticker}_grafico.png": fig,
        f"{ticker}_metricas.json": metricas
    }
}
```

### Exemplo 4: Comparação de Múltiplos Ativos

```python
# ========================================
# NODE: "Comparar Carteira"
# Inputs: lista de tickers
# Outputs: análise comparativa
# ========================================

import yfinance as yf

tickers = inputs[0] if len(inputs) > 0 else ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]

# Download de todos
dados = {}
for ticker in tickers:
    df = yf.download(ticker, period="1y", progress=False)
    dados[ticker] = df['Close']

# Criar DataFrame consolidado
portfolio = pd.DataFrame(dados)

# Normalizar para comparação (base 100)
portfolio_norm = (portfolio / portfolio.iloc[0]) * 100

# Calcular retornos e correlação
retornos = portfolio.pct_change()
correlacao = retornos.corr()

# Visualizações
fig1, ax1 = plt.subplots(figsize=(12, 6))
portfolio_norm.plot(ax=ax1, linewidth=2)
ax1.set_title('Evolução da Carteira (Base 100)')
ax1.set_ylabel('Valor Normalizado')
ax1.legend()
ax1.grid(True, alpha=0.3)

import seaborn as sns
fig2, ax2 = plt.subplots(figsize=(8, 6))
sns.heatmap(correlacao, annot=True, cmap='coolwarm', center=0, ax=ax2)
ax2.set_title('Correlação entre Ativos')

plt.tight_layout()

# Estatísticas
stats = {
    'retorno_total': {ticker: float((portfolio[ticker].iloc[-1] / portfolio[ticker].iloc[0] - 1) * 100)
                      for ticker in tickers},
    'volatilidade': {ticker: float(retornos[ticker].std() * np.sqrt(252) * 100)
                     for ticker in tickers},
    'sharpe_aproximado': {ticker: float(retornos[ticker].mean() / retornos[ticker].std() * np.sqrt(252))
                          for ticker in tickers}
}

# Salvar análise completa
return {
    "_folder": {
        "portfolio_precos.csv": portfolio,
        "portfolio_retornos.csv": retornos,
        "correlacao.csv": correlacao,
        "evolucao_grafico.png": fig1,
        "correlacao_mapa.png": fig2,
        "estatisticas.json": stats
    }
}
```

## 🎯 Dicas e Boas Práticas

1. **Use `load_data()` e `save_data()`** para simplicidade - elas detectam formato automaticamente
2. **Use `_folder`** quando quiser salvar rapidamente sem se preocupar com paths
3. **Use `project_dir`** quando precisar de controle total sobre subpastas
4. **Combine abordagens** - `save_data()` para controle, `_folder` para auto-save
5. **Sempre retorne algo** - mesmo que seja só `_folder`, facilita debugging
6. **Nomes descritivos** - quando usar `_folder` com dict, use nomes claros para os arquivos

## ⚠️ Observações

- Todos os arquivos são salvos no **diretório do projeto**
- Se o projeto não foi salvo, usa `~/Documents/Assets/`
- Paths são sempre relativos ao `project_dir`
- Formatos são detectados pela **extensão do arquivo**
- Erros de I/O são capturados e exibidos no Output Panel

## 🚀 Próximos Passos

Para funcionalidade avançada, veja:
- Criar nodes customizados na biblioteca (`~/.nodes/`)
- Usar Group Nodes para organizar workflows complexos
- Salvar projetos para reutilização

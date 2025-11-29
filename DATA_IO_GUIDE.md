# Guia de I/O de Dados nos Nodes

Guia prático para carregar e salvar dados nos nodes do Assets.

---

## 📚 Funções Disponíveis

Todos os nodes têm acesso automático a:

### **Funções de I/O**
- `load_data(path)` ou `load(path)` - Carrega arquivos
- `save_data(data, path)` ou `save(data, path)` - Salva dados
- `{"_folder": data}` - Convenção para auto-save

### **Variáveis de Path**
- `home_dir` - `/home/usuario/`
- `project_dir` - `/home/usuario/` (mesmo que home)
- `nodes_dir` - `/home/usuario/.nodes/`
- `Path` - pathlib.Path (para construir caminhos)

### **Bibliotecas Pré-importadas**
- `pd` - pandas
- `np` - numpy
- `plt` - matplotlib.pyplot

---

## 🔧 1. load_data() - Carregar Dados

### **Sintaxe**
```python
data = load_data(caminho)
```

### **Formatos Suportados**

| Extensão | Tipo Retornado | Exemplo |
|----------|---------------|---------|
| `.csv` | pandas DataFrame | `load_data("~/dados.csv")` |
| `.xlsx`, `.xls` | pandas DataFrame | `load_data("~/planilha.xlsx")` |
| `.json` | dict ou DataFrame | `load_data("~/config.json")` |
| `.parquet` | pandas DataFrame | `load_data("~/dados.parquet")` |
| `.txt`, `.log` | string | `load_data("~/arquivo.txt")` |

### **Tipos de Paths**

#### **Path Absoluto com ~**
```python
# Expande ~ para /home/usuario/
df = load_data("~/GitHub/projeto/data/vendas.csv")
df = load_data("~/Downloads/planilha.xlsx")
df = load_data("~/Desktop/dados.json")
```

#### **Path Absoluto Completo**
```python
df = load_data("/home/usuario/GitHub/projeto/data/vendas.csv")
df = load_data("/tmp/arquivo.csv")
```

#### **Path Construído**
```python
# Usar variáveis para construir paths
base = home_dir / "GitHub" / "projeto"
dados_dir = base / "data"

df = load_data(dados_dir / "vendas.csv")
```

#### **Path Relativo** (raramente usado)
```python
# Relativo ao home_dir
df = load_data("Documents/arquivo.csv")
# Busca em: /home/usuario/Documents/arquivo.csv
```

### **Exemplos Práticos**

```python
# ========================================
# Carregar CSV
# ========================================
vendas = load_data("~/GitHub/projeto/data/vendas_2024.csv")

# ========================================
# Carregar Excel
# ========================================
planilha = load_data("~/Downloads/relatorio.xlsx")

# ========================================
# Carregar JSON
# ========================================
config = load_data("~/projeto/config.json")

# ========================================
# Carregar de múltiplas fontes
# ========================================
vendas = load_data("~/GitHub/projeto/vendas.csv")
clientes = load_data("~/GitHub/projeto/clientes.xlsx")
produtos = load_data("~/GitHub/projeto/produtos.json")

merged = vendas.merge(clientes, on='cliente_id')
```

---

## 💾 2. save_data() - Salvar Dados

### **Sintaxe**
```python
save_data(dados, caminho)
```

### **Tipos de Dados Suportados**

| Tipo de Dado | Extensões Suportadas | Exemplo |
|--------------|---------------------|---------|
| pandas DataFrame | `.csv`, `.xlsx`, `.parquet`, `.json` | `save_data(df, "~/resultado.csv")` |
| matplotlib Figure | `.png`, `.jpg`, `.svg`, `.pdf` | `save_data(fig, "~/grafico.png")` |
| dict, list | `.json` | `save_data({"a": 1}, "~/dados.json")` |
| string | `.txt`, `.log` | `save_data("texto", "~/arquivo.txt")` |
| numpy array | `.npy`, `.csv` | `save_data(arr, "~/array.npy")` |

### **Exemplos Práticos**

```python
# ========================================
# Salvar DataFrame como CSV
# ========================================
resultado = df.groupby('categoria').sum()
save_data(resultado, "~/GitHub/projeto/outputs/resumo.csv")

# ========================================
# Salvar DataFrame como Excel
# ========================================
save_data(df, "~/Desktop/relatorio.xlsx")

# ========================================
# Salvar Gráfico
# ========================================
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.plot(df['x'], df['y'])
ax.set_title('Vendas')

save_data(fig, "~/Desktop/vendas_grafico.png")

# ========================================
# Salvar JSON
# ========================================
metricas = {
    'total': 1000,
    'media': 45.6,
    'data': '2024-01-28'
}
save_data(metricas, "~/projeto/metricas.json")

# ========================================
# Salvar Múltiplos Formatos
# ========================================
# Mesmo dado, formatos diferentes
save_data(df, "~/outputs/dados.csv")
save_data(df, "~/outputs/dados.xlsx")
save_data(df, "~/outputs/dados.parquet")
```

---

## ✨ 3. _folder - Auto-Save Mágico

A convenção `_folder` permite salvar automaticamente retornando um dict especial.

### **Formato**
```python
return {"_folder": dados}
```

### **Caso 1: Arquivo Único (Nome Auto-gerado)**

O sistema gera o nome baseado no título do node + timestamp.

```python
# ========================================
# Auto-save Simples
# ========================================
df = load_data("~/projeto/vendas.csv")
resumo = df.describe()

# Salva automaticamente como:
# "Nome_do_Node_20250129_153045.csv"
return {"_folder": resumo}
```

### **Caso 2: Múltiplos Arquivos (Nomes Definidos)**

Use um dict dentro de `_folder` para salvar vários arquivos de uma vez.

```python
# ========================================
# Auto-save Múltiplos Arquivos
# ========================================
df = load_data("~/projeto/vendas.csv")

# Análises
resumo = df.describe()
mensal = df.groupby('mes').sum()

# Gráfico
fig, ax = plt.subplots()
ax.plot(df['mes'], df['total'])

# Métricas
stats = {
    'total': float(df['valor'].sum()),
    'media': float(df['valor'].mean())
}

# Salvar tudo de uma vez
return {
    "_folder": {
        "~/Desktop/resumo_estatistico.csv": resumo,
        "~/Desktop/vendas_mensais.csv": mensal,
        "~/Desktop/grafico_vendas.png": fig,
        "~/Desktop/metricas.json": stats
    }
}

# Resultado: 4 arquivos salvos no Desktop
```

### **Caso 3: Auto-save + Passar Dados**

Salvar E passar dados para o próximo node.

```python
# ========================================
# Auto-save + Output para Próximo Node
# ========================================
df = load_data("~/projeto/vendas.csv")
processado = df[df['valor'] > 100]

# Primeiro output: salva automaticamente
# Segundo output: passa para próximo node
return {"_folder": processado}, processado
```

### **Caso 4: Organizar Outputs em Pastas**

```python
# ========================================
# Salvar em Estrutura de Pastas
# ========================================
projeto = "~/GitHub/mestrado/python"

analise = df.describe()
grafico, ax = plt.subplots()
ax.plot(df['Close'])

return {
    "_folder": {
        f"{projeto}/outputs/analise.csv": analise,
        f"{projeto}/outputs/grafico.png": grafico,
        f"{projeto}/raw/dados_brutos.csv": df
    }
}
```

---

## 📖 Exemplos Completos

### **Exemplo 1: ETL Simples**

```python
# ========================================
# NODE: "Limpar Dados"
# Inputs: nenhum
# Outputs: dados limpos
# ========================================

# Carregar dados brutos
vendas = load_data("~/projeto/data/vendas_raw.csv")

# Limpar
vendas_limpo = vendas.dropna()
vendas_limpo = vendas_limpo[vendas_limpo['valor'] > 0]
vendas_limpo['data'] = pd.to_datetime(vendas_limpo['data'])

# Salvar versão limpa
save_data(vendas_limpo, "~/projeto/data/vendas_limpo.csv")

# Passar para próximo node
return vendas_limpo
```

### **Exemplo 2: Análise Completa com Auto-save**

```python
# ========================================
# NODE: "Análise de Vendas"
# Inputs: DataFrame
# Outputs: múltiplos arquivos
# ========================================

df = inputs[0] if len(inputs) > 0 else load_data("~/projeto/vendas.csv")

# 1. Análises
por_mes = df.groupby('mes').agg({
    'valor': ['sum', 'mean', 'count']
})

por_categoria = df.groupby('categoria')['valor'].sum()

# 2. Visualizações
fig1, ax1 = plt.subplots(figsize=(10, 6))
por_mes['valor']['sum'].plot(kind='bar', ax=ax1)
ax1.set_title('Vendas Mensais')
ax1.set_ylabel('Valor (R$)')
plt.tight_layout()

fig2, ax2 = plt.subplots(figsize=(8, 8))
por_categoria.plot(kind='pie', ax=ax2, autopct='%1.1f%%')
ax2.set_title('Vendas por Categoria')
plt.tight_layout()

# 3. Métricas
metricas = {
    'periodo': f"{df['data'].min()} a {df['data'].max()}",
    'total_vendas': float(df['valor'].sum()),
    'ticket_medio': float(df['valor'].mean()),
    'num_transacoes': int(len(df)),
    'categorias': df['categoria'].nunique()
}

# 4. Salvar tudo automaticamente
return {
    "_folder": {
        "~/projeto/outputs/vendas_mensais.csv": por_mes,
        "~/projeto/outputs/vendas_categoria.csv": por_categoria,
        "~/projeto/outputs/grafico_mensal.png": fig1,
        "~/projeto/outputs/grafico_categorias.png": fig2,
        "~/projeto/outputs/metricas.json": metricas,
        "~/projeto/outputs/dados_completos.csv": df
    }
}
```

### **Exemplo 3: Yahoo Finance + Análise Técnica**

```python
# ========================================
# NODE: "Análise de Ação"
# Inputs: ticker (string)
# Outputs: análise completa
# ========================================

import yfinance as yf

ticker = inputs[0] if len(inputs) > 0 else "PETR4.SA"

# 1. Download dados
stock = yf.Ticker(ticker)
df = stock.history(period="1y")

# 2. Calcular indicadores
df['MA20'] = df['Close'].rolling(20).mean()
df['MA50'] = df['Close'].rolling(50).mean()
df['Returns'] = df['Close'].pct_change()
df['Volatility'] = df['Returns'].rolling(20).std() * np.sqrt(252)

# 3. Visualização
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))

# Preço e Médias Móveis
ax1.plot(df.index, df['Close'], label='Preço', linewidth=2)
ax1.plot(df.index, df['MA20'], label='MA20', linestyle='--', alpha=0.7)
ax1.plot(df.index, df['MA50'], label='MA50', linestyle='--', alpha=0.7)
ax1.set_title(f'{ticker} - Análise Técnica')
ax1.set_ylabel('Preço (R$)')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Volume
ax2.bar(df.index, df['Volume'], alpha=0.5, color='steelblue')
ax2.set_ylabel('Volume')
ax2.grid(True, alpha=0.3)

# Retornos
ax3.plot(df.index, df['Returns'] * 100, alpha=0.7)
ax3.axhline(y=0, color='r', linestyle='--', alpha=0.3)
ax3.set_ylabel('Retorno (%)')
ax3.set_xlabel('Data')
ax3.grid(True, alpha=0.3)

plt.tight_layout()

# 4. Métricas
metricas = {
    'ticker': ticker,
    'periodo': f"{df.index[0].date()} a {df.index[-1].date()}",
    'preco_atual': float(df['Close'].iloc[-1]),
    'maxima_52w': float(df['Close'].max()),
    'minima_52w': float(df['Close'].min()),
    'retorno_periodo': float((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100),
    'volatilidade_anual': float(df['Returns'].std() * np.sqrt(252) * 100),
    'volume_medio': float(df['Volume'].mean())
}

# 5. Auto-save
base = f"~/GitHub/mestrado/analise_acoes"
return {
    "_folder": {
        f"{base}/{ticker}_dados_completos.csv": df,
        f"{base}/{ticker}_analise_tecnica.png": fig,
        f"{base}/{ticker}_metricas.json": metricas
    }
}
```

### **Exemplo 4: Comparação de Múltiplos Ativos**

```python
# ========================================
# NODE: "Comparar Portfólio"
# Inputs: lista de tickers
# Outputs: análise comparativa
# ========================================

import yfinance as yf
import seaborn as sns

tickers = inputs[0] if len(inputs) > 0 else ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]

# 1. Download
dados = {}
for ticker in tickers:
    print(f"Baixando {ticker}...")
    df = yf.download(ticker, period="1y", progress=False)
    dados[ticker] = df['Close']

# 2. Consolidar
portfolio = pd.DataFrame(dados)

# 3. Normalizar (base 100)
portfolio_norm = (portfolio / portfolio.iloc[0]) * 100

# 4. Retornos e Correlação
retornos = portfolio.pct_change()
correlacao = retornos.corr()

# 5. Visualizações
fig1, ax1 = plt.subplots(figsize=(12, 6))
portfolio_norm.plot(ax=ax1, linewidth=2)
ax1.set_title('Evolução do Portfólio (Base 100)')
ax1.set_ylabel('Valor Normalizado')
ax1.legend(loc='best')
ax1.grid(True, alpha=0.3)
plt.tight_layout()

fig2, ax2 = plt.subplots(figsize=(8, 6))
sns.heatmap(correlacao, annot=True, cmap='RdYlGn', center=0,
            vmin=-1, vmax=1, ax=ax2, square=True)
ax2.set_title('Correlação entre Ativos')
plt.tight_layout()

# 6. Estatísticas
stats = {}
for ticker in tickers:
    stats[ticker] = {
        'retorno_total_%': float((portfolio[ticker].iloc[-1] / portfolio[ticker].iloc[0] - 1) * 100),
        'volatilidade_anual_%': float(retornos[ticker].std() * np.sqrt(252) * 100),
        'retorno_medio_diario_%': float(retornos[ticker].mean() * 100),
        'sharpe_ratio': float(retornos[ticker].mean() / retornos[ticker].std() * np.sqrt(252)) if retornos[ticker].std() > 0 else 0
    }

# 7. Auto-save organizado
base = "~/GitHub/mestrado/portfolio"
return {
    "_folder": {
        f"{base}/portfolio_precos.csv": portfolio,
        f"{base}/portfolio_normalizado.csv": portfolio_norm,
        f"{base}/portfolio_retornos.csv": retornos,
        f"{base}/portfolio_correlacao.csv": correlacao,
        f"{base}/grafico_evolucao.png": fig1,
        f"{base}/grafico_correlacao.png": fig2,
        f"{base}/estatisticas.json": stats
    }
}
```

---

## 🎯 Resumo - Quando Usar Cada Um

### **Use `load_data()`**
- ✅ Carregar qualquer arquivo (CSV, Excel, JSON, etc)
- ✅ Sempre use paths absolutos com `~`
- ✅ Formato detectado automaticamente pela extensão

### **Use `save_data()`**
- ✅ Salvar explicitamente em local específico
- ✅ Quando precisa de controle total do caminho
- ✅ Para salvar durante processamento (não só no final)

### **Use `_folder`**
- ✅ Auto-save no final do processamento
- ✅ Salvar múltiplos arquivos de uma vez
- ✅ Manter código limpo (menos linhas de save)
- ✅ Quando quer salvar E passar dados adiante

---

## ⚠️ Dicas Importantes

1. **Sempre use paths absolutos com `~`**
   ```python
   ✅ load_data("~/GitHub/projeto/dados.csv")
   ❌ load_data("dados.csv")  # Pode não encontrar
   ```

2. **Crie pastas de output organizadas**
   ```python
   base = "~/GitHub/mestrado/python"
   save_data(df, f"{base}/outputs/resultado.csv")
   save_data(fig, f"{base}/graficos/plot.png")
   ```

3. **Use `_folder` para múltiplos outputs**
   ```python
   # Ao invés de:
   save_data(df1, "~/path/file1.csv")
   save_data(df2, "~/path/file2.csv")
   save_data(fig, "~/path/plot.png")

   # Use:
   return {"_folder": {
       "~/path/file1.csv": df1,
       "~/path/file2.csv": df2,
       "~/path/plot.png": fig
   }}
   ```

4. **Verifique o Output Panel**
   - Mensagens de `✅ Salvo:` confirmam sucesso
   - Mensagens de `❌ Erro:` indicam problemas

5. **Formatos são detectados pela extensão**
   ```python
   save_data(df, "~/output.csv")     # CSV
   save_data(df, "~/output.xlsx")    # Excel
   save_data(df, "~/output.parquet") # Parquet
   ```

---

## 🚀 Próximos Passos

- Explore os exemplos completos
- Adapte para seus dados
- Combine `load_data()`, `save_data()` e `_folder`
- Organize seus outputs em pastas lógicas

**Divirta-se analisando dados!** 📊

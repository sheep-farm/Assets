"""
node_library.py - Biblioteca de nós pré-configurados
"""

# Definição de templates de nós organizados por categoria
NODE_LIBRARY = {
    "Input": {
        "icon": "📥",
        "nodes": [
            {
                "name": "Stock Data",
                "description": "Carrega dados de ações via API",
                "num_inputs": 0,
                "num_outputs": 2,
                "default_code": """# Carregar dados de ações
import yfinance as yf

ticker = "AAPL"
data = yf.download(ticker, period="1y")

prices = data['Close'].values
dates = data.index.values

return (prices, dates)"""
            },
            {
                "name": "CSV File",
                "description": "Lê arquivo CSV",
                "num_inputs": 0,
                "num_outputs": 1,
                "default_code": """# Ler CSV
import pandas as pd

df = pd.read_csv('data.csv')
return (df,)"""
            },
            {
                "name": "Number",
                "description": "Valor numérico constante",
                "num_inputs": 0,
                "num_outputs": 1,
                "default_code": """# Número constante
value = 42
return (value,)"""
            },
            {
                "name": "Date Range",
                "description": "Gera intervalo de datas",
                "num_inputs": 0,
                "num_outputs": 1,
                "default_code": """# Intervalo de datas
import pandas as pd

start = "2024-01-01"
end = "2024-12-31"
dates = pd.date_range(start, end)

return (dates,)"""
            }
        ]
    },

    "Process": {
        "icon": "⚙️",
        "nodes": [
            {
                "name": "Math Operation",
                "description": "Operações matemáticas básicas",
                "num_inputs": 2,
                "num_outputs": 1,
                "default_code": """# Operação matemática
# inputs[0]: valor A
# inputs[1]: valor B

result = inputs[0] + inputs[1]  # Mude para -, *, /
return (result,)"""
            },
            {
                "name": "Moving Average",
                "description": "Calcula média móvel",
                "num_inputs": 2,
                "num_outputs": 1,
                "default_code": """# Média móvel
import pandas as pd

data = inputs[0]  # Array de preços
window = inputs[1] if len(inputs) > 1 else 20

sma = pd.Series(data).rolling(window=window).mean()
return (sma.values,)"""
            },
            {
                "name": "Returns",
                "description": "Calcula retornos percentuais",
                "num_inputs": 1,
                "num_outputs": 1,
                "default_code": """# Retornos percentuais
import numpy as np

prices = inputs[0]
returns = np.diff(prices) / prices[:-1] * 100

return (returns,)"""
            },
            {
                "name": "Filter",
                "description": "Filtra dados por condição",
                "num_inputs": 1,
                "num_outputs": 1,
                "default_code": """# Filtrar dados
import numpy as np

data = inputs[0]
# Exemplo: filtrar valores > 100
filtered = data[data > 100]

return (filtered,)"""
            },
            {
                "name": "Statistics",
                "description": "Calcula estatísticas básicas",
                "num_inputs": 1,
                "num_outputs": 3,
                "default_code": """# Estatísticas
import numpy as np

data = inputs[0]

mean = np.mean(data)
std = np.std(data)
max_val = np.max(data)

return (mean, std, max_val)"""
            }
        ]
    },

    "Output": {
        "icon": "📊",
        "nodes": [
            {
                "name": "Plot Chart",
                "description": "Exibe gráfico",
                "num_inputs": 2,
                "num_outputs": 0,
                "default_code": """# Plotar gráfico
import matplotlib.pyplot as plt

data = inputs[0]
label = inputs[1] if len(inputs) > 1 else "Data"

plt.figure()
plt.plot(data)
plt.title(label)
plt.show()

return ()"""
            },
            {
                "name": "Print Table",
                "description": "Imprime dados em tabela",
                "num_inputs": 1,
                "num_outputs": 0,
                "default_code": """# Imprimir tabela
import pandas as pd

data = inputs[0]
df = pd.DataFrame(data)
print(df.head(10))

return ()"""
            },
            {
                "name": "Export CSV",
                "description": "Salva dados em CSV",
                "num_inputs": 1,
                "num_outputs": 0,
                "default_code": """# Exportar CSV
import pandas as pd

data = inputs[0]
df = pd.DataFrame(data)
df.to_csv('output.csv', index=False)
print("✓ Saved to output.csv")

return ()"""
            },
            {
                "name": "Show Value",
                "description": "Mostra valor no console",
                "num_inputs": 1,
                "num_outputs": 0,
                "default_code": """# Mostrar valor
value = inputs[0]
print(f"Value: {value}")

return ()"""
            }
        ]
    },

    "Finance": {
        "icon": "💰",
        "nodes": [
            {
                "name": "Bollinger Bands",
                "description": "Calcula Bandas de Bollinger",
                "num_inputs": 2,
                "num_outputs": 3,
                "default_code": """# Bollinger Bands
import pandas as pd

prices = inputs[0]
window = inputs[1] if len(inputs) > 1 else 20

sma = pd.Series(prices).rolling(window=window).mean()
std = pd.Series(prices).rolling(window=window).std()

upper = sma + (std * 2)
lower = sma - (std * 2)

return (upper.values, sma.values, lower.values)"""
            },
            {
                "name": "RSI",
                "description": "Relative Strength Index",
                "num_inputs": 2,
                "num_outputs": 1,
                "default_code": """# RSI (Relative Strength Index)
import pandas as pd
import numpy as np

prices = inputs[0]
period = inputs[1] if len(inputs) > 1 else 14

delta = pd.Series(prices).diff()
gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

rs = gain / loss
rsi = 100 - (100 / (1 + rs))

return (rsi.values,)"""
            },
            {
                "name": "Sharpe Ratio",
                "description": "Calcula Sharpe Ratio",
                "num_inputs": 2,
                "num_outputs": 1,
                "default_code": """# Sharpe Ratio
import numpy as np

returns = inputs[0]
risk_free = inputs[1] if len(inputs) > 1 else 0.02

excess_returns = returns - risk_free
sharpe = np.mean(excess_returns) / np.std(excess_returns)

return (sharpe,)"""
            }
        ]
    }
}


def get_all_categories():
    """Retorna lista de categorias"""
    return list(NODE_LIBRARY.keys())


def get_nodes_in_category(category):
    """Retorna lista de nós em uma categoria"""
    if category in NODE_LIBRARY:
        return NODE_LIBRARY[category]["nodes"]
    return []


def get_category_icon(category):
    """Retorna ícone de uma categoria"""
    if category in NODE_LIBRARY:
        return NODE_LIBRARY[category]["icon"]
    return "📦"


def create_node_from_template(template, x, y):
    """
    Cria um nó a partir de um template.

    Args:
        template: Dict com definição do nó
        x, y: Posição inicial

    Returns:
        Node object
    """
    from .node import Node

    node = Node(
        x=x,
        y=y,
        title=template["name"],
        num_inputs=template["num_inputs"],
        num_outputs=template["num_outputs"]
    )

    # Adicionar código default (será implementado quando tivermos editor)
    node.code = template.get("default_code", "")

    return node

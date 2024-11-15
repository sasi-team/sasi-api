


# Função para mapear um valor para uma cor em um gradiente
def color_gradient_picker(valor, min_val=0, max_val=100):
    norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
    cmap = plt.cm.get_cmap('RdYlGn')  # Paleta de cores (pode ser alterada)
    rgba_color = cmap(norm(valor))
    hex_color = mcolors.rgb2hex(rgba_color)
    return hex_color

def get_max_min_values(df, year):
    min_val = df[year].min()
    max_val = df[year].max()
    return min_val, max_val

# Função para buscar o valor do indicador com base no ano e no código IBGE
def get_indicator_value(df, codigo_ibge, ano):
    """
    Busca o valor do indicador no DataFrame com base no ano e no código IBGE.
    
    Args:
        df (pd.DataFrame): DataFrame contendo os dados dos indicadores.
        codigo_ibge (str): Código IBGE do município.
        ano (str): Ano para o qual o valor do indicador é necessário.
    
    Returns:
        float: Valor do indicador para o município e ano especificados, ou 0 se não encontrado.
    """
    # Remover o último dígito do código IBGE
    codigo_ibge = str(codigo_ibge)[:-1]
    
    try:
        # Verificar se o código IBGE está no DataFrame
        if codigo_ibge in df['Cod. IBGE'].values:
            # Verificar se o ano está no DataFrame
            if ano in df.columns:
                valor = df[df['Cod. IBGE'] == codigo_ibge][ano].values[0]
            else:
                print(f"Ano {ano} não encontrado no DataFrame.")
                valor = 0
        else:
            print(f"Código IBGE {codigo_ibge} não encontrado no DataFrame.")
            valor = 0
    except Exception as e:
        print(f"Erro ao buscar valor para código IBGE {codigo_ibge} e ano {ano}: {e}")
        valor = 0
    
    return valor

# Função para extrair o valor da meta
def extract_meta_value(meta_text):
    match = re.search(r'(\d+(\.\d+)?)(?=%|)', meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r'Redução\s*(\d+(\.\d+)?)%', meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r'Meta Estadual:\s*(\d+(\.\d+)?)%', meta_text)
    if match:
        return float(match.group(1))
    match = re.search(r'Meta Estadual:\s*(\d+(\.\d+)?)', meta_text)
    if match:
        return float(match.group(1))
    return None
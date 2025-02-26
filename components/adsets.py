from ctypes import alignment
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from app import *

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash_bootstrap_templates import template_from_url, ThemeChangerAIO

from graph_api import *


# =========  Data Ingestion  =========== #
fb_api = open("tokens/fb_token").read()
ad_acc = "991384508583089"

fb_api = GraphAPI(ad_acc, fb_api)

# Carregamento inicial dos dados com tratamento de erros
try:
    campaign_insights_data = fb_api.get_insights(ad_acc)
    campaign_insights = pd.DataFrame(campaign_insights_data.get("data", []))
    
    adset_status_data = fb_api.get_adset_status(ad_acc)
    adset_status = pd.DataFrame(adset_status_data.get("data", []))
    
    adset_insights_data = fb_api.get_insights(ad_acc, "adset")
    adset_insights = pd.DataFrame(adset_insights_data.get("data", []))
    
    ads_insights_data = fb_api.get_insights(ad_acc, "ad")
    ads_insights = pd.DataFrame(ads_insights_data.get("data", []))
    
    # Verificar se temos dados válidos
    if adset_insights.empty or adset_status.empty:
        print("AVISO: Dados de conjuntos de anúncios vazios ou inválidos")
        if adset_insights.empty:
            adset_insights = pd.DataFrame(columns=["adset_name", "clicks", "spend"])
        if adset_status.empty:
            adset_status = pd.DataFrame(columns=["name", "id", "status"])
except Exception as e:
    print(f"Erro ao carregar dados iniciais: {e}")
    # Criar dataframes vazios para evitar quebra da aplicação
    campaign_insights = pd.DataFrame(columns=["campaign_name"])
    adset_status = pd.DataFrame(columns=["name", "id", "status"])
    adset_insights = pd.DataFrame(columns=["adset_name", "clicks", "spend"])
    ads_insights = pd.DataFrame(columns=["ad_name", "adset_name"])

# Garantir que temos pelo menos um valor para o dropdown
if adset_insights.empty or "adset_name" not in adset_insights.columns:
    adset_insights = pd.DataFrame([{"adset_name": "Sem dados disponíveis"}])


# =========  Layout  =========== #
layout = html.Div([
            dbc.Row([
                html.H3("Selecione o conjunto de anúncio:", style={"margin-top": "50px"}),
                dcc.Dropdown(
                    options=[{"label": i, "value": i} for i in adset_insights.adset_name.values],
                    value=adset_insights.adset_name.values[0] if not adset_insights.empty else None,
                    id='dd-adset'),
                ], style={"margin-bottom": "30px"}),

            dbc.Row([
                dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Status"),
                            dbc.CardBody([
                                dbc.Button("", id="btn-adset-status"),
                            ], id="cb-status-adset")
                        ], color="light"),

                    ], md=2),

                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Clicks"),
                            dbc.CardBody([
                                html.H4("", id="adset-clicks", style={"color": "var(--bs-info)"}),
                            ])
                        ], color="light"),

                    ], md=2),

                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Spend"),
                            dbc.CardBody([
                                html.H4("", id="adset-spend", style={"color": "var(--bs-primary)"}),
                            ])
                        ], color="light"),
                    ], md=2),
                
                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Conversion"),
                            dbc.CardBody([
                                html.H5("", id="adset-conversions", style={"color": "var(--bs-primary)"}),
                            ])
                        ], color="light"),
                    ], md=2),
            ]),

            dbc.Row([
                html.H4("Selecione o indicador:"),
                dcc.RadioItems(options=['Spend', 'CPC', 'CPM', 'Clicks', 'Conversion'], 
                            value='Conversion', id='adset-kind', 
                            inputStyle={"margin-right": "5px", "margin-left": "20px"}),
                ], style={"margin-top": "50px"}),

            dbc.Row([            
                dbc.Col(dcc.Graph(id="graph-line-adset"), md=6),
                dbc.Col(dcc.Graph(id="graph-bar-adset"), md=6)
                ], style={"margin-top": "20px"}),
            ]) 

#========== Callbacks ================
@app.callback([
                Output("cb-status-adset", "children"),
                Output("adset-clicks", "children"),
                Output("adset-spend", "children"),
                Output("adset-conversions", "children"),
            ], 
                [Input("dd-adset", "value"),
                ])
def render_page_content(adset):
    # Verificar se existem dados e se o valor selecionado é válido
    if adset is None or adset_status.empty or adset_insights.empty:
        return [dbc.Button("N/A", color="secondary", size="sm")], "N/A", "N/A", "N/A"
    
    try:
        # Usar o primeiro adset disponível se não for especificado
        if adset_insights.adset_name.values.size > 0:
            adset = adset_insights.adset_name.values[0]
        else:
            return [dbc.Button("N/A", color="secondary", size="sm")], "N/A", "N/A", "N/A"

        # Filtrar status do adset
        filtered_status = adset_status[adset_status["name"] == adset]
        if filtered_status.empty:
            return [dbc.Button("UNKNOWN", color="warning", size="sm")], "N/A", "N/A", "N/A"
            
        status = filtered_status["status"].values[0]
        
        # Filtrar clicks e spend
        filtered_insights = adset_insights[adset_insights["adset_name"] == adset]
        if filtered_insights.empty:
            clicks = "N/A"
            spend = "N/A"
        else:
            clicks = filtered_insights["clicks"].values[0] if "clicks" in filtered_insights.columns else "N/A"
            spend = "R$ " + filtered_insights["spend"].values[0] if "spend" in filtered_insights.columns else "N/A"

        # Buscar conversões
        try:
            adset_id = filtered_status["id"].values[0]
            data_over_time = fb_api.get_data_over_time(adset_id)
            df_time = pd.DataFrame(data_over_time.get("data", []))
            conversions = df_time["conversion"].fillna(0).sum() if not df_time.empty and "conversion" in df_time.columns else 0
        except Exception as e:
            print(f"Erro ao processar dados de conversão: {e}")
            conversions = "N/A"

        # Formatar botão de status
        if status == "PAUSED":
            status_btn = dbc.Button("PAUSED", color="danger", size="sm")
        else: 
            status_btn = dbc.Button("ACTIVE", color="primary", size="sm")
            
        return [status_btn], clicks, spend, conversions
    except Exception as e:
        print(f"Erro no callback de status do adset: {e}")
        return [dbc.Button("ERROR", color="warning", size="sm")], "N/A", "N/A", "N/A"


@app.callback([
                Output("graph-line-adset", "figure"),
                Output("graph-bar-adset", "figure"),
            ], 
                [Input("dd-adset", "value"),
                Input("adset-kind", "value"),
                Input(ThemeChangerAIO.ids.radio("theme"), "value")]
            )
def render_page_content(adset, adset_kind, theme):
    # Verificação de valores vazios ou inválidos
    if adset is None or adset_status.empty:
        # Retornar gráficos vazios
        fig_empty = px.line(template=template_from_url(theme))
        fig_empty.update_layout(
            title="Sem dados disponíveis",
            xaxis_title="Data",
            yaxis_title="Valor"
        )
        return fig_empty, fig_empty
    
    try:
        adset_kind = adset_kind.lower() if adset_kind else "conversion"

        # Buscar dados do adset selecionado
        filtered_status = adset_status[adset_status["name"] == adset]
        if filtered_status.empty:
            # Retornar gráficos vazios se não encontrar o adset
            fig_empty = px.line(template=template_from_url(theme))
            fig_empty.update_layout(title="Conjunto de anúncios não encontrado")
            return fig_empty, fig_empty
            
        adset_id = filtered_status["id"].values[0]
        
        # Obter dados ao longo do tempo
        data_over_time = fb_api.get_data_over_time(adset_id)
        df_data = pd.DataFrame(data_over_time.get("data", []))
        
        # Verificar se há dados para exibir
        if df_data.empty:
            fig_empty = px.line(template=template_from_url(theme))
            fig_empty.update_layout(title="Sem dados disponíveis para este conjunto de anúncios")
            return fig_empty, fig_empty
            
        # Garantir que a coluna necessária existe
        if adset_kind not in df_data.columns:
            print(f"Coluna '{adset_kind}' não encontrada nos dados")
            # Usar uma coluna alternativa ou criar uma coluna de zeros
            if "clicks" in df_data.columns:
                df_data[adset_kind] = 0
            else:
                # Se nem clicks existir, provavelmente não há dados úteis
                fig_empty = px.line(template=template_from_url(theme))
                fig_empty.update_layout(title=f"Métrica '{adset_kind}' não disponível")
                return fig_empty, fig_empty
        
        # Converter clicks para numérico se existir
        if "clicks" in df_data.columns:
            df_data["clicks"] = pd.to_numeric(df_data["clicks"], errors="coerce").fillna(0)
        
        # Criar gráfico de linha
        fig_line = px.line(df_data, x="date_start", y=adset_kind, template=template_from_url(theme))
        fig_line.update_layout(
            margin=go.layout.Margin(l=0, r=0, t=30, b=0),
            title=f"{adset_kind.capitalize()} ao longo do tempo"
        )

        # Filtrar dados para o gráfico de barras
        df_ads = ads_insights[ads_insights["adset_name"] == adset]
        
        # Verificar se há dados de ads para este adset
        if df_ads.empty or adset_kind not in df_ads.columns:
            # Criar gráfico vazio
            fig_ads = px.bar(template=template_from_url(theme))
            fig_ads.update_layout(
                title="Sem dados de anúncios disponíveis",
                margin=go.layout.Margin(l=0, r=0, t=30, b=0)
            )
        else:
            # Criar gráfico de barras
            fig_ads = px.bar(df_ads, y=adset_kind, x="ad_name", template=template_from_url(theme))
            fig_ads.update_layout(
                margin=go.layout.Margin(l=0, r=0, t=30, b=0),
                title=f"{adset_kind.capitalize()} por anúncio"
            )
            
        return fig_line, fig_ads
        
    except Exception as e:
        print(f"Erro ao gerar gráficos: {e}")
        # Retornar gráficos de erro
        fig_error = px.line(template=template_from_url(theme))
        fig_error.update_layout(title=f"Erro ao processar dados: {str(e)[:50]}...")
        return fig_error, fig_error
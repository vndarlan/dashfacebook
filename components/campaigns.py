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
    
    adset_insights_data = fb_api.get_insights(ad_acc, "adset")
    adset_insights = pd.DataFrame(adset_insights_data.get("data", []))
    
    campaign_status_data = fb_api.get_campaigns_status(ad_acc)
    campaign_status = pd.DataFrame(campaign_status_data.get("data", []))
    
    # Verificar se temos dados válidos
    if campaign_insights.empty or campaign_status.empty:
        print("AVISO: Dados de campanhas vazios ou inválidos")
        # Criar dataframes vazios com colunas necessárias para evitar erros
        if campaign_insights.empty:
            campaign_insights = pd.DataFrame(columns=["campaign_name", "clicks", "spend"])
        if campaign_status.empty:
            campaign_status = pd.DataFrame(columns=["name", "id", "status"])
except Exception as e:
    print(f"Erro ao carregar dados iniciais: {e}")
    # Criar dataframes vazios para evitar quebra da aplicação
    campaign_insights = pd.DataFrame(columns=["campaign_name", "clicks", "spend"])
    adset_insights = pd.DataFrame(columns=["adset_name", "campaign_name"])
    campaign_status = pd.DataFrame(columns=["name", "id", "status"])

# Garantir que temos pelo menos um valor para o dropdown
if campaign_insights.empty or "campaign_name" not in campaign_insights.columns:
    campaign_insights = pd.DataFrame([{"campaign_name": "Sem dados disponíveis"}])

# Inicializar dados de exemplo para o gráfico de linha
# Este código só será usado se não houver dados reais
example_data_over_time = {
    "data": [
        {"date_start": "2023-01-01", "clicks": 10, "spend": 100, "conversion": 2, "cpc": 10, "cpm": 1000},
        {"date_start": "2023-01-02", "clicks": 15, "spend": 150, "conversion": 3, "cpc": 10, "cpm": 1000}
    ]
}

# =========  Layout  =========== #
layout = html.Div([
            dbc.Row([
                html.H3("Selecione a campanha:", style={"margin-top": "50px"}),
                dcc.Dropdown(
                    options=[{"label": i, "value": i} for i in campaign_insights.campaign_name.values],
                    value=campaign_insights.campaign_name.values[0] if not campaign_insights.empty else None,
                    id='dd-campaign'),
                ], style={"margin-bottom": "30px"}),

            dbc.Row([
                dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("Status"),
                            dbc.CardBody([
                            ], id="cb-status")
                        ], color="light"),

                    ], md=2),

                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Clicks"),
                            dbc.CardBody([
                                html.H4("", id="campaign-clicks", style={"color": "var(--bs-info)"}),
                            ])
                        ], color="light"),

                    ], md=2),

                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Spend"),
                            dbc.CardBody([
                                html.H4("", id="campaign-spend", style={"color": "var(--bs-primary)"}),
                            ])
                        ], color="light"),
                    ], md=2),
                
                dbc.Col([
                    dbc.Card([
                            dbc.CardHeader("Conversion"),
                            dbc.CardBody([
                                html.H5("", id="campaign-conversions", style={"color": "var(--bs-primary)"}),
                            ])
                        ], color="light"),
                    ], md=2),
            ]),

            dbc.Row([
                html.H4("Selecione o indicador:"),
                dcc.RadioItems(options=['Spend', 'CPC', 'CPM', 'Clicks', 'Conversion'], 
                            value='Conversion', id='campaign-kind', 
                            inputStyle={"margin-right": "5px", "margin-left": "20px"}),
                ], style={"margin-top": "50px"}),

            dbc.Row([            
                dbc.Col(dcc.Graph(id="graph-line-campaign"), md=6),
                dbc.Col(dcc.Graph(id="graph-bar-campaign"), md=6)
                ], style={"margin-top": "20px"}),
            ]) 

#========== Callbacks ================
@app.callback([
                Output("cb-status", "children"),
                Output("campaign-clicks", "children"),
                Output("campaign-spend", "children"),
                Output("campaign-conversions", "children"),
            ], 
                [Input("dd-campaign", "value"),
                ])
def render_page_content(campaign):
    # Verificar se existem dados e se o valor selecionado é válido
    if campaign is None or campaign_status.empty:
        return dbc.Button("N/A", color="secondary", size="sm"), "N/A", "N/A", "N/A"
    
    try:
        # Filtrar status da campanha - com tratamento para caso não seja encontrado
        filtered_status = campaign_status[campaign_status["name"] == campaign]
        if filtered_status.empty:
            return dbc.Button("UNKNOWN", color="warning", size="sm"), "N/A", "N/A", "N/A"
        
        status = filtered_status["status"].values[0]
        
        # Filtrar clicks e spend com tratamento para caso não seja encontrado
        filtered_insights = campaign_insights[campaign_insights["campaign_name"] == campaign]
        clicks = filtered_insights["clicks"].values[0] if not filtered_insights.empty and "clicks" in filtered_insights.columns else "N/A"
        spend = "R$ " + filtered_insights["spend"].values[0] if not filtered_insights.empty and "spend" in filtered_insights.columns else "N/A"

        # Buscar ID da campanha para get_data_over_time
        try:
            campaign_id = filtered_status["id"].values[0]
            data_over_time = fb_api.get_data_over_time(campaign_id)
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
            
        return status_btn, clicks, spend, conversions
    except Exception as e:
        print(f"Erro no callback de status: {e}")
        return dbc.Button("ERROR", color="warning", size="sm"), "N/A", "N/A", "N/A"
    

@app.callback([
                Output("graph-line-campaign", "figure"),
                Output("graph-bar-campaign", "figure"),
            ], 
                [Input("dd-campaign", "value"),
                Input("campaign-kind", "value"),
                Input(ThemeChangerAIO.ids.radio("theme"), "value")]
            )
def render_page_content(campaign, campaign_kind, theme):
    # Verificação de valores vazios ou inválidos
    if campaign is None or campaign_status.empty:
        # Retornar gráficos vazios
        fig_empty = px.line(template=template_from_url(theme))
        fig_empty.update_layout(
            title="Sem dados disponíveis",
            xaxis_title="Data",
            yaxis_title="Valor"
        )
        return fig_empty, fig_empty
    
    try:
        campaign_kind = campaign_kind.lower() if campaign_kind else "conversion"

        # Buscar dados da campanha selecionada
        filtered_status = campaign_status[campaign_status["name"] == campaign]
        if filtered_status.empty:
            # Retornar gráficos vazios se não encontrar a campanha
            fig_empty = px.line(template=template_from_url(theme))
            fig_empty.update_layout(title="Campanha não encontrada")
            return fig_empty, fig_empty
            
        campaign_id = filtered_status["id"].values[0]
        
        # Obter dados ao longo do tempo
        data_over_time = fb_api.get_data_over_time(campaign_id)
        df_data = pd.DataFrame(data_over_time.get("data", []))
        
        # Verificar se há dados para exibir
        if df_data.empty:
            fig_empty = px.line(template=template_from_url(theme))
            fig_empty.update_layout(title="Sem dados disponíveis para esta campanha")
            return fig_empty, fig_empty
            
        # Garantir que a coluna necessária existe
        if campaign_kind not in df_data.columns:
            print(f"Coluna '{campaign_kind}' não encontrada nos dados")
            # Usar uma coluna alternativa ou criar uma coluna de zeros
            if "clicks" in df_data.columns:
                df_data[campaign_kind] = 0
            else:
                # Se nem clicks existir, provavelmente não há dados úteis
                fig_empty = px.line(template=template_from_url(theme))
                fig_empty.update_layout(title=f"Métrica '{campaign_kind}' não disponível")
                return fig_empty, fig_empty
        
        # Converter clicks para numérico se existir
        if "clicks" in df_data.columns:
            df_data["clicks"] = pd.to_numeric(df_data["clicks"], errors="coerce").fillna(0)
        
        # Criar gráfico de linha
        fig_line = px.line(df_data, x="date_start", y=campaign_kind, template=template_from_url(theme))
        fig_line.update_layout(
            margin=go.layout.Margin(l=0, r=0, t=30, b=0),
            title=f"{campaign_kind.capitalize()} ao longo do tempo"
        )

        # Filtrar dados para o gráfico de barras
        df_adset = adset_insights[adset_insights["campaign_name"] == campaign]
        
        # Verificar se há dados de adsets para esta campanha
        if df_adset.empty or campaign_kind not in df_adset.columns:
            # Criar gráfico vazio
            fig_adsets = px.bar(template=template_from_url(theme))
            fig_adsets.update_layout(
                title="Sem dados de conjuntos de anúncios disponíveis",
                margin=go.layout.Margin(l=0, r=0, t=30, b=0)
            )
        else:
            # Criar gráfico de barras
            fig_adsets = px.bar(df_adset, y=campaign_kind, x="adset_name" if "adset_name" in df_adset.columns else "adset_id", 
                               template=template_from_url(theme))
            fig_adsets.update_layout(
                margin=go.layout.Margin(l=0, r=0, t=30, b=0),
                title=f"{campaign_kind.capitalize()} por conjunto de anúncios"
            )
            
        return fig_line, fig_adsets
        
    except Exception as e:
        print(f"Erro ao gerar gráficos: {e}")
        # Retornar gráficos de erro
        fig_error = px.line(template=template_from_url(theme))
        fig_error.update_layout(title=f"Erro ao processar dados: {str(e)[:50]}...")
        return fig_error, fig_error
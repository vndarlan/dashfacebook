import requests
import json
import pandas as pd

class GraphAPI:
    def __init__(self, ad_acc, fb_api):
        self.base_url = "https://graph.facebook.com/v22.0/"  # Versão atualizada da API
        self.api_fields = ["spend", "cpc", "cpm", "objective", "adset_name", 
                "adset_id", "clicks", "campaign_name", "campaign_id", 
                "conversions", "frequency", "conversion_values", "ad_name", "ad_id"]
        self.token = "&access_token=" + fb_api

    def get_insights(self, ad_acc, level="campaign"):
        url = self.base_url + "act_" + str(ad_acc)
        url += "/insights?level=" + level
        url += "&fields=" + ",".join(self.api_fields)

        response = requests.get(url + self.token)
        data = json.loads(response.content.decode("utf-8"))
        
        # Verificar se há erro na resposta
        if 'error' in data:
            print(f"Erro da API do Facebook: {data['error']}")
            return data
            
        if 'data' in data:
            for i in data["data"]:
                if "conversions" in i:
                    i["conversion"] = float(i["conversions"][0]["value"])
        return data

    def get_campaigns_status(self, ad_acc):
        url = self.base_url + "act_" + str(ad_acc)
        url += "/campaigns?fields=name,status,adsets{name, id}"
        response = requests.get(url + self.token)
        return json.loads(response.content.decode("utf-8"))

    def get_adset_status(self, ad_acc):
        url = self.base_url + "act_" + str(ad_acc)
        url += "/adsets?fields=name,status,id"
        response = requests.get(url + self.token)
        return json.loads(response.content.decode("utf-8"))

    def get_data_over_time(self, campaign):
        # Adicionar verificação para determinar o formato correto do ID da campanha
        if isinstance(campaign, int) or (isinstance(campaign, str) and campaign.isdigit()):
            url = self.base_url + "campaign_" + str(campaign)  # Usar prefixo campaign_
        else:
            url = self.base_url + str(campaign)
            
        url += "/insights?fields="+ ",".join(self.api_fields)
        url += "&date_preset=last_30d&time_increment=1"
        
        print(f"URL da API: {url}[TOKEN OCULTO]")  # Debug da URL
        
        response = requests.get(url + self.token)
        print(f"Código de status da API: {response.status_code}")
        
        data = json.loads(response.content.decode("utf-8"))
        
        # Debug da resposta
        print("Resposta da API:", json.dumps(data, indent=2, ensure_ascii=False)[:1000] + "...")
        
        # Verificar erros
        if 'error' in data:
            print(f"Erro da API do Facebook: {data['error']}")
            return data
        
        # Processar dados apenas se a chave 'data' existir
        if 'data' in data:
            for i in data["data"]:
                if "conversions" in i:
                    i["conversion"] = float(i["conversions"][0]["value"])
        else:
            print("A chave 'data' não foi encontrada na resposta da API")
            
        return data


if __name__ == "__main__":
    fb_api = open("tokens/fb_token").read()
    ad_acc = "991384508583089"

    self = GraphAPI(ad_acc, fb_api)

    # Teste inicial para verificar a conta
    print("Testando get_insights:")
    insights = self.get_insights(ad_acc)
    if 'data' in insights:
        print(f"Insights obtidos com sucesso. {len(insights['data'])} registros encontrados.")
    
    print("\nTestando get_campaigns_status:")
    campaigns = self.get_campaigns_status(ad_acc)
    if 'data' in campaigns:
        print(f"Campanhas obtidas com sucesso. {len(campaigns['data'])} campanhas encontradas.")
        # Listar IDs de campanhas válidas
        if len(campaigns['data']) > 0:
            print("IDs de campanhas disponíveis:")
            for campaign in campaigns['data']:
                print(f"- {campaign['id']} ({campaign['name']})")
    
    # Tentar com formato correto de ID
    campaign_id = None
    if 'data' in campaigns and len(campaigns['data']) > 0:
        campaign_id = campaigns['data'][0]['id']
        print(f"\nTestando get_data_over_time com o ID da primeira campanha: {campaign_id}")
        self.get_data_over_time(campaign_id)
    
    # Tentativa original
    print("\nTestando get_data_over_time com ID numérico:")
    self.get_data_over_time(991384508583089)
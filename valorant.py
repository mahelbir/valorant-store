import json
from urllib.parse import urlsplit, parse_qs
import cfscrape
import os.path
import time


class Valorant:

    def __init__(self, username, password, region="eu", path=""):
        self.auth_file = path + "riot_auth_" + username + ".json"
        self.region = region
        self.username = username
        self.password = password

    def riot_auth(self):
        if os.path.isfile(self.auth_file) and time.time() - os.path.getmtime(self.auth_file) < 3600:
            file = open(self.auth_file)
            auth = json.load(file)
            file.close()
            return auth
        else:
            auth_scraper = cfscrape.create_scraper()
            cookie_json = {
                "client_id": "play-valorant-web-prod",
                "nonce": "1",
                "redirect_uri": "https://playvalorant.com/opt_in",
                "response_type": "token id_token"
            }
            cookie_dict = json.loads(
                auth_scraper.post('https://auth.riotgames.com/api/v1/authorization', json=cookie_json).text)
            if "type" in cookie_dict and cookie_dict["type"] == "auth":
                auth_json = {
                    "type": "auth",
                    "username": self.username,
                    "password": self.password,
                    "remember": True,
                    "language": "en_US"
                }
                auth_dict = json.loads(
                    auth_scraper.put('https://auth.riotgames.com/api/v1/authorization', json=auth_json).text)
                if "response" in auth_dict and "parameters" in auth_dict["response"]:
                    query = urlsplit(auth_dict["response"]["parameters"]["uri"]).fragment
                    params = dict(parse_qs(query))
                    access_token = params["access_token"][0]
                    headers = {"Authorization": "Bearer " + access_token}
                    entitlements_dict = json.loads(
                        auth_scraper.post('https://entitlements.auth.riotgames.com/api/token/v1', json={},
                                          headers=headers).text)
                    entitlements_token = entitlements_dict["entitlements_token"]
                    player_dict = json.loads(
                        auth_scraper.get('https://auth.riotgames.com/userinfo', json={}, headers=headers).text)
                    auth = {
                        "access_token": access_token,
                        "entitlements_token": entitlements_token,
                        "puuid": player_dict["sub"]
                    }
                    f = open(self.auth_file, "w")
                    f.write(json.dumps(auth))
                    f.close()
                    return auth

    def store(self):
        auth = self.riot_auth()
        if auth:
            store_scraper = cfscrape.create_scraper()
            headers = {
                "X-Riot-Entitlements-JWT": auth["entitlements_token"],
                "Authorization": "Bearer " + auth["access_token"],
            }
            store_dict = json.loads(
                store_scraper.get('https://pd.' + self.region + '.a.pvp.net/store/v2/storefront/' + auth["puuid"], json={},
                                  headers=headers).text)
            return store_dict

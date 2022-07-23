import pickle
import cfscrape
from json import loads as json_decode
from os import path
from time import time


class ValorantStore:
    _auth = {}

    def __init__(self, username: str, password: str, region: str = "eu", auth_path: str = ""):
        self._username = username
        self._password = password
        self._region = region
        self._auth_path = auth_path
        self._auth_file = f"{self._auth_path}riot_auth_{self._username}.pickle"
        if path.isfile(self._auth_file) and time() - path.getmtime(self._auth_file) < 3600:
            with open(self._auth_file, "rb") as auth:
                self._auth = pickle.load(auth)
        else:
            self.__login()
        self.__headers = {
            "X-Riot-Entitlements-JWT": self._auth["entitlements_token"],
            "Authorization": "Bearer " + self._auth["access_token"],
        }
        self.__scraper = cfscrape.create_scraper()

    @staticmethod
    def __get_access_token(url: str) -> str:
        return [i.split("=")[-1] for i in url.split("#", 1)[-1].split("&") if i.startswith("access_token" + "=")][0]

    @staticmethod
    def __skin_image(skin: str) -> str:
        return f"https://media.valorant-api.com/weaponskinlevels/{skin}/displayicon.png"

    @staticmethod
    def skin_info(skin: str) -> dict:
        response = cfscrape.create_scraper().get(f"https://valorant-api.com/v1/weapons/skinlevels/{skin}")
        try:
            return json_decode(response.text)["data"]
        except Exception:
            raise ValorantStoreException("skin info", "request", response)

    @property
    def auth(self):
        return self._auth

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def auth_path(self):
        return self._auth_path

    @property
    def auth_file(self):
        return self._auth_file

    def __login(self):
        scraper = cfscrape.create_scraper()
        cookie_file = f"{self._auth_path}riot_cookie_{self._username}.pickle"
        if path.isfile(cookie_file):
            with open(cookie_file, "rb") as cookies:
                scraper.cookies = pickle.load(cookies)
            login_response = scraper.get(
                "https://auth.riotgames.com/authorize?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in&client_id"
                "=play-valorant-web-prod&response_type=token%20id_token&nonce=1", allow_redirects=False)
            if login_response.status_code != 303 or login_response.headers.get("location").find("access_token") == -1:
                raise ValorantStoreException("login", "request", login_response)
            else:
                self._auth["access_token"] = self.__get_access_token(login_response.headers.get("location"))
        else:
            cookie_response = scraper.post("https://auth.riotgames.com/api/v1/authorization", json={
                "client_id": "play-valorant-web-prod",
                "nonce": "1",
                "redirect_uri": "https://playvalorant.com/opt_in",
                "response_type": "token id_token"
            })
            cookie = json_decode(cookie_response.text)
            if "type" not in cookie:
                raise ValorantStoreException("cookie", "request", cookie_response)
            elif cookie["type"] != "auth":
                raise ValorantStoreException("cookie", "type", cookie_response)
            else:
                login_response = scraper.put("https://auth.riotgames.com/api/v1/authorization", json={
                    "type": "auth",
                    "username": self._username,
                    "password": self._password,
                    "remember": True,
                    "language": "en_US"
                })
                with open(cookie_file, "wb") as cookies:
                    pickle.dump(scraper.cookies, cookies)
            try:
                login = json_decode(login_response.text)
                self._auth["access_token"] = self.__get_access_token(login["response"]["parameters"]["uri"])
            except Exception:
                raise ValorantStoreException("login", "request", login_response)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self._auth["access_token"]
        }
        entitlements_response = scraper.post("https://entitlements.auth.riotgames.com/api/token/v1", headers=headers)
        try:
            entitlements = json_decode(entitlements_response.text)
            self._auth["entitlements_token"] = entitlements["entitlements_token"]
        except Exception:
            raise ValorantStoreException("entitlements", "request", entitlements_response)
        user_response = scraper.get("https://auth.riotgames.com/userinfo", headers=headers)
        try:
            entitlements = json_decode(user_response.text)
            self._auth["player"] = entitlements["sub"]
        except Exception:
            raise ValorantStoreException("user", "request", user_response)
        with open(self._auth_file, "wb") as auth:
            pickle.dump(self._auth, auth)

    def wallet(self, format_response: bool = True) -> dict:
        response = self.__scraper.get(f"https://pd.{self._region}.a.pvp.net/store/v1/wallet/{self._auth['player']}",
                                      headers=self.__headers)
        try:
            wallet = json_decode(response.text)
            if format_response:
                return {
                    "valorant_points": wallet["Balances"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"],
                    "radianite_points": wallet["Balances"]["e59aa87c-4cbf-517a-5983-6e81511be9b7"],
                    "free_agents": wallet["Balances"]["f08d4ae3-939c-4576-ab26-09ce1f23bb37"]
                }
            else:
                return wallet
        except Exception:
            raise ValorantStoreException("wallet", "request", response)

    def store(self, format_response: bool = True) -> dict:
        response = self.__scraper.get(f"https://pd.{self._region}.a.pvp.net/store/v2/storefront/{self._auth['player']}",
                                      headers=self.__headers)
        try:
            store = json_decode(response.text)
            if format_response:
                offers = []
                for offer in store["SkinsPanelLayout"]["SingleItemOffers"]:
                    offers.append({
                        "id": offer,
                        "image": self.__skin_image(offer)
                    })
                data = {
                    "daily_offers": {
                        "remaining_duration": store["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"],
                        "data": offers
                    }
                }
                if "BonusStore" in store:
                    bonuses = []
                    for bonus in store["BonusStore"]["BonusStoreOffers"]:
                        bonuses.append({
                            "id": bonus["Offer"]["OfferID"],
                            "image": self.__skin_image(bonus["Offer"]["OfferID"]),
                            "original_cost": bonus["Offer"]["Cost"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"],
                            "discount_cost": bonus["DiscountCosts"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"],
                            "discount_percent": bonus["DiscountPercent"]
                        })
                    data["night_market"] = {
                        "remaining_duration": store["BonusStore"]["BonusStoreRemainingDurationInSeconds"],
                        "data": bonuses
                    }
                return data
            else:
                return store
        except Exception:
            raise ValorantStoreException("store", "request", response)


class ValorantStoreException(Exception):
    def __init__(self, exception_type: str, exception_message: str, response=None) -> None:
        if response is not None:
            print(response.status_code)
            print(response.headers)
            print(response.text)
        super().__init__(f"{exception_type.title()}: {exception_message.capitalize()} error")

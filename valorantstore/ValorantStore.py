import pickle
import cfscrape
from json import loads as json_decode
from os import path, getcwd, sep, remove
from time import time
from valorantstore.ValorantStoreException import ValorantStoreException


class ValorantStore:
    __auth = {}

    def __init__(self, username: str, password: str, region: str = "eu", auth_path: str = ""):
        self.__username = username.lower()
        self.__password = password
        self.__region = region
        self.__auth_path = auth_path.rstrip('/').rstrip('\\') if auth_path else getcwd()
        self.__auth_file = f"{self.__auth_path + sep}riot_auth_{self.__username}.pickle"
        self.__cookie_file = f"{self.__auth_path + sep}riot_cookie_{self.__username}.pickle"
        if path.isfile(self.__auth_file) and time() - path.getmtime(self.__auth_file) < 3600:
            with open(self.__auth_file, "rb") as auth:
                self.__auth = pickle.load(auth)
        else:
            self.__login()
        self.headers = {
            "X-Riot-Entitlements-JWT": self.__auth["entitlements_token"],
            "Authorization": "Bearer " + self.__auth["access_token"],
        }
        self.scraper = cfscrape.create_scraper()

    @staticmethod
    def __get_access_token(url: str) -> str:
        return [i.split("=")[-1] for i in url.split("#", 1)[-1].split("&") if i.startswith("access_token" + "=")][0]

    @staticmethod
    def __skin_image(skin: str) -> str:
        return f"https://media.valorant-api.com/weaponskinlevels/{skin}/displayicon.png"

    @staticmethod
    def __buddy_image(buddy: str) -> str:
        return f"https://media.valorant-api.com/buddylevels/{buddy}/displayicon.png"

    @staticmethod
    def __card_image(card: str) -> str:
        return f"https://media.valorant-api.com/playercards/{card}/largeart.png"

    @staticmethod
    def __spray_image(spray: str) -> str:
        return f"https://media.valorant-api.com/sprays/{spray}/fulltransparenticon.png"

    @staticmethod
    def __bundle_image(bundle: str) -> str:
        return f"https://media.valorant-api.com/bundles/{bundle}/displayicon.png"

    @staticmethod
    def skin_info(skin: str) -> dict:
        response = cfscrape.create_scraper().get(f"https://valorant-api.com/v1/weapons/skinlevels/{skin}")
        try:
            return json_decode(response.text)["data"]
        except Exception:
            raise ValorantStoreException("skin_info", "request", response)

    @staticmethod
    def buddy_info(buddy: str) -> dict:
        response = cfscrape.create_scraper().get(f"https://valorant-api.com/v1/buddies/levels/{buddy}")
        try:
            return json_decode(response.text)["data"]
        except Exception:
            raise ValorantStoreException("buddy_info", "request", response)

    @staticmethod
    def card_info(card: str) -> dict:
        response = cfscrape.create_scraper().get(f"https://valorant-api.com/v1/playercards/{card}")
        try:
            return json_decode(response.text)["data"]
        except Exception:
            raise ValorantStoreException("card_info", "request", response)

    @staticmethod
    def spray_info(spray: str) -> dict:
        response = cfscrape.create_scraper().get(f"https://valorant-api.com/v1/sprays/{spray}")
        try:
            return json_decode(response.text)["data"]
        except Exception:
            raise ValorantStoreException("spray_info", "request", response)

    @staticmethod
    def bundle_info(bundle: str) -> dict:
        response = cfscrape.create_scraper().get(f"https://valorant-api.com/v1/bundles/{bundle}")
        try:
            return json_decode(response.text)["data"]
        except Exception:
            raise ValorantStoreException("skin info", "request", response)

    @property
    def region(self) -> str:
        return self.__region

    @property
    def username(self) -> str:
        return self.__username

    @property
    def auth(self) -> dict:
        return self.__auth

    @property
    def auth_path(self) -> str:
        return self.__auth_path

    @property
    def auth_file(self) -> str:
        return self.__auth_file

    @property
    def cookie_file(self) -> str:
        return self.__cookie_file

    def __login(self):
        scraper = cfscrape.create_scraper()
        if path.isfile(self.__cookie_file):
            with open(self.__cookie_file, "rb") as cookies:
                scraper.cookies = pickle.load(cookies)
            login_response = scraper.get(
                "https://auth.riotgames.com/authorize?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in&client_id"
                "=play-valorant-web-prod&response_type=token%20id_token&nonce=1", allow_redirects=False)
            if login_response.status_code != 303 or login_response.headers.get("location").find("access_token") == -1:
                remove(self.__cookie_file)
                self.__login()
            else:
                self.__auth["access_token"] = self.__get_access_token(login_response.headers.get("location"))
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
                    "username": self.__username,
                    "password": self.__password,
                    "remember": True,
                    "language": "en_US"
                })
                with open(self.__cookie_file, "wb") as cookies:
                    pickle.dump(scraper.cookies, cookies)
            try:
                login = json_decode(login_response.text)
            except Exception:
                raise ValorantStoreException("access", "request", login_response)
            if "type" in login and login["type"] == "multifactor":
                raise ValorantStoreException("access", "multifactor", login_response)
            try:
                self.__auth["access_token"] = self.__get_access_token(login["response"]["parameters"]["uri"])
            except Exception:
                raise ValorantStoreException("access", "token", login_response)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.__auth["access_token"]
        }
        entitlements_response = scraper.post("https://entitlements.auth.riotgames.com/api/token/v1", headers=headers)
        try:
            entitlements = json_decode(entitlements_response.text)
            self.__auth["entitlements_token"] = entitlements["entitlements_token"]
        except Exception:
            raise ValorantStoreException("entitlements", "request", entitlements_response)
        player_response = scraper.get("https://auth.riotgames.com/userinfo", headers=headers)
        try:
            player = json_decode(player_response.text)
            self.__auth["player"] = player["sub"]
        except Exception:
            raise ValorantStoreException("player", "request", player_response)
        with open(self.__auth_file, "wb") as auth:
            pickle.dump(self.__auth, auth)

    def wallet(self, format_response: bool = True) -> dict:
        response = self.scraper.get(f"https://pd.{self.__region}.a.pvp.net/store/v1/wallet/{self.__auth['player']}",
                                    headers=self.headers)
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
        response = self.scraper.get(
            f"https://pd.{self.__region}.a.pvp.net/store/v2/storefront/{self.__auth['player']}",
            headers=self.headers)
        try:
            store = json_decode(response.text)
            if format_response:
                offers = []
                for offer in store["SkinsPanelLayout"]["SingleItemOffers"]:
                    offers.append({
                        "id": offer,
                        "type": "skin",
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
                            "type": "skin",
                            "image": self.__skin_image(bonus["Offer"]["OfferID"]),
                            "original_cost": bonus["Offer"]["Cost"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"],
                            "discount_cost": bonus["DiscountCosts"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"],
                            "discount_percent": bonus["DiscountPercent"]
                        })
                    data["night_market"] = {
                        "remaining_duration": store["BonusStore"]["BonusStoreRemainingDurationInSeconds"],
                        "data": bonuses
                    }

                if "FeaturedBundle" in store:
                    bundles = []
                    for bundle in store["FeaturedBundle"]["Bundles"]:
                        items = []
                        for item in bundle["Items"]:
                            add = {
                                "id": item["Item"]["ItemID"],
                                "amount": item["Item"]["Amount"]
                            }
                            if item["Item"]["ItemTypeID"] == "e7c63390-eda7-46e0-bb7a-a6abdacd2433":
                                add["type"] = "skin"
                                add["image"] = self.__skin_image(item["Item"]["ItemID"])
                            elif item["Item"]["ItemTypeID"] == "dd3bf334-87f3-40bd-b043-682a57a8dc3a":
                                add["type"] = "buddy"
                                add["image"] = self.__buddy_image(item["Item"]["ItemID"])
                            elif item["Item"]["ItemTypeID"] == "3f296c07-64c3-494c-923b-fe692a4fa1bd":
                                add["type"] = "card"
                                add["image"] = self.__card_image(item["Item"]["ItemID"])
                            elif item["Item"]["ItemTypeID"] == "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475":
                                add["type"] = "spray"
                                add["image"] = self.__spray_image(item["Item"]["ItemID"])
                            items.append(add)
                        bundles.append({
                            "id": bundle["DataAssetID"],
                            "image": self.__bundle_image(bundle["DataAssetID"]),
                            "items": items,
                            "remaining_duration": bundle["DurationRemainingInSeconds"]
                        })
                        data["bundles"] = {
                            "remaining_duration": store["FeaturedBundle"]["BundleRemainingDurationInSeconds"],
                            "data": bundles
                        }
                return data
            else:
                return store
        except Exception:
            raise ValorantStoreException("store", "request", response)

    def session(self) -> dict:
        response = self.scraper.get(
            f"https://glz-{self.__region}-1.{self.__region}.a.pvp.net/session/v1/sessions/{self.__auth['player']}",
            headers=self.headers)
        try:
            return json_decode(response.text)
        except Exception:
            raise ValorantStoreException("session", "request", response)

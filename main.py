import os
import eel
from selenium import webdriver
from selenium.webdriver import Chrome, ChromeOptions
import time
import pandas as pd
import datetime
import requests
import math
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

INSTA_URL = "https://www.instagram.com/"
GOOGLE_MAP_URL = "https://www.google.com/maps/search/{keyword}"

class HEADER():
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36}"
    API_HEADRS = {
        'Content-Type': 'application/json; charset=utf-8',
    }

LOG_FILE_PATH = "./logs/log_{datetime}.log"
EXP_CSV_PATH="./results/exp_list_{search_keyword}_{datetime}.csv"
log_file_path=LOG_FILE_PATH.format(datetime=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))


### Chromeを起動する関数
def set_driver(driver_path, headless_flg=False):
    # Chromeドライバーの読み込み
    options = webdriver.ChromeOptions()

    # ヘッドレスモード（画面非表示モード）をの設定
    if headless_flg == True:
        options.add_argument('--headless')

    # 起動オプションの設定
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36')
    # options.add_argument('log-level=3')
    options.add_argument('--ignore-certifica-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--incognito')          # シークレットモードの設定を付与

    # ChromeのWebDriverオブジェクトを作成する。
    return webdriver.Chrome(ChromeDriverManager().install(), options=options)

### ログファイルおよびコンソール出力
def log(text):
    now=datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    logStr = '[%s: %s] %s' % ('log',now , text)
    # ログ出力
    with open(log_file_path, 'a', encoding='utf-8_sig') as f:
        f.write(logStr + '\n')
    print(logStr)

def find_table_target_word(th_elms, td_elms, target:str):
    # tableのthからtargetの文字列を探し一致する行のtdを返す
    for th_elm,td_elm in zip(th_elms,td_elms):
        if th_elm.text == target:
            return td_elm.text

def chs(user_id:str, driver:WebDriver):
    '''
    user_id:対象のインスタアカウントのID(urlの{user_id}の部分　https://www.instagram.com/{user_id}/)
    '''
    # ユーザー情報にアクセス
    driver.get(f"https://www.instagram.com/{user_id}/?__a=1")
    time.sleep(5)
    # データを取得
    try:
        res = json.loads(driver.find_element_by_tag_name('body').text)
        if not res["graphql"]["user"]["is_business_account"]:
            log(f"businessアカウントではありません:{user_id}")
            return None,None,None,None,None
        try:
            address = json.loads(res["graphql"]["user"]["business_address_json"])
            zip_code = address['zip_code']
            street_address = address["street_address"]
        except Exception as e:
            log(e)
            address = None
            zip_code = None
            street_address = None
        store_name = res["graphql"]["user"]["full_name"]
        phone_number = res["graphql"]["user"]["business_phone_number"]
        url = res["graphql"]["user"]["connected_fb_page"]
        store_url = res["graphql"]["user"]["external_url"]
        # addressが取得できない場合はGoogleMyBusinessのデータを取得
        if address == None:
            if store_url != None:
                print("google scrape")
                keyword = store_url.replace(r"/",r"%2F")
                store_name, zip_code, street_address, phone_number, _ = scrape_google_my_business(keyword, driver)

        print(store_name, phone_number, zip_code, street_address, store_url)
        return store_name, phone_number, zip_code, street_address, store_url
    except Exception as e:
        log(f"json load error:{user_id} / {e}")
        return None,None,None,None,None


def scrape_google_my_business(keyword:str, driver:WebDriver):
    log(f"scrape gloogle:{keyword}")
    driver.get(GOOGLE_MAP_URL.format(keyword=keyword))
    time.sleep(5)
    # 結果が複数件の場合は、一番上の店舗をクリックする
    if driver.current_url.find("https://www.google.com/maps/search") >= 0:
        link_elms = driver.find_elements_by_css_selector("[role='region'] a")
        if len(link_elms) == 0:
            log(f"google scrape not found:{keyword}")
            return None,None,None,None,None 
        link = link_elms[0].get_attribute("href")
        driver.get(link)
        time.sleep(5)
        
    store_name_elms = driver.find_elements_by_css_selector(".x3AX1-LfntMc-header-title-title.gm2-headline-5")
    address_elms = driver.find_elements_by_css_selector(".QSFF4-text.gm2-body-2")
    url_elms = driver.find_elements_by_css_selector(".rogA2c.HY5zDd")
    phone_number_elms = driver.find_elements_by_css_selector("[data-tooltip='電話番号をコピーします']")
    name = store_name_elms[0].text if len(store_name_elms) >= 1 else None
    _address = address_elms[0].text if len(address_elms) >= 1 else None
    phone_number = phone_number_elms[0].get_attribute("aria-label").replace("電話番号: ","").strip() if len(phone_number_elms) >= 1 else None
    url = url_elms[0].text if len(url_elms) >= 1 else None
    if _address != None and _address.find("〒") >= 0:
        zip_code = _address[1:9]
        address = _address[10:]
    else:
        zip_code = None
        address = _address
        
    log(f"google scrape result: {name} | {zip_code} | {address} | {url} | {phone_number}")
    log("finish scrape")
    
    return name, zip_code, address, phone_number, url

def get_abs_path(filepath:str):
    return os.path.join(os.getcwd(),filepath)

def read_cred():
    cred_df = pd.read_csv(get_abs_path("cred.csv"), delimiter=",")
    username=list(cred_df["username"])[0]
    password=list(cred_df["password"])[0]
    page_number=list(cred_df["page_number"])[0]
    token=list(cred_df["token"])[0]
    admin_user_id=str(list(cred_df["admin_user_id"])[0])
    return username,password,page_number,token,admin_user_id

def exists_hashtag(hashtag_name:str):
    try:
        df = pd.read_csv(get_abs_path("hashtag.csv"), encoding="utf-8_sig", 
                         index_col=0, delimiter=",", dtype='object')
        return str(df.loc[hashtag_name][0])
    except Exception as e:
        log(f"not exists hashtag: {hashtag_name} / {e}")
        return None
    
def insert_hashtag_csv(hashtag_name:str, hashtag_id:str):
    df = pd.DataFrame({"hashtag_name": [hashtag_name],
                    "hashtag_id": [hashtag_id]})
    df.to_csv("hashtag.csv", mode='a', encoding="utf-8_sig", header=False, index=False,line_terminator='\n')
    
    
# 処理の流れ
# ハッシュタグ名からIDを取得→APIだと３０個までなので（スクレイピングJSONで実施）、一度取得した情報はキャッシュする
# https://www.instagram.com/explore/tags/{tag名}/?__a=1
# hashtag_id = data["id"]
# APIを実行して投稿一覧を取得(recent_media)
# 投稿からowner情報を取得（スレイピングJSON）
# graphql["owner"]["location"]["address_json"] にデータがあれば、これを取得　→　完了
# ない場合は、userAPIを実行してwebsite情報を取得
# business_discovery["website"]
# GoogleMapAPIを実行してwebsiteから住所情報を取得


def login(driver:WebDriver, username:str, password:str):
    url = "https://www.instagram.com/"
    driver.get(url)
    time.sleep(3)
    driver.find_element_by_name("username").send_keys(username)
    driver.find_element_by_name("password").send_keys(password)
    time.sleep(3)
    driver.find_element_by_css_selector('[type="submit"]').click()
    time.sleep(3)
    

def fetch_hashtag_id(hashtag_name:str):
    # ハッシュタグが取得済か確認
    hashtag_id = exists_hashtag(hashtag_name)
    if hashtag_id:
        log("exists hashtag: {hashtag_name} / {hashtag_id}")
        return hashtag_id
        
    # 取得済ではない場合は取得
    try:
        #token = "EAACtPmeEWB0BAHpBAhqWirgJSZCNZChc6ny0JzKKeZBZB5dYJwVCAGSOpwQAM8E1mkWxdNklCVyfd4VM7Go3qIZBMjYLqrrtZBYlpYR14RMCYcE31vIqjsnbUQkOvTzpHPSsf6fIzChUZCj9dPEGOZBmIfrF0ZAZBdnx2AVD32ZBK4KkOwAFDkJ0J9R"
        #admin_user_id = "17841448974344841"
        username,password,page_number,token,admin_user_id = read_cred()
        if not(token and admin_user_id):
            log(f"instagram api token or admin_user_id not found error")
            return None
        
        # API実行
        url = r"https://graph.facebook.com/ig_hashtag_search/?q=###HASHTAG_NAME###&user_id=###ADMIN_USER_ID###&fields=id,name&access_token=###TOKEN###"
        url = url.replace("###ADMIN_USER_ID###", admin_user_id)\
                .replace("###HASHTAG_NAME###", hashtag_name)\
                .replace('###TOKEN###', token)
        res = requests.get(url)
        if not(300 > res.status_code >= 200):
            print(f"hashtatag_name not found:{hashtag_name}")
            return None
        res_dict = res.json()
        if not res_dict.get("data"):
            return None
        hashtag_id = res_dict["data"][0]["id"]
        insert_hashtag_csv(hashtag_name=hashtag_name, hashtag_id=hashtag_id)
        return hashtag_id
    except Exception as e:
        log(f"fetch_hashtag_id error: {hashtag_name} / {e}")
        return None
    
    
def fetch_user_info(driver:WebDriver, url:str):
    # 取得済ではない場合は取得
    res = {}
    try:
        driver.get(url + "?__a=1")
        time.sleep(5)
        try:
            data_dict = json.loads(driver.find_element_by_tag_name('body').text)
            res["username"] = data_dict["graphql"]["shortcode_media"]["owner"]["username"]
            res["address"] = json.loads(data_dict["graphql"]["shortcode_media"]["location"]["address_json"])
            return res
        except Exception as e:
            log(f"address not found / {e}")
            return res
    except Exception as e:
        log(f"fetch_user_info error: {url} / {e}")
        return res
    
def search_media_list_by_hashtag_id(hashtag_id:str, media_limit:int, max_page_num:int):
    #token = "EAAHBqeP3YCYBAASomG8OaO3y3kvkTIaeMMhvYoFMNdVAGxDds0yMz1sscOyXlXW4lvH99FbaKxDZBk3WAxsE9hte435hEmBspVoOZCd1xJ5ZCZBsL3o2oQt3l2CzB6ihxmxBwjMyxZB2bsTqPIYZAZCUNoea3XjsLO3C0VEaMgJl7kN5HTCxVCc"
    #admin_user_id = "17841407715810110"
    username,password,page_number,token,admin_user_id = read_cred()
    if not(token and admin_user_id):
        log(f"instagram api token or admin_user_id not found error")
        return False
    
    # API実行
    url = r"https://graph.facebook.com/###HASHTAG_ID###/top_media?user_id=###ADMIN_USER_ID###&fields=id,media_product_type,media_type,media_url,permalink,like_count,comments_count,caption,timestamp,children{id,media_url}&limit=###MEDIA_LIMIT###&access_token=###TOKEN###"
    url = url.replace("###ADMIN_USER_ID###", admin_user_id)\
             .replace("###HASHTAG_ID###", hashtag_id)\
             .replace("###MEDIA_LIMIT###", str(media_limit))\
             .replace('###TOKEN###', token)
    
    media_list = []
    for page in range(max_page_num):
        res = requests.get(url)
        if not(300 > res.status_code >= 200):
            print(f"business hashtag_id not found(search_medi_list_by_hashtag_id):{hashtag_id}")
            return None
        res_json = res.json()
        if not res_json.get("data"):
            return media_list
        media_list.extend(res_json["data"])
        if res_json.get("pading") and res_json["pading"].get("next"):
            url = res_json["pading"]["next"]
        
    return media_list

def fetch_user_website(username:str):
    #token = "EAAHBqeP3YCYBAASomG8OaO3y3kvkTIaeMMhvYoFMNdVAGxDds0yMz1sscOyXlXW4lvH99FbaKxDZBk3WAxsE9hte435hEmBspVoOZCd1xJ5ZCZBsL3o2oQt3l2CzB6ihxmxBwjMyxZB2bsTqPIYZAZCUNoea3XjsLO3C0VEaMgJl7kN5HTCxVCc"
    #admin_user_id = "17841407715810110"
    _,password,page_number,token,admin_user_id = read_cred()
    
    # API実行
    url = r"https://graph.facebook.com/###ADMIN_USER_ID###/?fields=business_discovery.username(###TARGET_USERNAME###){username,website}&access_token=###TOKEN###"
    url = url.replace("###ADMIN_USER_ID###", str(admin_user_id))\
             .replace("###TARGET_USERNAME###", username)\
             .replace('###TOKEN###', token)
    res = requests.get(url)
    if not(300 > res.status_code >= 200):
        print(f"business user_id not found(fetch_user_website):{username}")
        return None
    
    try:
        print(res.json()["business_discovery"])
        return res.json()["business_discovery"]["website"]
    except Exception as e:
        log(f"website not fount:{username}")
        return None
    
def search_place_by_google(query:str):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id,photos,formatted_address,name,rating,opening_hours,geometry",
        "key": "AIzaSyDL3PVwkIaEeYKKKOz1x2w_SOMY5jzxQOY"
    }
    place = {
        "address": None,
        "phone_number": None,
        "store_name": None
    }
    res = requests.get(url, params=params)
    if not(300 > res.status_code >= 200):
        log(f"google api error address not found: {query}")
        return place
    
    try:
        res_dict = res.json()
        place_id = res_dict["candidates"][0]["place_id"]
        try:
            place["address"] = res_dict["candidates"][0]["formatted_address"].replace("日本、","")
        except:
            pass
        try:
            place["phone_number"] = fetch_phone_number(place_id)
        except:
            pass
        place["store_name"] = res_dict["candidates"][0]["name"]
        return place
    except Exception as e:
        log(f"search address error:{query} / {e}")
        return  place
    
def fetch_phone_number(place_id:str):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,rating,formatted_phone_number",
        "key": "AIzaSyDL3PVwkIaEeYKKKOz1x2w_SOMY5jzxQOY"
    }
    res = requests.get(url, params=params)
    if not(300 > res.status_code >= 200):
        log(f"google api error place not found: {place_id}")
        return None
    try:
        res_dict = res.json()
        return res_dict["result"]["formatted_phone_number"]
    except Exception as e:
        log(f"find place detail error: {place_id}")
        return None

def read_fetched_usernames():
    try:
        df = pd.read_csv("fetched_usernames.csv")
        return list(df["username"])
    except:
        return []
    
def update_fetched_usernames(usernames:list):
    pd.DataFrame({
        "username": usernames
    }).to_csv("fetched_usernames.csv")
    
def main(search_keyword):
    media_limit=50
    df=pd.DataFrame()
    try:
        log("処理開始")
        log("検索キーワード:{}".format(search_keyword))
        
        # インスタにログイン
        username,password,page_number,token,admin_user_id = read_cred()
        driver = set_driver("chromedriver.exe", False)
        login(driver, username, password)
        
        # ハッシュタグIDを取得
        hashtag_id = fetch_hashtag_id(search_keyword)
        # ここがおかしい
        if hashtag_id == None:
            log("hashtag_id not found")
            return 0,"hashtag is is not found"
        
        # 投稿一覧を取得
        try:
            media_list = search_media_list_by_hashtag_id(hashtag_id=hashtag_id, media_limit=page_number, max_page_num=math.ceil(media_limit/50))
        except Exception as e:
            print("a")

        if not media_list:
            log(f"投稿が取得できませんでした:{hashtag_id}")
            return 0,"投稿が取得できませんでした"
        
        now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        fetched_usernames = read_fetched_usernames()
        for media in media_list:
            # 投稿URLからユーザーのWebsiteを取得
            user = fetch_user_info(driver, media["permalink"])
            username = user['username']
            if username in fetched_usernames:
                log(f"already read skip: {username}")
                continue
            fetched_usernames.append(username) # 同一ユーザーはスキップするために保持
            website = fetch_user_website(username)
            if website == None:
                log(f"website not found:{username}")
                address = None
                phone_number = None
                store_name = None
                #continue
            else:
                # 店舗情報を取得
                place = search_place_by_google(website)
                # 出力用データ作成
                address = place.get("address")
                phone_number = place.get("phone_number")
                store_name = place.get("store_name")
            
            # 出力用データ作成
            #address = place.get("address")
            #phone_number = place.get("phone_number")
            #store_name = place.get("store_name")
            df = df.append(
                {
                    "username": username,
                    "店舗名": store_name,
                    "電話番号": phone_number,
                    "住所": address,
                    "店舗URL": website,
                    "InstagramURL": INSTA_URL + username
                },
                ignore_index=True)
            # デバックしやすいように毎回出力する
            df.to_csv(EXP_CSV_PATH.format(search_keyword=search_keyword,datetime=now), encoding="utf-8-sig")
            
        update_fetched_usernames(fetched_usernames)
        
        driver.quit()
    except Exception as e:
        import traceback
        print(traceback.print_exc())
        log(f"処理が失敗しました / {e}")
        return len(df),f"処理が失敗しました / {e}"
    
    log(f"処理が成功しました / 検索キーワード:{search_keyword} / 出力件数:{len(df)}件")
    return len(df),"処理が成功しました"
   
# 直接起動された場合はmain()を起動(モジュールとして呼び出された場合は起動しないようにするため)
if __name__ == "__main__":
   main("")

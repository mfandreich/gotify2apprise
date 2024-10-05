from dotenv import load_dotenv
import os
import requests
import json
import websocket
import yaml
import apprise

load_dotenv()

host = os.environ["GOTIFY_HOST"]
token = os.environ["GOTIFY_TOKEN"]

configPath = os.environ["CONF_FILE"] if "CONF_FILE" in os.environ else '/etc/gotify2apprise/config.yaml'

with open(configPath, 'r') as f:
  configData = yaml.safe_load(f)

def getGotifyApps():
    headers = { 'X-Gotify-Key': str(token) }
    try:
        response = requests.get("http://" + str(host) + "/application", headers=headers)

        if response.status_code != 200:
            return {}

        result = {}
        for app in response.json():
            result[app["id"]] = app

        return result
    except Exception as e:
        print(e)

def getUrls(appId, priority):

    apps = getGotifyApps()

    if not appId in apps:
        return []

    app = apps[appId]

    if not "applications" in configData:
        return []

    result =[]

    for confApp in configData["applications"]:
        if not "tokens" in confApp or not "receivers" in confApp:
            continue

        tokens = confApp["tokens"]
        if "all" in tokens or app["token"] in tokens:
            receivers = confApp["receivers"]
            for receiver in receivers:
                try:
                    minPriority = 0
                    if "minPriority" in receiver:
                        minPriority = receiver["minPriority"]

                    if minPriority > priority:
                        continue

                    if "urls" in receiver:
                        result += receiver["urls"]
                except Exception as e:
                    print(e)

    return result

def onNotify(ws, msg):
    print("msg: ", msg)

    try:
        msgData = json.loads(msg)
        appId = msgData["appid"]
        priority = msgData["priority"]

        urls = getUrls(appId, priority)

        if len(urls) <= 0:
            print("No receiver urls found for this message, skip")
            return

        appriseInstance = apprise.Apprise()

        for url in urls:
            appriseInstance.add(url)

        type = apprise.NotifyType.INFO

        if priority >= 4 and priority < 8:
            type = apprise.NotifyType.WARNING
        elif priority >= 8:
            type = apprise.NotifyType.FAILURE


        appriseInstance.notify(title=msgData['title'], body=msgData['message'], notify_type=type)

    except Exception as e:
        print(e)

def onError(ws, err):
    print(err)

def onClose(ws, code, msg):
    print("Connection closed with message '" + str(msg) + "' and code " + str(code))

def onOpen(ws):
    print("Gotify websocket connected")

applications = getGotifyApps()

getUrls(3, 2)
getUrls(3, 4)
getUrls(2, 10)
getUrls(2, 2)
getUrls(3, 10)
getUrls(3, 0)

if __name__ == "__main__":
    print("Gotify To Apprise start...")
    wsApp = websocket.WebSocketApp("ws://" + str(host) + "/stream", header={"X-Gotify-Key": str(token)},
                                   on_open=onOpen,
                                   on_message=onNotify,
                                   on_error=onError,
                                   on_close=onClose)

    wsApp.run_forever()
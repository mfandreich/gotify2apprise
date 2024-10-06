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

defaultTitleTemplate = os.environ["TITLE_TEMPLATE"] if "TITLE_TEMPLATE" in os.environ else "$title"
defaultMessageTemplate = os.environ["MESSAGE_TEMPLATE"] if "MESSAGE_TEMPLATE" in os.environ else "$message"

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

def isCorrectPriority(priority, receiver):
    if "priorities" in receiver:
        prioritiesList = []

        for priority in receiver["priorities"]:
            if isinstance(priority, int):
                prioritiesList.append(priority)
            if isinstance(priority, str):
                match priority:
                    case "info":
                        prioritiesList += [0, 1, 2, 3]
                    case "warn":
                        prioritiesList += [4, 5, 6, 7]
                    case "crit":
                        prioritiesList += [8, 9, 10]

        if not priority in prioritiesList:
            return False

    if "minPriority" in receiver:
        minPriority = receiver["minPriority"]

        minPriorityValue = 0

        if isinstance(minPriority, int):
            minPriorityValue = minPriority
        if isinstance(minPriority, str):
            match minPriority:
                case "info":
                    minPriorityValue = 0
                case "warn":
                    minPriorityValue = 4
                case "crit":
                    minPriorityValue = 8

        if minPriorityValue > priority:
            return False

    return True

def getReceivers(appId, priority):

    apps = getGotifyApps()

    if not appId in apps:
        return []

    app = apps[appId]

    if not "applications" in configData:
        return []

    result = []

    for confApp in configData["applications"]:
        if not "tokens" in confApp or not "receivers" in confApp:
            continue

        tokens = confApp["tokens"]
        if "all" in tokens or app["token"] in tokens:
            receivers = confApp["receivers"]
            for receiver in receivers:
                try:
                    if isCorrectPriority(priority, receiver) and "urls" in receiver:
                        result.append(receiver)
                except Exception as e:
                    print(e)

    return result

def getPriorityString(priority):
    if priority < 4:
        return "info"
    if priority < 8:
        return "warn"
    return "crit"


def getTemplateText(msgData, receiver, template):
    result = template

    priority = msgData["priority"]
    appId = msgData["appid"]
    title = msgData['title']
    message = msgData['message']
    priorityStr = getPriorityString(priority)

    result = result.replace("$priorityStr", priorityStr)
    result = result.replace("$priority", str(priority))
    result = result.replace("$appid", str(appId))
    result = result.replace("$title", title)
    result = result.replace("$message", message)

    return result

def getTitle(msgData, receiver):
    template = defaultTitleTemplate
    if "titleTemplate" in receiver:
        try:
            template = receiver["titleTemplate"]
        except Exception as e:
            print(e)

    return getTemplateText(msgData, receiver, template)

def getMessage(msgData, receiver):
    template = defaultMessageTemplate
    if "messageTemplate" in receiver:
        try:
            template = receiver["messageTemplate"]
        except Exception as e:
            print(e)

    return getTemplateText(msgData, receiver, template)

def getNotifyType(priority):
    type = apprise.NotifyType.INFO

    if priority >= 4 and priority < 8:
        type = apprise.NotifyType.WARNING
    elif priority >= 8:
        type = apprise.NotifyType.FAILURE

    return type


def onNotify(ws, msg):
    print("msg: ", msg)

    try:
        msgData = json.loads(msg)
        appId = msgData["appid"]
        priority = msgData["priority"]

        receivers = getReceivers(appId, priority)

        if len(receivers) <= 0:
            print("No receivers found for this message, skip")
            return

        for receiver in receivers:
            appriseInstance = apprise.Apprise()

            for url in receiver["urls"]:
                try:
                    appriseInstance.add(url)

                    appriseInstance.notify(title=getTitle(msgData, receiver),
                                           body=getMessage(msgData, receiver),
                                           notify_type=getNotifyType(priority))
                except Exception as e:
                    print(e)

    except Exception as e:
        print(e)

def onError(ws, err):
    print(err)

def onClose(ws, code, msg):
    print("Connection closed with message '" + str(msg) + "' and code " + str(code))

def onOpen(ws):
    print("Gotify websocket connected")

applications = getGotifyApps()

if __name__ == "__main__":
    print("Gotify To Apprise start...")
    wsApp = websocket.WebSocketApp("ws://" + str(host) + "/stream", header={"X-Gotify-Key": str(token)},
                                   on_open=onOpen,
                                   on_message=onNotify,
                                   on_error=onError,
                                   on_close=onClose)

    wsApp.run_forever()
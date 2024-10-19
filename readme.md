# gotify2apprise

> This is a utility for personal use. Use it at your own risk.

This utility reads messages from gotify in real time and forwards them according to the configuration to other services. [Apprise](https://github.com/caronc/apprise) is used for sending.

## Config

The configuration uses a yaml file. You can configure sending for individual applications registered in Gotify. Also, filtering by the minimum message priority is possible.

By default `/etc/gotify2apprise/config.yaml` used as config file. But its possible set custom path with `CONF_FILE` env variable

Example config:

```yaml
applications: #root of config, mus be array of
  - tokens:
    - all #if all presented we use this receivers for all messages
    receivers: # settings for receivers
      - urls:
        - mailto://myemail:mypass@gmail.com
        - pover://USER_KEY@TOKEN    
      - urls:
        - tgram://MY_BOT_TOKEN
        minPriority: 4 #send message only for "warning" and greater
  - tokens:
    - GOTIFY_APP_TOKEN1 # receivers in this block process only
    - GOTIFY_APP_TOKEN2 # messages from this two apps
    receivers:
      - urls:
        - discord://WEBHOOK_ID/WEBHOOK_TOKEN
        minPriority: info
      - urls:
        - slack://TokenA/TokenB/TokenC/
        priorities: #also you can determine specific list of priorities for your receiver
        - info
        - 9
        - 10
```

You can use any receiver for any application token in any combination. You can also send messages to Gotify via gotify://hostname/token url but be careful not to go sending in an infinite cycle.

For priorities settings you can use key words:

- info - if used in minPriority its equal 0. For priorities its translate to values 0, 1, 2 and 3
- warn - if used in minPriority its equal 4. For priorities its translate to values 4, 5, 6 and 7
- crit - if used in minPriority its equal 8. For priorities its translate to values 8, 9 and 10

## Config fields

|Field|Is required|Description|
|-|-|-|
|applications|true|Root field. Array of all processed applications|
|applications[].tokens|true|List of Gotify app tokens which included in this processed application. If contain `all` value, this record process all Gotify apps|
|applications[].receivers|true|List of receivers which process incoming messages for target Gotify apps|
|applications[].receivers[].urls|true|List of Apprise urls. More info about supported urls can be found [here](https://github.com/caronc/apprise)|
|applications[].receivers[].titleTemplate|false|Template string for Title. Default value: `$title`|
|applications[].receivers[].messageTemplate|false|Template string for Title. Default value: `$message`|
|applications[].receivers[].minPriority|false|Minimal message priority witch must be process by this receiver. Valid values is number or `info`, `warn` and `crit` strings|
|applications[].receivers[].priorities|false|List of message priorities witch must be process by this receiver. Valid values is number or `info`, `warn` and `crit` strings|

## Templates

The message title and message body are all created with a templates. You can define your own default templates with ENV variables: `TITLE_TEMPLATE` and `MESSAGE_TEMPLATE`. If this variables not presented `$title` and `$message` strings will be used.

Template variables:

- `$title` - title of message
- `$message` - body of message
- `$appid` - id of Gotify app which send this message
- `$priority` - priority of message (number)
- `$priorityStr` - priority string mapped to values `info`, `warn` and `crit`

## Installation with Docker Compose

```
  gotify2apprise:
    image: mfandreich/gotify2apprise:latest
    container_name: gotify2apprise
    restart: unless-stopped
    environment:
      - GOTIFY_HOST=myhost[:port]
      - GOTIFY_TOKEN=gotify_client_token
    volumes:
      - ./gotify2apprise/config.yaml:/etc/gotify2apprise/config.yaml
```

> Attention! You don’t need to specify http:// in the hostname, but the program works on http and ws access

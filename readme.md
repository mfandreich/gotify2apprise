# gotify2apprise

> This is a utility for personal use. Use it at your own risk.

This utility reads messages from gotify in real time and forwards them according to the configuration to other services. [Apprise](https://github.com/caronc/apprise) is used for sending.

The configuration uses a yaml file. You can configure sending for individual applications registered in Gotify. Also, filtering by the minimum message priority is possible.

Example config:

```yaml
applications: #root of config, mus be array of
  - tokens:
    - all #if all presented we use this receivers for all messages
    receivers: # settings for receivers
      - urls:
        - mailto://myemail:mypass@gmail.com
        - pover://USER_KEY@TOKEN
    receivers:
      - urls:
        - tgram://MY_BOT_TOKEN
        minPriority: 4 #send message only for "warning@ and greater
  - tokens:
    - GOTIFY_APP_TOKEN1 # receivers in this block process only
    - GOTIFY_APP_TOKEN2 # messages fro this two apps
    receivers:
      - urls:
        - discord://WEBHOOK_ID/WEBHOOK_TOKEN
        minPriority: 8
```

You can use any receiver for any application token in any combination. You can also send messages to Gotify, but be careful not to go sending in an infinite cycle.
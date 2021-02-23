# Gru 
Gru: a simple web terminal written in Python and JavaScript, which contains these features:

* Web terminal support by Xterm.js
* Copy on selecting text
* Upload/Download directly to server
* Preventing shell shortcut(Ctrl+W) to close browser tab accidently
* Reversed SSH tunnel management

Minion: a ssh client to establish reversed SSH tunnel to Gru

# Environment
Name | Description | Default
--- | --- | --- 
NW_ETCD_PASSWORD | Etcd password | 
NW_IFACE | IP accessible by other nodes for inter-host communication | 
NW_DNS_ENDPOINTS | Consul DNS endpoint | http://localhost:8500
NW_LOOP | Netswatch max loop(seconds) | 600 
NW_LOG_LEVEL | Logging level | info

## Misc
* Go 1.14
* Python 3.7


# Third-party Libraries

* [Tornado](https://github.com/tornadoweb/tornado)
* [Paramiko](https://github.com/paramiko/paramiko)
* [Xterm.js](https://github.com/xtermjs/xterm.js/)
* [NES.css](https://github.com/nostalgic-css/NES.css/)

# Screenshots
![screenshot-0](pics/screenshot-0.png)
![screenshot-1](pics/screenshot-1.png)
![screenshot-2](pics/screenshot-2.png)



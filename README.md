# certbot-dnspod
### Install & Requirements
```
pip install certbot
pip install tencentcloud-sdk-python-common
pip install tencentcloud-sdk-python-dnspod
pip install git+https://github.com/Looomo/certbot-dnspod.git
```

### Usage
##### If you want to use config file:
```
# cat /etc/letsencrypt/tencentcloud.ini
certbot_dnspod_secret_id = "your_tencent_id"
certbot_dnspod_secret_key = "your_tencent_key"
# obtain  with certbot
certbot certonly \
    -a certbot-dnspod \ # use  certbot-dnspod plugin
    --certbot-dnspod-credentials /etc/letsencrypt/tencentcloud.ini 
    -d example.com
```

##### If you DO NOT want to use config file:
```
rm /etc/letsencrypt/tencentcloud.ini
export TENCENTCLOUD_SECRET_ID="your_tencent_id"
export TENCENTCLOUD_SECRET_KEY="your_tencent_key"
# obtain  with certbot
certbot certonly \
    -a certbot-dnspod \ # use  certbot-dnspod plugin
    -d example.com
```
### Acknowledge
Thanks to [certbot-dns-tencentcloud](https://github.com/Frefreak/certbot-dns-tencentcloud/tree/master).
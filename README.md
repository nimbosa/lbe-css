# Light Block Explorer Enhanced (LBEE)

- __Author__: LBEE - hellcatz 
- __Author__: LBE - Ondrej Sika <https://github.com/ondrejsika/lbe>
- __License__: MIT <http://ondrejsika.com/license/mit.txt>


### Abstract

Basic block explorer for every forks of Bitcoin (Namecoin, Litecoin, ..), which has same RPC interface.

### Xcoind requirements

LBE requires this rpc calls:

- getbestblockhash
- getblock
- getrawtransaction
- decoderawtransaction


### Install

    git clone git@github.com:ondrejsika/lbe.git
    cd lbe
    virtualenv .env
    source .env/bin/activate
    pip install -r requirements.txt


### Usage

Show help

    python lbe.py -h

## Example Zcash Testnet Run Script

/home/user/start.sh

    #!/bin/bash
    source .env/bin/activate
    python lbe.py :: 8000 localhost 18232 username password --coin TAZ --n-last-blocks 100
    
## Example Systemd Unit Script
This requires the coin daemon to also be setup as a service.

/etc/systemd/system/lbe-block-explorer.service    
    
    [Unit]
    Wants=network-online.target
    After=network.target network-online.target
    Description=LBEE Block Explorer Service
    
    [Service]
    Environment=HOME=/home/user
    Environment=PWD=/home/user/lbe
    Environment=PATH=/home/user/bin:/home/user/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    Environment=USER=user
    User=user
    Group=user
    WorkingDirectory=/home/user/lbe
    ExecStart=/home/user/lbe/start.sh
    Restart=always
    
    [Install]
    WantedBy=multi-user.target

sudo systemctl start lbe-block-explorer.service

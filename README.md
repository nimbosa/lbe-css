# Light Block Explorer (LBE)

- __Author__: Ondrej Sika <ondrej@ondrejsika.com>
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
    
Example Zcash Testnet

    python lbe.py :: 8000 localhost 18232 username password --coin TAZ --n-last-blocks 100

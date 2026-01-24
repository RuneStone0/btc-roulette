# This require Microsoft C++ Redistributable
# https://www.microsoft.com/en-us/download/details.aspx?id=52685

from electrumx.lib.server import Server
from electrumx.lib.coins import Bitcoin
from electrumx.lib.hash import address_to_scripthash

# Connect to an ElectrumX server
server = Server("electrumx.example.com", 50002)
server.connect()

# The address you want to look up
address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

# Convert the address to a scripthash
scripthash = address_to_scripthash(address, Bitcoin)

# Get the balance
balance = server.db.get_balance(scripthash)

# Convert balance from satoshis to BTC
balance_btc = Bitcoin.decimal_value(balance)

print("Balance:", balance_btc)
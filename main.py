from mnemonic import Mnemonic
import requests
import bip32utils
import sys

test_address_with_funds = "1EzwoHtiXB4iFwedPr49iywjZn2nnekhoj"


def lookup_balance(address):
	url = f"https://blockchain.info/q/addressbalance/{address}"
	rsp = requests.get(url)
	data = rsp.json()
	return data
#lookup_balance("1EzwoHtiXB4iFwedPr49iywjZn2nnekhoj")

def lookup_balance2(address):
	url = "https://blockchainzakutynskyv1.p.rapidapi.com/getAddressBalance"

	payload = "address=%3CREQUIRED%3E"
	headers = {
		"content-type": "application/x-www-form-urlencoded",
		"X-RapidAPI-Host": "BlockchainzakutynskyV1.p.rapidapi.com",
		"X-RapidAPI-Key": "4025db3b52msh95fce055d90fd93p114399jsnf81482861d72"
	}
	try:
		response = requests.request("POST", url, data=payload, headers=headers, timeout=3)
		print(response.text)
	except Exception as e:
		print(e)
#lookup_balance2("1EzwoHtiXB4iFwedPr49iywjZn2nnekhoj")

def gen_seed():
	mnemon = Mnemonic('english')
	words = mnemon.generate(256)
	seed = mnemon.to_seed(words)
	return (seed, words)

def gen_keys(seed):
	root_key = bip32utils.BIP32Key.fromEntropy(seed[0])
	root_address = root_key.Address()
	root_public_hex = root_key.PublicKey().hex()
	root_private_wif = root_key.WalletImportFormat()
	out = {
		"seed": seed[1],
		"address": root_address,
		"public": root_public_hex,
		"private": root_private_wif
	}
	#print(out)
	return out

def roulette():
	#balance = lookup_balance(test_address_with_funds)
	#print(balance)
	while(True):
		seed = gen_seed()
		keys = gen_keys(seed)
		print(keys)
		addr = keys["address"]
		balance = lookup_balance(addr)
		print(balance)
		print(type(balance))
		if balance > 0:
			sys.exit()


roulette()




#print(words)
#mnemon.check(words)
#seed = mnemon.to_seed(words)


"""
seed = mnemon.to_seed(b'lucky labor rally law toss orange weasel try surge meadow type crumble proud slide century')
print(f'BIP39 Seed: {seed.hex()}\n')
"""


"""
child_key = root_key.ChildKey(0).ChildKey(0)
child_address = child_key.Address()
child_public_hex = child_key.PublicKey().hex()
child_private_wif = child_key.WalletImportFormat()
print('Child key m/0/0:')
print(f'\tAddress: {child_address}')
print(f'\tPublic : {child_public_hex}')
print(f'\tPrivate: {child_private_wif}\n')
"""



# BTC Roulette
This project is a simple BTC "routlette" that generates seed phrases (private keys) and check their balance. If a balance is found, the private key is printed to the console and you have won the lottery.

This project is for educational purposes only. Do not use this project to steal BTC.

We use the following components to build this project:
- Umbrel Node running a Bitcoin Core full node
- ElectrumX Server installed on the Umbrel Node
- Python script to generate private keys and check their balance using the ElectrumX Server

# Run the lottery
```bash
python .\main.py lottery
```

# Other commands
```bash
python .\electrum_cli.py --server vps.hsmiths.com blockchain.address.get_balance 1PuJjnF476W3zXfVYmJfGnouzFDAXakkL4
python .\main.py bip --seed "dynamic proof rival secret warrior prepare miss notable merit script gap judge"
python .\main.py balance bc1qcme5u6v8a4ss855jsvgae59z20f05sky494qpa
python .\electrum_cli.py --server VPS.hsmiths.com --port s blockchain.getblockchaininfo
```

# FAQ
The script return: `ERROR:root:An error occurred: 'int' object is not subscriptable` when I run it. What does it mean?

This error occurs when the script is unable to connect to the ElectrumX Server. This usually happens if:
   * The ElectrumX Server is not running
   * The ElectrumX Server address or port is incorrect
   * The ElectrumX Server is still syncing with the Bitcoin Core full node (this can take a few hours)

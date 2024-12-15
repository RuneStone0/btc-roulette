import hashlib
import base58
from typing import Dict
import mnemonic
import bitcoin
import time
from queue import Queue
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor
from logging_config import log
import bip39 as bip39_module

mnemo = mnemonic.Mnemonic("english")

class Bip39AddressGenerator:
    def __init__(self, seed_phrase: str = None):
        """Initialize BIP39 address generator with optional seed phrase.
        
        Args:
            seed_phrase (str, optional): BIP39 seed phrase. If None, generates new one.
        """
        if seed_phrase:
            if not mnemo.check(seed_phrase):
                raise ValueError("Invalid BIP39 seed phrase")
            self.seed_phrase = seed_phrase
        else:
            self.seed_phrase = mnemo.generate(strength=128)
            
        self.seed = mnemo.to_seed(self.seed_phrase)

    def compute_scripthash(self, address):
        # Decode the address using Base58Check
        decoded = base58.b58decode_check(address)
        pubkeyhash = decoded[1:]  # Remove version byte

        # Build the P2PKH locking script
        script = b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'

        # Compute the SHA256 hash and reverse it
        sha256_hash = hashlib.sha256(script).digest()
        reversed_hash = sha256_hash[::-1]  # Reverse endianness

        return reversed_hash.hex()

    def generate_address(self, account: int = 0, change: int = 0, address_index: int = 0) -> Dict[str, str]:
        """Generate Bitcoin address from seed using BIP44 derivation path.
        
        Args:
            account (int): Account number (default: 0)
            change (int): Change address (0 for external, 1 for internal)
            address_index (int): Address index
            
        Returns:
            Dict containing seed phrase and generated address
        """
        # Generate the master key
        master_key = bitcoin.bip32_master_key(self.seed)
        
        # Derive the path m/44'/0'/account'/change/address_index
        derived_key = master_key
        for level in [44 + 0x80000000, 0 + 0x80000000, account + 0x80000000, change, address_index]:
            derived_key = bitcoin.bip32_ckd(derived_key, level)
        
        # Get the public key and generate the address
        pub_key = bitcoin.bip32_extract_key(derived_key)
        address = bitcoin.pubkey_to_address(pub_key)
        
        return {
            "seed_phrase": self.seed_phrase,
            "address": address,
            "derivation_path": f"m/44'/0'/{account}'{change}/{address_index}",
            "scripthash": self.compute_scripthash(address)
        }

class AddressQueue:
    """
    Address generator with a queue to store pre-generated addresses.
    """
    def __init__(self, queue_size=100):
        self.queue = Queue(maxsize=queue_size)
        self.stop_event = Event()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.logger = log
        self._start_generating()

    def _start_generating(self):
        for _ in range(4):  # Start 4 threads for address generation
            self.executor.submit(self._address_generator)

    def _address_generator(self):
        while not self.stop_event.is_set():
            try:
                if not self.queue.full():
                    address = bip39_module.Bip39AddressGenerator().generate_address()
                    self.queue.put(address)
                else:
                    time.sleep(0.1)  # Avoid busy waiting
            except Exception as e:
                self.logger.error(f"Error generating address: {e}")
                time.sleep(1)

    def get_address(self, timeout=1):
        """Get next pre-generated address"""
        return self.queue.get(timeout=timeout)

    def stop(self):
        """Stop address generation"""
        log.info("Stopping address generation")
        self.stop_event.set()
        self.executor.shutdown(wait=False)
        # Forcefully terminate any remaining threads
        for thread in self.executor._threads:
            if thread.is_alive():
                thread.join(timeout=1)

if __name__ == "__main__":
    generator = Bip39AddressGenerator()
    address = generator.generate_address()
    print(f"Generated Bitcoin address: {address}")

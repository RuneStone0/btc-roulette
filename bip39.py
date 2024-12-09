from typing import Dict
import mnemonic
import bitcoin

class Bip39AddressGenerator:
    def __init__(self, seed_phrase: str = None):
        """Initialize BIP39 address generator with optional seed phrase.
        
        Args:
            seed_phrase (str, optional): BIP39 seed phrase. If None, generates new one.
        """
        self.mnemo = mnemonic.Mnemonic("english")
        
        if seed_phrase:
            if not self.mnemo.check(seed_phrase):
                raise ValueError("Invalid BIP39 seed phrase")
            self.seed_phrase = seed_phrase
        else:
            self.seed_phrase = self.mnemo.generate(strength=128)
            
        self.seed = self.mnemo.to_seed(self.seed_phrase)

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
        }

if __name__ == "__main__":
    generator = Bip39AddressGenerator()
    address = generator.generate_address()
    print(f"Generated Bitcoin address: {address}")

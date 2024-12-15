import fire
import bip39 as bip39_module
from electrum_query import ElectrumQuery
import logging
import time
from functools import wraps
import random
import signal
import sys
import os

def retry_with_backoff(retries=5, backoff_in_seconds=1):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt == retries:
                        raise e
                    
                    # Calculate sleep time with exponential backoff and jitter
                    sleep_time = (backoff_in_seconds * 2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Attempt {attempt} failed: {str(e)}. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
            return None
        return wrapper
    return decorator

class CLI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.stop_event = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def bip(self, seed: str = None):
        """Generate Bitcoin addresses using BIP39
        
        Args:
            seed (str, optional): Specific BIP39 seed phrase to use. 
                                       If not provided, generates a random one.
        """
        bip = bip39_module.Bip39AddressGenerator(seed_phrase=seed)
        
        return bip.generate_address()

    def _validate_balance(self, address, balance, seed):
        if balance is None:
            self.logger.warning(f"Address: {address}, balance: None (error occurred), seed: {seed}")
            return
            
        confirmed = balance.get('confirmed', 0)
        unconfirmed = balance.get('unconfirmed', 0)
        log_msg = f"Address: {address}, balance: {confirmed}, seed: {seed}"
        
        if confirmed > 0 or unconfirmed > 0:
            self.logger.info(f"🎯 FOUND FUNDED ADDRESS!")
            self.logger.info(log_msg)
            import sys
            sys.exit(0)
        else:
            self.logger.info(log_msg)

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    def _check_balance(self, client, address, seed):
        balance = client.get_address_balance(address)
        if balance is None:
            raise Exception("Failed to get balance")
        return balance

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        self.logger.info("\n⚠️  Received interrupt signal. Shutting down gracefully...")
        self.stop_event = True

    def report_funds(self, address, balance, seed=None, is_test=False):
        """Report found funds in a consistent format"""
        confirmed = balance.get('confirmed', 0)
        unconfirmed = balance.get('unconfirmed', 0)
        
        if confirmed > 0 or unconfirmed > 0:
            marker = "✅" if is_test else "🎯"
            message = "Test successful!" if is_test else "FOUND FUNDED ADDRESS!"
            
            self.logger.info(
                f"{marker} {message}\n"
                f"  Address: {address}\n"
                f"  Balance: {confirmed} (confirmed) + {unconfirmed} (unconfirmed)"
                + (f"\n  Seed: {seed}" if seed else "\n  Seed: mock seed mock seed mock seed mock seed mock seed mock seed")
            )
            return True
        return False

    def lottery(self, batch_size: int = 100, server: str = "umbrel.lan", port: int = 50003):
        """Search for funded Bitcoin addresses using Electrum server"""
        self.logger.info(f"Connecting to Electrum server {server}:{port}...")
        client = ElectrumQuery(server_url=server, port=port, protocol="t")
        self.logger.info("✓ Connected")

        total_attempts = 0
        last_batch_time = time.time()
        
        try:
            while not self.stop_event:
                try:
                    result = bip39_module.Bip39AddressGenerator().generate_address()
                    balance = client.get_address_balance(result["address"])
                    total_attempts += 1
                    
                    if balance and self.report_funds(result["address"], balance, result["seed_phrase"]):
                        return

                    if total_attempts % 100 == 0:
                        now = time.time()
                        batch_elapsed = now - last_batch_time
                        rate = 100 / batch_elapsed if batch_elapsed > 0 else 0
                        self.logger.info(
                            f"[{server}:{port}] "
                            f"Rate: {rate:.2f}/s | "
                            f"Time: {batch_elapsed:.1f}s | "
                            f"Total: {total_attempts} addresses"
                        )
                        last_batch_time = now

                except Exception as e:
                    self.logger.error(f"❌ Error: {str(e)}")
                    time.sleep(5)
                    client = ElectrumQuery(server_url=server, port=port, protocol="t")

        finally:
            client.close()

    def balance(self, address: str, server: str = "VPS.hsmiths.com", port: str = "50002"):
        """Check balance of a specific Bitcoin address.
        
        Args:
            address: Bitcoin address to check
            server: Electrum server hostname
            port: Electrum server port
        """
        self.logger.info(f"Connecting to Electrum server {server}:{port}")
        client = ElectrumQuery(server_url=server, port=port)
        
        try:
            balance = client.get_address_balance(address)
            self._validate_balance(address, balance, None)
            return balance
        finally:
            client.close()

    def test(self, num_addresses: int = 1000):
        """Test balance checking with random addresses and a known funded address
        
        Args:
            num_addresses: Number of random addresses to check before the funded one
        """
        self.logger.info(f"Starting test: Will check {num_addresses} random addresses")
        
        client = ElectrumQuery(server_url="umbrel.lan", port=50003, protocol="t")
        start_time = time.time()
        last_batch_time = start_time
        
        try:
            # First check random addresses
            for i in range(num_addresses):
                result = bip39_module.Bip39AddressGenerator().generate_address()
                client.get_address_balance(result["address"])
                
                if i > 0 and i % 100 == 0:
                    now = time.time()
                    batch_elapsed = now - last_batch_time
                    rate = 100 / batch_elapsed if batch_elapsed > 0 else 0
                    last_batch_time = now
                    self.logger.info(f"[{rate:.2f}/s per 100 addresses] Processed {i} addresses")

            # Finally check the known funded address
            self.logger.info("Testing known funded address...")
            funded_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
            client.get_address_balance(funded_address)
            
        finally:
            client.close()

def main():
    fire.Fire(CLI)

if __name__ == "__main__":
    main()
import fire
import bip39 as bip39_module
from electrum_query import ElectrumQuery
from balance_provider import BalanceProvider
import logging
import time
from functools import wraps
import random
import signal
import cProfile
import pstats
from datetime import datetime
from logging_config import log
from bip39 import AddressQueue
from statistics import BruteForceStatistics
import sys
import os
from asyncio.exceptions import InvalidStateError

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
                    log.warning(f"Attempt {attempt} failed: {str(e)}. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
            return None
        return wrapper
    return decorator

def profile(output_file=None):
    def inner(func):
        def wrapper(*args, **kwargs):
            if '--profiling' in sys.argv:
                profiler = cProfile.Profile()
                try:
                    return profiler.runcall(func, *args, **kwargs)
                finally:
                    if output_file:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        stats_file = f"{output_file}_{timestamp}.stats"
                        profiler.dump_stats(stats_file)
                        # Print top 10 time-consuming calls
                        stats = pstats.Stats(stats_file)
                        print("\n🔍 Performance Profile (Top 10 calls by time):")
                        stats.strip_dirs().sort_stats('cumulative').print_stats(10)
            else:
                return func(*args, **kwargs)
        return wrapper
    return inner

class CLI:
    def __init__(self):
        self.logger = log
        self.stop_event = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self.address_queue = None

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
            self.logger.warning(
                f"⚠️  Failed to check balance for address {address}. "
                f"This may be due to network issues or provider unavailability. "
                f"Seed: {seed if seed else 'N/A'}"
            )
            return
        
        if not isinstance(balance, dict):
            self.logger.error(
                f"❌ Invalid balance format received for address {address}. "
                f"Expected dict, got {type(balance).__name__}"
            )
            return
            
        confirmed = balance.get('confirmed', 0)
        unconfirmed = balance.get('unconfirmed', 0)
        
        # Validate balance values are numeric
        try:
            confirmed = int(confirmed) if confirmed is not None else 0
            unconfirmed = int(unconfirmed) if unconfirmed is not None else 0
        except (ValueError, TypeError) as e:
            self.logger.error(
                f"❌ Invalid balance values for address {address}: {e}. "
                f"Balance data: {balance}"
            )
            return
        
        log_msg = f"Address: {address}, balance: {confirmed} (confirmed) + {unconfirmed} (unconfirmed)"
        
        if confirmed > 0 or unconfirmed > 0:
            self.logger.info(f"🎯 FOUND FUNDED ADDRESS!")
            self.logger.info(log_msg)
            if seed:
                self.logger.info(f"Seed phrase: {seed}")
            sys.exit(0)
        else:
            self.logger.debug(log_msg)  # Use debug level for empty balances

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    def _check_balance(self, provider, address, seed, scripthash=None):
        """Check balance with retry logic and improved error handling.
        
        Args:
            provider: BalanceProvider instance
            address: Bitcoin address to check
            seed: Seed phrase (for logging)
            scripthash: Optional scripthash for faster lookup
            
        Returns:
            Balance dict or None on error
        """
        try:
            balance = provider.get_balance(address, scripthash=scripthash)
            if balance is None:
                raise Exception("Provider returned None - connection may have failed")
            
            # Validate balance structure
            if not isinstance(balance, dict):
                raise ValueError(f"Invalid balance format: expected dict, got {type(balance).__name__}")
            
            if 'confirmed' not in balance or 'unconfirmed' not in balance:
                raise ValueError(f"Invalid balance structure: missing required keys. Got: {list(balance.keys())}")
            
            return balance
            
        except KeyboardInterrupt:
            # Don't retry on user interrupt
            raise
        except Exception as e:
            error_type = type(e).__name__
            self.logger.debug(
                f"Balance check failed for {address[:10]}... "
                f"({error_type}: {str(e)})"
            )
            return None

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        self.logger.info("\n⚠️  Received interrupt signal. Shutting down gracefully...")
        self.stop_event = True
        if self.address_queue:
            self.address_queue.stop()

    def _save_funded_address(self, address, balance, seed_phrase):
        """Save funded address information to a file.
        
        Args:
            address: Bitcoin address with funds
            balance: Balance information dict
            seed_phrase: BIP39 seed phrase
        """
        try:
            # Create results directory if it doesn't exist
            results_dir = "results"
            os.makedirs(results_dir, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(results_dir, f"funded_address_{timestamp}.txt")
            
            # Prepare file content
            confirmed = balance.get('confirmed', 0)
            unconfirmed = balance.get('unconfirmed', 0)
            total_balance = confirmed + unconfirmed
            
            content = f"""🎯 FUNDED BITCOIN ADDRESS FOUND 🎯

Discovery Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

═══════════════════════════════════════════════════════════════
ADDRESS INFORMATION
═══════════════════════════════════════════════════════════════
Address: {address}
Confirmed Balance: {confirmed} satoshis
Unconfirmed Balance: {unconfirmed} satoshis
Total Balance: {total_balance} satoshis ({total_balance / 100000000:.8f} BTC)

═══════════════════════════════════════════════════════════════
SEED PHRASE (KEEP THIS SECRET!)
═══════════════════════════════════════════════════════════════
{seed_phrase}

═══════════════════════════════════════════════════════════════
⚠️  SECURITY WARNING
═══════════════════════════════════════════════════════════════
• Keep this file secure and private
• Anyone with access to this seed phrase can control the funds
• Do not share this information with anyone
• Consider encrypting this file or storing it in a secure location
• This was found through brute-force (extremely rare occurrence)

═══════════════════════════════════════════════════════════════
"""
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"💾 Saved funded address details to: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save funded address to file: {e}")
            return None
    
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
            
            # Save to file if seed phrase is available and not a test
            if seed and not is_test:
                saved_file = self._save_funded_address(address, balance, seed)
                if saved_file:
                    self.logger.info(f"📁 Full details saved to: {saved_file}")
            
            return True
        return False

    @profile(output_file='lottery_profile')
    def lottery(self, server: str = None, port: int = None, use_queue: bool = True, show_stats: bool = True):
        """Search for funded Bitcoin addresses
        
        Args:
            server (str, optional): Electrum server hostname. If None, uses Blockstream API
            port (int, optional): Electrum server port. If None, uses Blockstream API
            use_queue (bool): Whether to use AddressQueue for pre-generating addresses
            show_stats (bool): Whether to show educational statistics
        """
        # Flush output immediately and ensure we see initial messages
        print("Starting lottery...", flush=True)
        sys.stdout.flush()
        
        # Educational warning (more fun version)
        self.logger.info("🎲 Bitcoin Roulette - Educational Edition 🎲")
        self.logger.info("⚠️  For educational purposes only - demonstrates why brute-forcing is impossible")
        sys.stdout.flush()
        
        # Initialize provider (auto-detects based on server/port)
        try:
            provider = BalanceProvider(
                electrum_server=server,
                electrum_port=port,
                electrum_protocol="t"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize provider: {e}")
            print(f"ERROR: Failed to initialize provider: {e}", flush=True)
            return
        
        if server and port:
            self.logger.info(f"Using Electrum server {server}:{port}")
        else:
            self.logger.info("Using Blockstream API (no server required)")
        sys.stdout.flush()

        # Initialize statistics tracker
        stats = BruteForceStatistics() if show_stats else None
        if stats:
            try:
                self.logger.info(stats.get_educational_message())
                sys.stdout.flush()
            except Exception as e:
                self.logger.warning(f"Could not display educational message: {e}")
                self.logger.info("Statistics tracking enabled (some calculations may be simplified)")
                sys.stdout.flush()

        if use_queue:
            # Initialize address queue
            queue_size = 100
            self.logger.info("Initializing address queue...")
            sys.stdout.flush()
            self.address_queue = AddressQueue(queue_size=queue_size)
            self.logger.info("Pre-generating addresses...")
            sys.stdout.flush()
            while self.address_queue.queue.qsize() < queue_size and not self.stop_event:  # Wait for initial batch
                time.sleep(0.1)
            self.logger.info(f"Queue ready with {self.address_queue.queue.qsize()} addresses")
            sys.stdout.flush()

        total_attempts = 0
        last_batch_time = time.time()
        
        self.logger.info("Starting address checking loop...")
        sys.stdout.flush()
        
        try:
            while not self.stop_event:
                try:
                    if use_queue:
                        result = self.address_queue.get_address(timeout=1)
                        address = result["address"]
                        seed_phrase = result["seed_phrase"]
                        scripthash = result.get("scripthash")  # Use scripthash if available
                    else:
                        result = bip39_module.Bip39AddressGenerator().generate_address()
                        address = result["address"]
                        seed_phrase = result["seed_phrase"]
                        scripthash = result.get("scripthash")  # Use scripthash if available

                    try:
                        balance = self._check_balance(provider, address, seed_phrase, scripthash)
                    except Exception as e:
                        self.logger.error(f"Error in _check_balance: {e}")
                        balance = None
                    
                    total_attempts += 1
                    
                    # Show progress for first few attempts
                    if total_attempts <= 5:
                        self.logger.info(f"Attempt {total_attempts}: Checked {address[:10]}... (balance: {balance})")
                        sys.stdout.flush()
                    
                    # Record attempt in statistics
                    if stats:
                        try:
                            stats.record_attempt(success=(balance is not None and 
                                                          (balance.get('confirmed', 0) > 0 or 
                                                           balance.get('unconfirmed', 0) > 0)))
                        except Exception as e:
                            # Silently handle statistics errors to not interrupt main loop
                            self.logger.debug(f"Statistics error (non-critical): {e}")
                    
                    if balance and self.report_funds(address, balance, seed_phrase):
                        if stats:
                            try:
                                self.logger.info("\n" + stats.format_statistics())
                            except Exception as e:
                                self.logger.warning(f"Could not format final statistics: {e}")
                        return

                    if total_attempts % 100 == 0:
                        now = time.time()
                        batch_elapsed = now - last_batch_time
                        rate = 100 / batch_elapsed if batch_elapsed > 0 else 0
                        queue_size = self.address_queue.queue.qsize() if use_queue else 'N/A'
                        provider_info = f"{server}:{port}" if server and port else "Blockstream API"
                        self.logger.info(
                            f"[{provider_info}] "
                            f"Rate: {rate:.2f}/s | "
                            f"Time: {batch_elapsed:.1f}s | "
                            f"Queue: {queue_size} | "
                            f"Total: {total_attempts} addresses"
                        )
                        sys.stdout.flush()
                        
                        # Show statistics every 1000 attempts
                        if stats and total_attempts % 1000 == 0:
                            try:
                                self.logger.info("\n" + stats.format_statistics())
                                sys.stdout.flush()
                            except Exception as e:
                                self.logger.warning(f"Could not format statistics: {e}")
                        
                        last_batch_time = now

                except KeyboardInterrupt:
                    # User requested stop, exit gracefully
                    self.logger.info("\n⚠️  Interrupted by user")
                    raise
                except Exception as e:
                    error_type = type(e).__name__
                    self.logger.error(
                        f"❌ Unexpected error in main loop ({error_type}): {str(e)}. "
                        f"Attempting to recover..."
                    )
                    time.sleep(5)
                    # Recreate provider on error
                    try:
                        provider.close()
                    except:
                        pass
                    provider = BalanceProvider(
                        electrum_server=server,
                        electrum_port=port,
                        electrum_protocol="t"
                    )

        finally:
            if use_queue and self.address_queue:
                self.address_queue.stop()
            provider.close()
            
            # Show final statistics
            if stats:
                try:
                    self.logger.info("\n" + "=" * 70)
                    self.logger.info("Final Statistics:")
                    self.logger.info("=" * 70)
                    self.logger.info("\n" + stats.format_statistics())
                except Exception as e:
                    self.logger.warning(f"Could not format final statistics: {e}")
                    # Show basic stats instead
                    self.logger.info(f"Total attempts: {stats.total_attempts}")
                    self.logger.info(f"Rate: {stats.attempts_per_second:.2f} attempts/second")

    def balance(self, address: str, server: str = None, port: int = None):
        """Check balance of a specific Bitcoin address.
        
        Args:
            address: Bitcoin address to check
            server (str, optional): Electrum server hostname. If None, uses Blockstream API
            port (int, optional): Electrum server port. If None, uses Blockstream API
        """
        # Initialize provider
        provider = BalanceProvider(
            electrum_server=server,
            electrum_port=port,
            electrum_protocol="t"
        )
        
        if server and port:
            self.logger.info(f"Using Electrum server {server}:{port}")
        else:
            self.logger.info("Using Blockstream API (no server required)")
        
        try:
            balance = provider.get_balance(address)
            self._validate_balance(address, balance, None)
            return balance
        finally:
            provider.close()

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
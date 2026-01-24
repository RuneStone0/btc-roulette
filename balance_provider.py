import logging
import requests
from typing import Dict, Optional
from electrum_query import ElectrumQuery

logger = logging.getLogger(__name__)


class BalanceProvider:
    """Unified interface for checking Bitcoin address balances.
    
    Supports multiple backends:
    - Electrum server (faster, requires server)
    - Blockstream API (slower, no server needed)
    
    Automatically falls back from Electrum to Blockstream API if Electrum fails.
    """
    
    def __init__(self, electrum_server: str = None, electrum_port: int = None, 
                 electrum_protocol: str = "t"):
        """Initialize balance provider.
        
        Args:
            electrum_server: Electrum server hostname (optional)
            electrum_port: Electrum server port (optional)
            electrum_protocol: Electrum protocol ('s' for SSL, 't' for TCP)
        """
        self.electrum_server = electrum_server
        self.electrum_port = electrum_port
        self.electrum_protocol = electrum_protocol
        self.electrum_client = None
        self.use_electrum = electrum_server is not None and electrum_port is not None
        self.provider_name = "Electrum" if self.use_electrum else "Blockstream API"
        
    def get_balance(self, address: str, scripthash: str = None) -> Optional[Dict[str, int]]:
        """Get balance for an address with automatic fallback.
        
        Args:
            address: Bitcoin address to check
            scripthash: Optional scripthash (faster for Electrum if provided)
            
        Returns:
            Dict with 'confirmed' and 'unconfirmed' keys, or None on error
        """
        # Use scripthash for Electrum if available (faster)
        if self.use_electrum and scripthash:
            balance = self._get_balance_electrum_scripthash(scripthash)
            if balance is not None:
                return balance
        
        # Fallback to address-based lookup
        if self.use_electrum:
            balance = self._get_balance_electrum(address)
            if balance is not None:
                return balance
            # Fallback to Blockstream if Electrum fails
            logger.warning("Electrum failed, falling back to Blockstream API")
        
        return self._get_balance_blockstream(address)
    
    def get_balance_by_scripthash(self, scripthash: str) -> Optional[Dict[str, int]]:
        """Get balance by scripthash (Electrum only, faster than address lookup).
        
        Args:
            scripthash: Script hash to check
            
        Returns:
            Dict with balance info or None on error
        """
        if self.use_electrum:
            return self._get_balance_electrum_scripthash(scripthash)
        else:
            # Blockstream API doesn't support scripthash directly
            logger.warning("Scripthash lookup only supported with Electrum server")
            return None
    
    def _get_balance_electrum_scripthash(self, scripthash: str) -> Optional[Dict[str, int]]:
        """Get balance via Electrum server using scripthash (faster).
        
        Args:
            scripthash: Script hash to check
            
        Returns:
            Dict with balance info or None on error
        """
        try:
            if not self.electrum_client:
                self.electrum_client = ElectrumQuery(
                    server_url=self.electrum_server,
                    port=self.electrum_port,
                    protocol=self.electrum_protocol
                )
            balance = self.electrum_client.get_scripthash_balance(scripthash)
            if balance is None:
                logger.debug(f"Electrum scripthash lookup returned None for {scripthash[:16]}...")
            return balance
        except Exception as e:
            logger.debug(f"Electrum scripthash error for {scripthash[:16]}...: {e}")
            return None
    
    def _get_balance_electrum(self, address: str) -> Optional[Dict[str, int]]:
        """Get balance via Electrum server.
        
        Args:
            address: Bitcoin address to check
            
        Returns:
            Dict with balance info or None on error
        """
        try:
            if not self.electrum_client:
                self.electrum_client = ElectrumQuery(
                    server_url=self.electrum_server,
                    port=self.electrum_port,
                    protocol=self.electrum_protocol
                )
            balance = self.electrum_client.get_address_balance(address)
            if balance is None:
                logger.debug(f"Electrum lookup returned None for {address[:10]}...")
            return balance
        except Exception as e:
            logger.debug(f"Electrum error for {address[:10]}...: {e}")
            return None
    
    def _get_balance_blockstream(self, address: str) -> Optional[Dict[str, int]]:
        """Get balance via Blockstream API (no server needed).
        
        Args:
            address: Bitcoin address to check
            
        Returns:
            Dict with balance info or None on error
        """
        try:
            url = f"https://blockstream.info/api/address/{address}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Calculate balance from chain_stats and mempool_stats
            # Blockstream returns funded_txo_sum (total received) and spent_txo_sum (total sent)
            chain_stats = data.get('chain_stats', {})
            mempool_stats = data.get('mempool_stats', {})
            
            # Balance = received - spent
            confirmed = chain_stats.get('funded_txo_sum', 0) - chain_stats.get('spent_txo_sum', 0)
            unconfirmed = mempool_stats.get('funded_txo_sum', 0) - mempool_stats.get('spent_txo_sum', 0)
            
            return {
                'confirmed': max(0, confirmed),  # Can be negative if spent, but we show 0
                'unconfirmed': unconfirmed
            }
        except requests.exceptions.Timeout:
            logger.debug(f"Blockstream API timeout for {address[:10]}...")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Blockstream API connection error for {address[:10]}...: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 429:
                logger.warning("Blockstream API rate limit reached. Consider using Electrum server for faster queries.")
            else:
                logger.debug(f"Blockstream API HTTP error for {address[:10]}...: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Blockstream API request error for {address[:10]}...: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error in Blockstream API for {address[:10]}...: {e}")
            return None
    
    def close(self):
        """Clean up connections."""
        if self.electrum_client:
            self.electrum_client.close()
            self.electrum_client = None

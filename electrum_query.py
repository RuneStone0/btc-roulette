import logging
import asyncio
import socket
from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo

class ElectrumQuery:
    _dns_cache = {}

    def __init__(self, server_url="umbrel.local", port=50003, protocol="s"):
        self.server_url = server_url
        self.port = port
        self.protocol = protocol
        self.client = None
        self.logger = logging.getLogger(__name__)
        self.loop = None
        self._loop_owner = False

    async def _resolve_dns(self):
        if self.server_url in self._dns_cache:
            return self._dns_cache[self.server_url]
        
        try:
            info = await self.loop.getaddrinfo(
                self.server_url, self.port,
                family=socket.AF_INET,
                proto=socket.IPPROTO_TCP,
            )
            if info:
                ip = info[0][4][0]
                self._dns_cache[self.server_url] = ip
                return ip
        except Exception as e:
            self.logger.error(f"DNS resolution failed for {self.server_url} - {str(e)}")
        return None

    async def _ensure_connected(self):
        """Ensure client is connected, reconnect if needed."""
        if self.client and hasattr(self.client, 'is_connected') and self.client.is_connected():
            return True
        
        try:
            ip = await self._resolve_dns()
            if not ip:
                return False
            
            if self.client:
                self.client.close()
            
            self.client = StratumClient()
            self.svr = ServerInfo(self.server_url, ip, ports=(self.protocol + str(self.port)))
            await self.client.connect(self.svr, disable_cert_verify=True)
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to {self.server_url}:{self.port} - {str(e)}")
            if self.client:
                self.client.close()
                self.client = None
            return False

    async def _get_balance_async(self, method, param):
        """Get balance asynchronously, reusing connection if available."""
        if not await self._ensure_connected():
            return None
        
        try:
            return await self.client.RPC(method, param)
        except Exception as e:
            self.logger.error(f"Error in RPC call to {self.server_url}:{self.port} - {str(e)}")
            # Mark connection as invalid, will reconnect on next call
            if self.client:
                try:
                    self.client.close()
                except:
                    pass
                self.client = None
            return None

    def _get_or_create_loop(self):
        """Get or create an event loop for this instance."""
        if self.loop is None or self.loop.is_closed():
            try:
                self.loop = asyncio.get_event_loop()
                if self.loop.is_closed():
                    raise RuntimeError("Event loop is closed")
                self._loop_owner = False
            except RuntimeError:
                # No event loop in current thread, create one
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self._loop_owner = True
        return self.loop

    def get_address_balance(self, address):
        try:
            loop = self._get_or_create_loop()
            return loop.run_until_complete(
                self._get_balance_async('blockchain.address.get_balance', address)
            )
        except asyncio.InvalidStateError as e:
            self.logger.error(f"Invalid state error: {e}, address: {address}")
            # Reset loop on invalid state
            self.loop = None
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}, address: {address}")
            return None

    def get_scripthash_balance(self, scripthash):
        try:
            loop = self._get_or_create_loop()
            return loop.run_until_complete(
                self._get_balance_async('blockchain.scripthash.get_balance', scripthash)
            )
        except asyncio.InvalidStateError as e:
            self.logger.error(f"Invalid state error: {e}, scripthash: {scripthash}")
            # Reset loop on invalid state
            self.loop = None
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}, scripthash: {scripthash}")
            return None

    def close(self):
        """Close connection and clean up resources."""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
        # Clean up event loop if we created it
        if self._loop_owner and self.loop and not self.loop.is_closed():
            try:
                self.loop.close()
            except:
                pass
            self.loop = None
            self._loop_owner = False

if __name__ == "__main__":
    client = ElectrumQuery()
    # Example address lookup
    client.get_address_balance("bc1qns9f7yfx3ry9lj6yz7c9er0vwa0ye2eklpzqfw")
    # Example scripthash lookup
    # client.get_scripthash_balance("ded22b2ecdb7226361dc6120e6b230869fba8062d6de97a77dc3438a30255da8")

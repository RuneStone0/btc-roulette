import asyncio
from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo
import logging
from typing import List, Dict
import time

#There is a schedule to move the default list to e-x (electrumx) by Jan 2018
#Schedule is as follows:
#move ~3/4 to e-x by 1.4.17
#then gradually switch remaining nodes to e-x nodes

# https://github.com/spesmilo/electrum/blob/afa1a4d22a31d23d088c6670e1588eed32f7114d/lib/network.py#L57
DEFAULT_SERVERS = {
    #'ecdsa.net':{'s':'110'},                # core, e-x
    #'VPS.hsmiths.com':{'s':'50002'},        # core, e-x
    #'helicarrier.bauerj.eu':{'s':'50002'},  # core, e-x
    #'kirsche.emzy.de':{'s':'50002'},        # core, e-x
    #'b.1209k.com':{'s':'50002'},            # XT, jelectrum
    'umbrel.lan':{'t':'50003'},             # local
}
# https://btc.arnzenarms.com:50002/

async def test_server_connection(host: str, port: str, protocol: str = 's', timeout: int = 5) -> Dict:
    """Test connection to a single Electrum server
    
    Args:
        host: Server hostname
        port: Server port
        protocol: Connection protocol ('s' for SSL or 't' for TCP)
        timeout: Connection timeout in seconds
    
    Returns:
        Dict with server info and connection status
    """
    result = {
        'host': host,
        'port': port,
        'protocol': protocol,
        'working': False,
        'latency': None,
        'error': None
    }
    
    try:
        # Create server info
        server = ServerInfo(host, host, ports=(protocol + str(port)))
        client = StratumClient()
        
        # Measure connection time
        start = time.time()
        
        # Try to connect with timeout
        await asyncio.wait_for(
            client.connect(server, disable_cert_verify=True),
            timeout=timeout
        )
        
        # Get server info if connected
        if client.protocol_version:
            result['working'] = True
            result['latency'] = round((time.time() - start) * 1000, 2)  # ms
            result['version'] = client.server_version
            
    except asyncio.TimeoutError:
        result['error'] = 'Connection timeout'
    except Exception as e:
        result['error'] = str(e)
    finally:
        if 'client' in locals():
            client.close()
            
    return result

async def test_servers(servers: dict = None, 
                      timeout: int = 5,
                      max_concurrent: int = 10) -> List[Dict]:
    """Test multiple Electrum servers concurrently
    
    Args:
        servers: Dictionary of servers to test (uses DEFAULT_SERVERS if None)
        timeout: Connection timeout per server
        max_concurrent: Maximum number of concurrent connection tests
        
    Returns:
        List of working servers sorted by latency
    """
    if servers is None:
        servers = DEFAULT_SERVERS
        
    # Create tasks for each server
    tasks = []
    sem = asyncio.Semaphore(max_concurrent)
    
    async def _test_with_semaphore(host, port, protocol):
        async with sem:
            return await test_server_connection(host, port, protocol, timeout)
    
    # Create test tasks for each server and protocol
    for host, ports in servers.items():
        for protocol, port in ports.items():
            tasks.append(_test_with_semaphore(host, port, protocol))
            
    # Run all tests concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter working servers and sort by latency
    working_servers = [r for r in results if isinstance(r, dict) and r['working']]
    return sorted(working_servers, key=lambda x: x['latency'])

def get_working_servers(timeout: int = 5, max_concurrent: int = 10) -> List[Dict]:
    """Synchronous wrapper to test and get working Electrum servers
    
    Args:
        timeout: Connection timeout per server
        max_concurrent: Maximum number of concurrent connection tests
        
    Returns:
        List of working servers sorted by latency
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_servers(
            timeout=timeout,
            max_concurrent=max_concurrent
        ))
    finally:
        loop.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test all servers and print results
    working_servers = get_working_servers()
    print("\nWorking servers:")
    for server in working_servers:
        print(f"{server['host']}:{server['port']} ({server['protocol']}) - "
              f"latency: {server['latency']}ms")

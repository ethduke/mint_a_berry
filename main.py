import requests
from web3 import Web3
import json
import random
import time

def get_address_from_private_key(w3, private_key):
    account = w3.eth.account.from_key(private_key)
    return account.address

def read_private_keys(filename='addresses.txt'):
    with open(filename, 'r') as file:
        # Read lines and strip whitespace/0x prefix
        private_keys = [line.strip() for line in file.readlines()]
        # Remove 0x prefix if present
        private_keys = [pk[2:] if pk.startswith('0x') else pk for pk in private_keys]
        return private_keys

def read_proxies(filename='proxies.txt'):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def get_random_proxy(proxies):
    if not proxies:
        return None
    return random.choice(proxies)

def format_proxy(proxy):
    if not proxy:
        return None
    
    try:
        # Handle full URL format
        if proxy.startswith('http://'):
            proxy = proxy.replace('http://', '')
        
        if '@' in proxy:
            # Split at the last @ in case credentials contain @
            auth, ip_port = proxy.rsplit('@', 1)
            
            # Handle cases where username might contain :
            if auth.count(':') > 1:
                username = auth.rsplit(':', 1)[0]
                password = auth.rsplit(':', 1)[1]
            else:
                username, password = auth.split(':')
                
            return {
                'http': f'http://{username}:{password}@{ip_port}',
                'https': f'http://{username}:{password}@{ip_port}'
            }
        else:
            return {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
    except Exception as e:
        print(f'Error formatting proxy {proxy}: {str(e)}')
        return None

def make_signed_message_request(address, proxies):
    url = 'https://berry.beboundless.xyz/signed-message'
    
    headers = {
        'authority': 'berry.beboundless.xyz',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'en,en-US;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://berry.beboundless.xyz',
        'referer': 'https://berry.beboundless.xyz/',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    }
    
    payload = {
        'address': address
    }
    
    max_retries = 3
    retry_delay = 2  # seconds
    used_proxies = set()
    
    while len(used_proxies) < len(proxies):
        # Get a proxy we haven't tried yet
        available_proxies = [p for p in proxies if p not in used_proxies]
        if not available_proxies:
            break
            
        proxy = random.choice(available_proxies)
        used_proxies.add(proxy)
        print(f'\n>>> Switching to new proxy: {proxy}')
        
        for attempt in range(max_retries):
            try:
                formatted_proxy = format_proxy(proxy)
                if not formatted_proxy:
                    print(f'❌ Invalid proxy format, skipping: {proxy}')
                    break
                    
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=payload, 
                    proxies=formatted_proxy, 
                    timeout=10
                )
                response.raise_for_status()
                print('✅ Proxy working successfully!')
                print('Response:', response.text)
                return response.json()
                
            except requests.exceptions.ProxyError as e:
                print(f'❌ Proxy error (attempt {attempt + 1}/{max_retries}): Proxy not working or blocked')
                if attempt < max_retries - 1:
                    print(f'Waiting {retry_delay} seconds before retry...')
                    time.sleep(retry_delay)
                continue
                
            except requests.exceptions.ConnectTimeout:
                print(f'❌ Proxy timeout (attempt {attempt + 1}/{max_retries}): Connection took too long')
                if attempt < max_retries - 1:
                    print(f'Waiting {retry_delay} seconds before retry...')
                    time.sleep(retry_delay)
                continue
                
            except requests.exceptions.RequestException as e:
                print(f'❌ Request error (attempt {attempt + 1}/{max_retries}): {str(e)}')
                if attempt < max_retries - 1:
                    print(f'Waiting {retry_delay} seconds before retry...')
                    time.sleep(retry_delay)
                continue
        
        print(f'❌ Proxy {proxy} failed all attempts, switching to another proxy...')
    
    print('❌ All proxies have been tried without success')
    return None

def mint_with_signature(recipient_address, signature, timestamp, private_key):
    # Load ABI from file
    with open('abi.json', 'r') as file:
        contract_abi = json.load(file)
    
    # Connect to Base network
    w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
    
    # Contract setup
    CONTRACT_ADDRESS = '0xa25e0AF7Dd580fcE7121FD78E95c3f3beE258e8f'
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
    
    # Remove '0x' prefix from signature if present and convert to bytes
    signature = bytes.fromhex(signature[2:] if signature.startswith('0x') else signature)
    
    # Estimate gas for the transaction
    estimated_gas = contract.functions.mintTo(
        recipient_address,
        signature,
        timestamp
    ).estimate_gas({
        'from': recipient_address,
    })
    
    # Add 20% buffer to estimated gas
    gas_limit = int(estimated_gas * 1.2)
    
    # Build transaction
    transaction = contract.functions.mintTo(
        recipient_address,
        signature,
        timestamp
    ).build_transaction({
        'from': recipient_address,
        'gas': gas_limit,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(recipient_address),
        'chainId': 8453  # Base mainnet chain ID
    })
    
    # Sign transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    try:
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        # Get transaction hash in hex
        tx_hash_hex = w3.to_hex(tx_hash)
        print('Transaction Hash:', tx_hash_hex)
        
        return tx_hash_hex
        
    except Exception as e:
        error_str = str(e)
        if "Wallet has already minted" in error_str:
            print(f'Address {recipient_address} has already minted a Berry NFT')
            return None
        else:
            raise  # Re-raise other exceptions

if __name__ == '__main__':
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
    
    # Read private keys and proxies
    private_keys = read_private_keys()
    proxies = read_proxies()
    
    # Initialize statistics
    stats = {
        'total_processed': 0,
        'successful_mints': 0,
        'already_minted': 0,
        'failed': 0
    }
    
    print("Mint a Berry NFT")
    print(f'Loaded 142 addresses and 201 proxies')
    
    # Process each private key
    for private_key in private_keys:
        try:
            stats['total_processed'] += 1
            
            # Get the corresponding address for this private key
            recipient = get_address_from_private_key(w3, private_key)
            print(f'\nProcessing for address: {recipient}')
            
            # Try to get signature using available proxies
            result = make_signed_message_request(recipient, proxies)
            if result:
                signature = result['signature']
                timestamp = result['timestamp']
                
                # Add random delay between signature and mint (1-3 seconds)
                delay = random.uniform(1, 3)
                print(f'Waiting {delay:.2f} seconds before minting...')
                time.sleep(delay)
                
                # Send transaction and get hash
                tx_hash = mint_with_signature(recipient, signature, timestamp, private_key)
                if tx_hash:  # Only print success message if we got a transaction hash
                    print('Transaction submitted successfully!')
                    print('You can track your transaction at:')
                    print(f'https://basescan.org/tx/{tx_hash}')
                    stats['successful_mints'] += 1
            
        except Exception as e:
            error_str = str(e)
            if "Wallet has already minted" in error_str:
                print(f'Address {recipient} has already minted a Berry NFT')
                stats['already_minted'] += 1
            else:
                print(f'Error processing private key: {str(e)}')
                stats['failed'] += 1
        
        # Add random delay between accounts (2-5 seconds)
        if private_keys.index(private_key) < len(private_keys) - 1:
            delay = random.uniform(2, 5)
            print(f'\nWaiting {delay:.2f} seconds before next account...')
            time.sleep(delay)
        
        print('-' * 50)
    
    # Print final statistics
    print('\n' + '=' * 50)
    print('FINAL STATISTICS:')
    print(f'✅ Successfully minted: {stats["successful_mints"]} Berry NFTs')
    print(f'ℹ️ Already minted: {stats["already_minted"]} NFTs')
    print(f'❌ Failed: {stats["failed"]} attempts')
    print(f'📊 Total processed: {stats["total_processed"]} accounts')
    print('=' * 50)

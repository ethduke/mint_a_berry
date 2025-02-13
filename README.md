# Berry NFT Minter

An educational script demonstrating how to interact with smart contracts on Base network for minting NFTs.

## Features

- Interacts with Berry NFT contract on Base network
- Handles server signature requests with proxy support
- Processes multiple wallets from addresses.txt
- Tracks minting statistics and transaction status

## Setup

1. Install requirements:

pip install -r requirements.txt

2. Create required files:
- `addresses.txt` - One private key per line
- `proxies.txt` - One proxy per line (format: ip:port or username:password@ip:port)
- `abi.json` - Contract ABI

## How it Works
1. Reads keys & gets addresses
2. Gets server signatures via proxies
3. Mints NFTs with signatures
4. Handles errors
5. Shows stats

## Note

Features:
- Web3 contract interactions
- Server signature requests (parsing responses)
- Proxy handling
- Transaction management
- Error handling